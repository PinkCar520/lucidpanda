#!/usr/bin/env python3
"""
scripts/backfill_knowledge_graph.py
====================================
历史数据回填脚本：将已有的 entities JSONB 数据写入 entity_nodes / entity_edges 图谱表。

运行方式：
    cd /path/to/LucidPanda
    python scripts/backfill_knowledge_graph.py

两个阶段：
  Step A：对 entities IS NOT NULL 的记录，直接从 JSONB 提取关系 → 写入图谱（无需调 LLM）
  Step B：对 entities IS NULL AND urgency_score >= 7 的记录，重新调 DeepSeek 补齐 entities，再写图谱

可通过命令行参数控制：
  --step a      只执行 Step A（默认）
  --step b      只执行 Step B
  --step all    执行 A 和 B
  --dry-run     只统计，不写入
  --batch-size  每批处理数量（默认 50）
  --min-urgency Step B 最低紧急度门槛（默认 7）
"""
import argparse
import logging
import os
import sys
import time

# 确保能找到 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='LucidPanda 知识图谱历史回填工具')
    parser.add_argument('--step', choices=['a', 'b', 'all'], default='a',
                        help='执行阶段: a=已有entities回填, b=重新调LLM补齐, all=全部')
    parser.add_argument('--dry-run', action='store_true',
                        help='只统计数量，不执行写入')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Step B 自动确认，跳过交互式提示（适用于 Docker 非交互终端）')
    parser.add_argument('--llm', choices=['deepseek', 'gemini'], default='deepseek',
                        help='Step B 使用的 LLM 提供商（默认 deepseek）')
    parser.add_argument('--batch-size', type=int, default=50,
                        help='每批处理的记录数量（默认 50）')
    parser.add_argument('--min-urgency', type=int, default=7,
                        help='Step B 的最低 urgency_score 门槛（默认 7）')
    parser.add_argument('--sleep-ms', type=int, default=200,
                        help='Step B 每次 LLM 调用后的等待毫秒（限速，默认 200ms）')
    return parser.parse_args()


def step_a_backfill(db, batch_size: int, dry_run: bool) -> int:
    """
    Step A：对已有 entities 的记录，提取关系写入图谱。
    不需要调用任何外部 API，完全从本地数据库读取。
    """


    logger.info("=" * 60)
    logger.info("Step A：从现有 entities JSONB 回填图谱边")
    logger.info("=" * 60)

    conn = db._get_conn()
    cursor = conn.cursor()

    # 统计总数
    cursor.execute("""
        SELECT COUNT(*) FROM intelligence
        WHERE entities IS NOT NULL
          AND jsonb_array_length(entities) > 0
          AND status = 'COMPLETED'
    """)
    total = cursor.fetchone()[0]
    logger.info(f"找到 {total} 条有 entities 的已完成记录")

    if dry_run:
        logger.info("[Dry-run] 不执行写入，退出 Step A")
        conn.close()
        return 0

    processed = 0
    success = 0
    offset = 0

    while True:
        cursor.execute("""
            SELECT source_id, entities
            FROM intelligence
            WHERE entities IS NOT NULL
              AND jsonb_array_length(entities) > 0
              AND status = 'COMPLETED'
            ORDER BY id ASC
            LIMIT %s OFFSET %s
        """, (batch_size, offset))
        rows = cursor.fetchall()
        if not rows:
            break

        for row in rows:
            source_id = row['source_id']
            entities = row['entities']
            if not source_id or not entities:
                continue
            try:
                # 用已有的 entities 构造一个轻量 analysis_result
                result = db.upsert_knowledge_graph(
                    source_id,
                    {"entities": entities}
                )
                success += 1
            except Exception as e:
                logger.warning(f"  ⚠️  source_id={source_id} 失败: {e}")
            processed += 1

        offset += batch_size
        logger.info(f"  进度: {min(offset, total)}/{total} 已处理, {success} 成功")

    conn.close()
    logger.info(f"Step A 完成: {processed} 条处理, {success} 条成功写入图谱")
    return success


