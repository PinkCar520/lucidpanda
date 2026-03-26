import asyncio
import os
import sys
import time
from datetime import date

from dotenv import load_dotenv

# 确保能导入 src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载配置
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
ai_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.ai")
load_dotenv(env_path)
load_dotenv(ai_env_path, override=True)

from src.lucidpanda.config import settings  # noqa: E402
from src.lucidpanda.core.engine import AlphaEngine  # noqa: E402
from src.lucidpanda.db.base import close_global_pool  # noqa: E402

# 强制本地数据库与开启所有组件 (已在 docker-compose 中暴露 6379)
# 使用默认配置 (由环境变量从 Docker Compose 注入)
pass
settings.ENABLE_AGENT_TOOLS = False

async def test_full_factor_flow():
    print("🚀 开始全链路因子聚合 (Full Flow) 测试...")

    # 1. 初始化引擎
    engine = AlphaEngine()
    # 模拟禁用通知通道，防止测试时报错
    engine.channels = []

    # 2. 构造测试数据
    source_id = f"test_factor_full_{int(time.time())}"
    raw_data = {
        "source_id": source_id,
        "id": source_id,
        "content": f"美联储主席鲍威尔今日表示，由于通胀数据超预期，美联储可能在下周会议上调整基准利率，当前市场关注点在于降息 26 个基点的可能性 ({int(time.time())})。",
        "extraction_method": "TEST_MOCK"
    }

    # 清理旧数据
    try:
        conn = engine.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM intelligence WHERE source_id = %s", (source_id,))
            cursor.execute("DELETE FROM entity_metrics WHERE canonical_id = 'ent_fed_powell' AND metric_date = %s", (date.today(),))
            # 预插入记录，模拟 Collector 行为
            cursor.execute("""
                INSERT INTO intelligence (source_id, content, status, timestamp)
                VALUES (%s, %s, 'PENDING', NOW())
            """, (source_id, raw_data["content"]))
            conn.commit()
        print(f"🧹 已清理并预初始化测试数据 ({source_id})。")
    except Exception as e:
        print(f"⚠️ 清理失败: {e}")

    # 2. 调用 AlphaEngine 处理
    # 内部流程: LLM -> EntityResolver -> DB Save -> FactorService Update
    print("🤖 启动 AlphaEngine 处理逻辑 (包含 LLM 分析)...")
    await engine._process_single_item_async(raw_data)

    # 3. 验证结果
    print("\n🧐 验证数据库中的因子变化...")
    trend = await engine.factor_service.get_entity_trend_async("ent_fed_powell", days=1)

    if trend:
        metric = trend[0]
        print("✅ 成功命中因子更新!")
        print("  - Canonical ID: ent_fed_powell")
        print(f"  - 平均分 (avg_sentiment): {metric['avg_sentiment']:.4f}")
        print(f"  - 提及次数 (mention_count): {metric['mention_count']}")

        if metric['mention_count'] >= 1:
            print("\n🌟 全链路验证 (LLM -> Factor) 100% 通过！")
        else:
            print("\n❌ 提及次数不符合预期。")
    else:
        print("❌ 因子表中未发现对应记录。请检查 LLM 是否成功提取了 '鲍威尔' 以及 EntityResolver 是否正确对齐了 ID。")

    # 4. 显式关闭连接池，防止 FinalizationError
    close_global_pool()

if __name__ == "__main__":
    asyncio.run(test_full_factor_flow())
