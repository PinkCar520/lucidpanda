"""
TaskIQ Broker Configuration for LucidPanda
==========================================
Replaces the old Celery setup with a lightweight, native asyncio TaskIQ broker
using Redis as the message transport and Result Backend.
"""
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from src.lucidpanda.config import settings

# 1. 配置结果后端 (Result Backend) - 可选，如果我们不需要保留任务结果，可以用 Dummy
redis_result_backend = RedisAsyncResultBackend(
    redis_url=settings.REDIS_URL,
)

# 2. 配置主 Broker (ListQueueBroker 代替原有的 Celery Broker)
broker = ListQueueBroker(
    url=settings.REDIS_URL,
).with_result_backend(redis_result_backend)

# 3. 开启调度器 (替代 Celery Beat)
# 使用 LabelScheduleSource 允许我们通过装饰器的 labels 来控制定时任务
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

# IMPORTANT: Import tasks here to ensure they are registered with the broker/scheduler

# 当 FastAPI 或独立的 Worker 启动时，需要初始化这些东西
@broker.on_event("startup")
async def startup() -> None:
    pass

@broker.on_event("shutdown")
async def shutdown() -> None:
    pass
