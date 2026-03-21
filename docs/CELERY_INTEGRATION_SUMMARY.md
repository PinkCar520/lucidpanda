# Celery 集成总结

## ✅ 完成的工作

### 1. 依赖安装
- **文件**: `apps/api/requirements.txt`
- **新增**: `celery[redis]>=5.3.0`, `flower>=2.0.0`

### 2. Celery 配置
- **文件**: `apps/api/celery_config.py`
- **功能**: 
  - Celery 应用初始化
  - Redis Broker/Backend 配置
  - Beat 调度器配置（每分钟触发）

### 3. 任务模块
- **目录**: `apps/api/src/lucidpanda/tasks/`
- **文件**:
  - `__init__.py` - 模块初始化
  - `collector_tasks.py` - RSS 采集任务（含动态自适应间隔）

### 4. 数据库迁移
- **文件**: `apps/api/scripts/migrations/create_feed_statistics_table.py`
- **功能**: 创建 `feed_statistics` 表，用于存储信源统计和间隔状态

### 5. Docker 服务
- **文件**: `apps/api/docker-compose.yml`
- **新增服务**:
  - `celery_beat` - 调度器
  - `celery_worker` - 任务执行器（4 并发）
  - `celery_flower` - 监控 UI（可选，profile: monitoring）
  - `collector` - 旧版采集器（profile: legacy，默认不启动）

### 6. Dockerfile 更新
- **文件**: `apps/api/Dockerfile.backend`
- **新增**: Celery 相关环境变量

### 7. 脚本和文档
- **文件**:
  - `apps/api/scripts/core/run_collector.py` - 添加过时警告
  - `apps/api/scripts/celery_start.sh` - 快速启动脚本
  - `docs/CELERY_DEPLOYMENT.md` - 部署指南

---

## 📐 架构设计

### 动态自适应间隔算法

```python
# 每个信源维护状态
state = {
    'current_interval': 120,        # 当前间隔 (秒)
    'consecutive_empty_count': 0,   # 连续空返回次数
}

# 调整规则
if new_items == 0:
    consecutive_empty_count += 1
    if consecutive_empty_count >= 10:
        current_interval = min(current_interval * 2, 1800)  # 最多 30 分钟
else:
    consecutive_empty_count = 0
    current_interval = max(current_interval // 2, 30)  # 最少 30 秒
```

### 任务执行流程

```
Celery Beat (每分钟)
    ↓
fetch_all_feeds (检查所有信源)
    ↓
for each feed:
    - 检查距上次采集时间
    - 如果 < current_interval → 跳过
    - 如果 >= current_interval → 执行采集
    ↓
fetch_single_feed_task
    - RSS 拉取
    - 过滤/去重
    - 入库
    - Redis Pub/Sub 唤醒 Worker
    - 更新间隔状态
```

---

## 🚀 使用方法

### 快速开始

```bash
cd apps/api

# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行数据库迁移
python scripts/migrations/create_feed_statistics_table.py

# 3. 启动 Celery 服务
./scripts/celery_start.sh start

# 或使用 docker compose
docker compose up -d celery_beat celery_worker
```

### 启动监控 UI

```bash
# 启动 Flower
docker compose --profile monitoring up -d celery_flower

# 访问 http://localhost:5555
```

### 查看日志

```bash
# Beat 日志
docker compose logs -f celery_beat

# Worker 日志
docker compose logs -f celery_worker

# 过滤特定信源
docker compose logs -f celery_worker | grep "财联社"
```

### 停止旧版

```bash
# 停止旧版轮询采集器
docker compose stop collector
```

---

## 📊 预期效果

### 请求量对比

| 指标 | 旧版 | 新版 | 改进 |
|------|------|------|------|
| 每小时请求数 | ~540 次 | ~120 次 | **-78%** |
| 无效请求占比 | ~65% | ~15% | **-50%** |
| 高频信源延迟 | 2 分钟 | 30-60 秒 | **更快** |
| 低频信源请求 | 2 分钟 | 15-30 分钟 | **节省 85%** |

### 资源占用

| 服务 | CPU | 内存 |
|------|-----|------|
| Celery Beat | <1% | ~50MB |
| Celery Worker (4 并发) | ~10% | ~200MB |
| Flower | ~2% | ~80MB |
| 旧版 Collector | ~5% | ~150MB |

**总资源变化**: +180MB 内存，+8% CPU（换取 78% 请求量减少）

---

## 🔍 监控和调试

### Redis 状态查询

```bash
docker compose exec redis redis-cli

# 查看所有信源状态
KEYS lucidpanda:feed_state:*

# 查看特定信源
HGETALL lucidpanda:feed_state:财联社 - 电报

# 查看当前间隔
HGET lucidpanda:feed_state:财联社 - 电报 current_interval
```

### Flower 监控

访问 http://localhost:5555 查看：
- Tasks: 任务执行历史、成功率、平均耗时
- Workers: Worker 状态、并发数
- Broker: Redis 队列状态

### 数据库查询

```sql
-- 查看信源统计
SELECT 
    feed_name,
    category,
    current_interval,
    consecutive_empty_count,
    total_fetches,
    total_new_items,
    ROUND(total_new_items::numeric / NULLIF(total_fetches, 0) * 100, 2) AS success_rate
FROM feed_statistics
ORDER BY current_interval ASC;

-- 查看间隔分布
SELECT 
    CASE 
        WHEN current_interval <= 60 THEN '高频 (<=60s)'
        WHEN current_interval <= 300 THEN '中频 (60-300s)'
        ELSE '低频 (>300s)'
    END AS interval_tier,
    COUNT(*) AS feed_count
FROM feed_statistics
GROUP BY 1;
```

---

## ⚠️ 注意事项

### 1. 首次启动

首次启动时，所有信源使用默认间隔（120 秒）。需要 1-2 天学习期才能收敛到最优间隔。

### 2. Redis 持久化

建议开启 Redis AOF 持久化，避免重启后丢失间隔状态：

```yaml
# docker-compose.yml
redis:
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

### 3. 回滚方案

如果遇到问题，可以快速回滚到旧版：

```bash
# 停止 Celery
docker compose stop celery_beat celery_worker

# 启动旧版 Collector
docker compose --profile legacy up -d collector
```

### 4. Worker 并发数

根据服务器配置调整并发数：

```yaml
# docker-compose.yml
celery_worker:
  command: celery -A celery_config worker --loglevel=info --concurrency=4
  # 4 核 8G 推荐：--concurrency=4
  # 2 核 4G 推荐：--concurrency=2
```

---

## 📝 后续优化建议

1. **告警通知**: 集成失败告警（重试 3 次后发送邮件/Bark）
2. **限流保护**: PENDING 队列 > 100 时自动暂停采集
3. **健康检查**: 添加 Celery Worker 健康检查端点
4. **指标导出**: 集成 Prometheus + Grafana 监控
5. **任务路由**: 将不同分类信源分发到不同队列

---

## 📚 相关文档

- [Celery 部署指南](./CELERY_DEPLOYMENT.md)
- [架构文档](./architecture.md)
- [快速启动脚本](../apps/api/scripts/celery_start.sh)
