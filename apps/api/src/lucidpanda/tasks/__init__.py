"""
LucidPanda Celery 任务模块
===========================
所有异步任务定义在此模块中
"""
from celery_config import app

__all__ = ['app']

# 导入所有任务模块，确保 Celery 能发现任务
from . import collector_tasks