def step_b_backfill(db, llm, batch_size: int, min_urgency: int,
                    sleep_ms: int, dry_run: bool, auto_yes: bool = False) -> int:
    """
    Step B：对 entities IS NULL 的高价值记录，重新调 LLM 补齐 entities，再写图谱。
    有 API 调用成本，建议先通过 --dry-run 确认数量。
    """


    logger.info("=" * 60)
    logger.info(f"Step B：重新 LLM 提取 entities（urgency >= {min_urgency}）")
    logger.info("=" * 60)

    conn = db._get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM intelligence
        WHERE entities IS NULL
          AND urgency_score >= %s
          AND status = 'COMPLETED'
          AND content IS NOT NULL
    """, (min_urgency,))
    total = cursor.fetchone()[0]
    logger.info(f"找到 {total} 条 entities=NULL 且 urgency>={min_urgency} 的记录")

    if dry_run:
        logger.info(f"[Dry-run] 预计调用 LLM {total} 次，退出 Step B")
        conn.close()
        return 0

    if total == 0:
        logger.info("没有需要处理的记录，Step B 跳过")
        conn.close()
        return 0

    if not auto_yes:
        try:
            confirm = input(f"\n将调用 LLM {total} 次，预计费用约 ${total * 0.002:.2f}。继续? [y/N]: ")
            if confirm.strip().lower() != 'y':
                logger.info("用户取消，退出 Step B")
                conn.close()
                return 0
        except EOFError:
            logger.error("非交互式终端无法读取确认输入。请使用 --yes 参数跳过确认，例如：")
            logger.error("  docker exec lucidpanda_api python scripts/backfill_knowledge_graph.py --step b --yes --llm gemini")
            conn.close()
            return 0
    else:
        logger.info(f"--yes 模式：自动确认，将调用 LLM {total} 次（预计费用约 ${total * 0.002:.2f}）")

    processed = 0
    success = 0
    offset = 0

    while True:
        cursor.execute("""
            SELECT source_id, content, author
            FROM intelligence
            WHERE entities IS NULL
              AND urgency_score >= %s
              AND status = 'COMPLETED'
              AND content IS NOT NULL
            ORDER BY urgency_score DESC, id ASC
            LIMIT %s OFFSET %s
        """, (min_urgency, batch_size, offset))
        rows = cursor.fetchall()
        if not rows:
            break

        for row in rows:
            source_id = row['source_id']
            try:
                analysis = llm.analyze({
                    "content": row['content'] or '',
                    "author": row['author'] or '',
                    "context": "",
                })
                entities = analysis.get("entities", [])
                if entities:
                    # 写入 intelligence.entities 字段
                    update_cursor = conn.cursor()
                    from psycopg.types.json import Jsonb
                    update_cursor.execute(
                        "UPDATE intelligence SET entities = %s WHERE source_id = %s",
                        (Jsonb(entities), source_id)
                    )
                    conn.commit()
                    # 写入图谱
                    db.upsert_knowledge_graph(source_id, analysis)
                    success += 1
                    logger.info(f"  ✅ {source_id[:40]} → {len(entities)} 实体")
                else:
                    logger.info(f"  ⚠️  {source_id[:40]} → LLM 返回空 entities")
            except Exception as e:
                logger.warning(f"  ❌ {source_id[:40]} 失败: {e}")

            processed += 1
            time.sleep(sleep_ms / 1000.0)

        offset += batch_size
        logger.info(f"  Step B 进度: {min(offset + batch_size, total)}/{total}")

    conn.close()
    logger.info(f"Step B 完成: {processed} 条处理, {success} 条成功")
    return success


def main():
    args = parse_args()

    logger.info("LucidPanda 知识图谱历史回填工具")
    logger.info(f"模式: step={args.step}, dry_run={args.dry_run}, batch={args.batch_size}")

    # 初始化 DB
    from src.lucidpanda.core.database import IntelligenceDB
    db = IntelligenceDB()

    total_written = 0

    if args.step in ('a', 'all'):
        total_written += step_a_backfill(db, args.batch_size, args.dry_run)

    if args.step in ('b', 'all'):
        if args.llm == 'gemini':
            import os

            from src.lucidpanda.providers.llm.gemini import GeminiLLM
            # 批量任务优先使用 gemini-2.0-flash-lite（无每日上限），避免占用实时分析配额
            if not os.environ.get("GEMINI_MODEL"):
                os.environ["GEMINI_MODEL"] = os.environ.get("GEMINI_BATCH_MODEL", "gemini-2.0-flash-lite")
            llm = GeminiLLM()
            logger.info(f"使用 Gemini 作为 LLM 提供商（模型: {os.environ.get('GEMINI_MODEL')}）")
        else:
            from src.lucidpanda.providers.llm.deepseek import DeepSeekLLM
            llm = DeepSeekLLM()
            logger.info("使用 DeepSeek 作为 LLM 提供商")
        total_written += step_b_backfill(
            db, llm,
            batch_size=args.batch_size,
            min_urgency=args.min_urgency,
            sleep_ms=args.sleep_ms,
            dry_run=args.dry_run,
            auto_yes=args.yes,
        )

    logger.info("=" * 60)
    logger.info(f"全部完成。共写入图谱: {total_written} 条记录")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
