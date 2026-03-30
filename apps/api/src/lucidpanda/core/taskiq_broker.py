"""
TaskIQ Broker Configuration for LucidPanda
==========================================
Replaces the old Celery setup with a lightweight, native asyncio TaskIQ broker
using Redis as the message transport and Result Backend.
"""

import asyncio
from redis.exceptions import ConnectionError as RedisConnectionError
from taskiq import TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from src.lucidpanda.config import settings


class RobustListQueueBroker(ListQueueBroker):
    """
    Robust version of ListQueueBroker that handles connection errors during shutdown.
    
    When TaskIQ worker shuts down, the Redis connection can be closed while the
    prefetcher is still blocked on BRPOP, leading to redis.exceptions.ConnectionError.
    This subclass catches and ignores these expected errors.
    """
    async def listen(self):
        try:
            async for message in super().listen():
                yield message
        except (RedisConnectionError, RuntimeError, asyncio.CancelledError):
            # During shutdown, these errors are expected as the connection or loop 
            # is closed while the prefetcher is still waiting on BRPOP. 
            pass


# 1. 配置结果后端 (Result Backend) - 可选，如果我们不需要保留任务结果，可以用 Dummy
redis_result_backend: RedisAsyncResultBackend = RedisAsyncResultBackend(
    redis_url=settings.REDIS_URL,
)

# 2. 配置主 Broker (ListQueueBroker 代替原有的 Celery Broker)
broker = RobustListQueueBroker(
    url=settings.REDIS_URL,
).with_result_backend(redis_result_backend)

# 3. 开启调度器 (替代 Celery Beat)
# 使用 LabelScheduleSource 允许我们通过装饰器的 labels 来控制定时任务
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

# IMPORTANT: Import tasks here to ensure they are registered with the broker/scheduler
import src.lucidpanda.tasks.collector_tasks
import src.lucidpanda.tasks.monitor_tasks


# 当 FastAPI 或独立的 Worker 启动时，需要初始化这些东西
@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState) -> None:
    pass


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown(state: TaskiqState) -> None:
    pass
