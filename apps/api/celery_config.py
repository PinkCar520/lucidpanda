"""
Celery 配置文件
================
LucidPanda 任务队列配置
"""
import os
from celery import Celery
from celery.schedules import crontab

# 从环境变量读取 Redis URL，默认使用本地 Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# 创建 Celery 应用
app = Celery(
    'lucidpanda',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['src.lucidpanda.tasks.collector_tasks']
)

# Celery 配置
app.conf.update(
    # 时区配置
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # 序列化配置
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # 任务确认配置
    task_acks_late=True,
    task_ack_on_failure_or_timeout=True,
    
    # 重试配置
    task_default_retry_delay=60,
    task_max_retries=3,
    task_default_rate_limit=None,
    
    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # 结果过期时间 (1 小时)
    result_expires=3600,
)

# 动态调度任务配置
# 注意：实际调度逻辑在 collector_tasks 中通过 Redis 状态控制
# 这里只配置一个每分钟触发的任务，由任务内部判断是否真的需要采集
app.conf.beat_schedule = {
    'fetch-all-feeds': {
        'task': 'src.lucidpanda.tasks.collector_tasks.fetch_all_feeds',
        'schedule': crontab(minute='*'),  # 每分钟执行一次
        'options': {
            'expires': 60,  # 1 分钟过期，避免堆积
        }
    },
}

if __name__ == '__main__':
    app.start()
