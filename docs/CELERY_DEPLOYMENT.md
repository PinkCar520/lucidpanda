# Celery 部署指南

## 概述

LucidPanda 现已集成 Celery 任务队列，用于 RSS 采集的动态自适应间隔调度。

## 架构变化

### 之前
```
Collector (固定 2 分钟轮询) → PostgreSQL → Worker
```

### 之后
```
Celery Beat (每分钟检查) → Celery Worker (动态间隔) → PostgreSQL → Worker
                              ↓
                         Redis (状态存储)
                              ↓
                      Flower (监控 UI, 可选)
```

## 快速开始

### 1. 安装依赖

```bash
cd apps/api
pip install -r requirements.txt
```

新增依赖：
- `celery[redis]>=5.3.0`
- `flower>=2.0.0`

### 2. 数据库迁移

运行迁移脚本创建 `feed_statistics` 表：

```bash
cd apps/api
python scripts/migrations/create_feed_statistics_table.py
```

### 3. Docker Compose 启动

#### 启动 Celery 服务（推荐）

```bash
# 启动 Celery Beat + Worker
docker compose up -d celery_beat celery_worker

# 查看日志
docker compose logs -f celery_beat
docker compose logs -f celery_worker
```

#### 启动监控 UI（可选）

```bash
# 启动 Flower 监控
docker compose --profile monitoring up -d celery_flower

# 访问 http://localhost:5555
```

#### 停止旧版 Collector

```bash
# 停止旧版轮询采集器
docker compose stop collector
```

### 4. 本地开发模式

```bash
# 终端 1: 启动 Celery Beat
cd apps/api
celery -A celery_config beat --loglevel=info

# 终端 2: 启动 Celery Worker
celery -A celery_config worker --loglevel=info --concurrency=4

# 终端 3: 启动 Flower (可选)
celery -A celery_config flower --port=5555
```

## 动态自适应间隔

### 工作原理

每个信源维护一个状态（存储在 Redis）：

```python
{
    'current_interval': 120,        # 当前间隔 (秒)
    'consecutive_empty_count': 0,   # 连续空返回次数
    'total_fetches': 100,           # 总采集次数
    'total_new_items': 25,          # 总新增情报数
    'last_fetch_at': '2026-03-21T...',
    'last_new_item_at': '2026-03-21T...',
}
```

### 调整规则

- **空返回**: 连续 10 次空返回 → 间隔 ×2 (上限 30 分钟)
- **有新增**: 间隔 ÷2 (下限 30 秒)

### 默认间隔配置

| 信源类型 | 信源示例 | 默认间隔 |
|---------|---------|---------|
| 高频快讯 | 财联社 - 电报 | 60 秒 |
| 中频新闻 | Bloomberg, WSJ | 300 秒 |
| 低频官方 | WhiteHouse, Fed | 900 秒 |

## 监控

### Celery Flower

访问 http://localhost:5555 查看：
- 任务执行历史
- 任务成功率
- Worker 状态
- 队列长度

### Redis 状态查询

```bash
# 查看信源状态
docker compose exec redis redis-cli
> KEYS lucidpanda:feed_state:*
> HGETALL lucidpanda:feed_state:财联社 - 电报
```

### 日志查看

```bash
# Celery Beat 日志
docker compose logs -f celery_beat

# Celery Worker 日志
docker compose logs -f celery_worker

# 过滤特定信源日志
docker compose logs -f celery_worker | grep "财联社"
```

## 配置调优

### celery_config.py

```python
# 调整调度频率
app.conf.beat_schedule = {
    'fetch-all-feeds': {
        'task': 'src.lucidpanda.tasks.collector_tasks.fetch_all_feeds',
        'schedule': crontab(minute='*'),  # 每分钟
    },
}

# 调整 Worker 并发数
# docker-compose.yml 中修改 --concurrency=4
```

### 环境变量

```bash
# .env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

## 故障排查

### 问题 1: Celery Worker 不执行任务

```bash
# 检查 Redis 连接
docker compose exec redis redis-cli ping

# 检查任务注册
celery -A celery_config inspect registered

# 检查 Worker 状态
celery -A celery_config inspect stats
```

### 问题 2: 任务一直显示 PENDING

```bash
# 检查 Redis 中的任务结果
docker compose exec redis redis-cli
> KEYS celery-task-meta-*
```

### 问题 3: 数据库连接失败

```bash
# 检查数据库连接
docker compose exec db pg_isready

# 查看数据库日志
docker compose logs db
```

## 回滚到旧版

如果需要回滚到旧版固定间隔轮询：

```bash
# 停止 Celery 服务
docker compose stop celery_beat celery_worker celery_flower

# 启动旧版 Collector
docker compose --profile legacy up -d collector
```

## 性能预期

### 请求量对比

| 模式 | 每小时请求数 | 无效请求占比 |
|------|-------------|-------------|
| 旧版 (固定 2 分钟) | ~540 次 | ~65% |
| 新版 (动态间隔) | ~120 次 | ~15% |

### 资源占用

| 服务 | CPU | 内存 |
|------|-----|------|
| Celery Beat | <1% | ~50MB |
| Celery Worker (4 并发) | ~10% | ~200MB |
| Flower | ~2% | ~80MB |

## 下一步

1. 运行数据库迁移
2. 启动 Celery 服务
3. 观察 24 小时，确认间隔自适应正常
4. 停止旧版 Collector
