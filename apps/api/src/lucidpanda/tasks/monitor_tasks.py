"""
tasks/monitor_tasks.py — 系统监控和告警任务
=========================================
"""

import asyncio

from src.lucidpanda.core.logger import logger
from src.lucidpanda.core.taskiq_broker import broker
from src.lucidpanda.db.intelligence import IntelligenceRepo
from src.lucidpanda.providers.channels.bark import BarkChannel
from src.lucidpanda.providers.channels.email import EmailChannel


@broker.task(schedule=[{"cron": "0 8 * * *"}])  # 每天早上 8点运行
async def report_missed_entities():
    """定期推送高频未知实体报告"""
    logger.info("🔍 [TaskIQ] 开始执行全量未知实体监控...")
    db = IntelligenceRepo()
    missed = await asyncio.to_thread(db.get_frequent_missed_entities, 1, 3)

    if not missed:
        logger.info("✅ 本时段未发现高频未知实体。")
        return {"status": "ok", "missed_count": 0}

    # Format the report
    report_lines = ["🚨 【系统警报】发现高频未知实体，请人工审核并录入 Registry：\n"]
    for m in missed:
        report_lines.append(
            f"• {m['raw_entity_name']} (出现 {m['occurrence_count']} 次, 最后见于 {m['last_source_id']})"
        )

    body = "\n".join(report_lines)
    title = f"⚠️ LucidPanda 未知实体告警 ({len(missed)}项)"

    channels = [BarkChannel(), EmailChannel()]
    for channel in channels:
        try:
            channel.send(title, body)
        except Exception as e:
            logger.warning(f"❌ 发送告警失败 {channel.__class__.__name__}: {e}")

    logger.info(f"📣 [TaskIQ] 已推送未知实体告警！({len(missed)}个实体)")
    return {"status": "alerted", "missed_count": len(missed)}
