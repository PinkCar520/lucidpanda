# Collector V2 改进版设计文档

## 📋 功能对比

| 功能 | Celery | Collector V1 | Collector V2 |
|------|--------|-----------|------------|
| **定时调度** | ✅ Celery Beat | ✅ asyncio.sleep | ✅ 动态检查 |
| **并发控制** | ✅ Worker 并发 | ❌ 串行 | ✅ Semaphore (5 并发) |
| **失败重试** | ✅ 自动重试 | ❌ 仅日志 | ✅ 指数退避 (3 次) |
| **动态间隔** | ✅ 独立间隔 | ❌ 统一 2 分钟 | ✅ 独立配置 |
| **任务持久化** | ✅ Redis 队列 | ❌ 无 | ⚠️ Redis 统计 |
| **监控** | ✅ Flower UI | ❌ 仅日志 | ✅ Redis 统计 |
| **内存占用** | 385MB | 117MB | ~150MB |
| **复杂度** | 高 | 低 | 中 |

---

## 🎯 Collector V2 核心特性

### 1. 并发控制

```python
# 配置
MAX_CONCURRENT = 5  # 最大同时采集 5 个信源

# 实现
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def _fetch_with_retry(feed_config):
    async with self.semaphore:  # 限制并发
        return await self._fetch_single(feed_config)
```

**效果**:
- 避免同时发起 20 个请求导致网络拥塞
- 比串行快 4 倍（20 个信源 / 5 并发 = 4 轮）

---

### 2. 失败重试（指数退避）

```python
# 配置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 30  # 基础延迟 30 秒

# 重试逻辑
for attempt in range(MAX_RETRIES):
    try:
        return await fetch()
    except Exception as e:
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            # 第 1 次重试：30 秒
            # 第 2 次重试：60 秒
            # 第 3 次重试：120 秒
            await asyncio.sleep(delay)
```

**效果**:
- 网络抖动自动恢复
- 避免频繁重试压垮源站

---

### 3. 动态间隔

```python
# 配置
DEFAULT_INTERVALS = {
    "财联社 - 电报": 60,      # 1 分钟（快讯）
    "Bloomberg": 300,         # 5 分钟（新闻）
    "Fed Speeches": 900,      # 15 分钟（官方）
}

# 检查逻辑
async def _should_fetch(feed_name):
    stats = await _get_feed_stats(feed_name)
    elapsed = now - stats.last_fetch_at
    return elapsed >= stats.current_interval
```

**效果**:
- 快讯 60 秒采集一次（及时）
- 官方源 15 分钟采集一次（省资源）

---

### 4. 统计监控

```python
@dataclass
class FeedStats:
    feed_name: str
    last_fetch_at: str          # 上次采集时间
    last_success_at: str        # 上次成功时间
    last_error: str             # 最后错误信息
    consecutive_failures: int   # 连续失败次数
    total_fetches: int          # 总采集次数
    total_successes: int        # 总成功次数
    total_items: int            # 总采集条目
    avg_duration_ms: float      # 平均耗时

# 存储到 Redis
key = "lucidpanda:collector:stats:{feed_name}"
await redis.hset(key, mapping=asdict(stats))
```

**查询示例**:
```bash
# 查看财联社统计
docker exec lucidpanda_redis redis-cli HGETALL lucidpanda:collector:stats:财联社 - 电报
```

---

## 🚀 部署说明

### 启动 Collector V2

```bash
# 停止旧版 collector
docker compose stop collector

# 启动 V2
docker compose up -d collector_v2

# 查看日志
docker logs lucidpanda_collector_v2 --tail 30 -f
```

### 预期输出

```
============================================================
   LucidPanda Collector V2 启动
============================================================
📊 信源数量：20
🔀 最大并发：5
🔄 重试次数：3
⏱️  基础延迟：30 秒
============================================================
✅ 已连接 Redis: redis://redis:6379/0
🚀 [轮询 1] 开始采集 | 到期信源：20/20
📡 [财联社 - 电报] 开始采集 (尝试 1/3) [并发：5]
✅ [财联社 - 电报] 采集成功 | 15 条目 | 1234ms
...
✅ [轮询 1] 采集完成 | 入库：156 条 | 错误：0 | 耗时：12.3 秒
```

---

## 📊 性能预估

### 采集时间对比

| 信源数 | Collector V1 (串行) | Collector V2 (5 并发) | Celery (4 Worker) |
|--------|-------------------|---------------------|------------------|
| 20 个 | 60 秒 | 12 秒 | 15 秒 |
| 单信源失败 | 等 2 分钟 | 30 秒后重试 | 60 秒后重试 |

### 内存占用

| 组件 | Collector V1 | Collector V2 | Celery |
|------|-------------|-------------|--------|
| **采集器** | 117MB | ~150MB | 385MB |
| **Redis** | 50MB | 55MB (+统计) | 50MB |
| **总计** | 167MB | 205MB | 435MB |

---

## 🔧 配置调优

### 调整并发数

```python
# collector_v2.py
MAX_CONCURRENT = 5  # 改为 3 或 10
```

### 调整重试策略

```python
MAX_RETRIES = 5              # 增加重试次数
RETRY_BASE_DELAY = 10        # 减少基础延迟（更激进）
```

### 调整采集间隔

```python
DEFAULT_INTERVALS = {
    "财联社 - 电报": 30,     # 更快（但可能触发反爬）
    "Bloomberg": 600,        # 降低频率
}
```

---

## ⚠️ 注意事项

1. **Redis 持久化**: 统计信息存储 7 天自动过期
2. **网络代理**: 境外源仍需要 sing-box 代理
3. **数据库连接**: 确保 PostgreSQL 连接池足够（建议 20+）
4. **日志量**: 开启详细日志会占用更多磁盘空间

---

## 📈 监控建议

### 1. 采集成功率

```bash
# 查询连续失败 >3 次的信源
docker exec lucidpanda_redis redis-cli --scan | grep stats | xargs -I {} redis-cli HGET {} consecutive_failures
```

### 2. 平均耗时

```bash
# 查看平均采集耗时
docker exec lucidpanda_redis redis-cli HGETALL lucidpanda:collector:stats:财联社 - 电报 | grep avg_duration_ms
```

### 3. 采集频率

```bash
# 查看上次采集时间
docker exec lucidpanda_redis redis-cli HGET lucidpanda:collector:stats:财联社 - 电报 last_fetch_at
```

---

## 🎯 总结

**Collector V2 相比 Celery 的优势**:
- ✅ 内存节省 53%（205MB vs 435MB）
- ✅ 代码简单（无消息队列复杂度）
- ✅ 功能足够（并发 + 重试 + 动态间隔）

**Collector V2 相比 V1 的改进**:
- ✅ 并发采集（快 4 倍）
- ✅ 失败重试（更可靠）
- ✅ 动态间隔（更灵活）
- ✅ 统计监控（可观测）

**推荐使用 Collector V2** 替代 Celery！
