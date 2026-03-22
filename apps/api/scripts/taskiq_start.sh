#!/bin/bash
# TaskIQ 快速启动脚本 (替代旧版 Celery)

echo "🚀 启动 TaskIQ Scheduler 和 Worker..."
docker compose build --no-cache taskiq_scheduler taskiq_worker
docker compose up -d taskiq_scheduler taskiq_worker
echo "✅ 启动成功! 使用 'docker compose logs -f taskiq_worker' 查看日志"
