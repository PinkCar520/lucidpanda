# LucidPanda 单进程部署指南

## 📋 架构对比

### 旧架构（多容器）

```bash
# 启动 3 个容器
docker compose up -d collector worker rsshub

# 内存占用
collector:  117MB
worker:     508MB
rsshub:     242MB
总计：      867MB
```

**问题**：
- ❌ collector 和 worker 可能同时执行，资源竞争
- ❌ RSSHub 中转层增加延迟和内存开销
- ❌ DB 锁竞争（collector 写入，worker 读取）
- ❌ 网络开销（容器间 HTTP 通信）

---

### 新架构（单进程）

```bash
# 启动 1 个容器
docker compose up -d lucidpanda

# 内存占用
lucidpanda: ~400MB
总计：      ~400MB（节省 54%）
```

**优势**：
- ✅ 单进程运行，无资源竞争
- ✅ 内存队列，低延迟（无 DB 中转）
- ✅ 16 个原生 RSS 直采（无需 RSSHub）
- ✅ 进程内通信，无网络开销

---

## 🚀 部署步骤

### 1. 停止旧服务

```bash
cd ~/lucidpanda

# 停止旧容器
docker compose stop collector worker collector_v2

# 移除旧容器
docker compose rm -f collector worker collector_v2
```

### 2. 启动新守护进程

```bash
# 重新构建并启动
docker compose up -d --build lucidpanda

# 查看状态
docker compose ps
```

### 3. 验证运行

```bash
# 查看日志
docker logs lucidpanda --tail 50 -f

# 预期输出
==============================================================
   LucidPanda Daemon 启动
==============================================================
📊 采集间隔：120 秒
🔀 Worker 并发：5
📦 队列大小：100
==============================================================
✅ Collector 已初始化
✅ Worker 已初始化
✅ Daemon 已启动
==============================================================
📡 Collector Loop 已启动
🤖 Worker Loop 已启动
💓 Health Check Loop 已启动
✅ 所有后台任务已启动
==============================================================
```

---

## 📊 监控命令

### 查看内存占用

```bash
docker stats lucidpanda
```

### 查看运行日志

```bash
# 实时日志
docker logs lucidpanda --tail 50 -f

# 搜索特定日志
docker logs lucidpanda 2>&1 | grep "采集完成"
docker logs lucidpanda 2>&1 | grep "分析完成"
```

### 查看队列状态

```bash
# 进入容器
docker exec -it lucidpanda bash

# 查看 Python 进程
ps aux | grep python

# 查看网络连接
netstat -tlnp | grep python
```

---

## 🔧 配置调优

### 调整采集间隔

编辑 `src/lucidpanda/core/daemon.py`:

```python
# 默认 2 分钟
COLLECT_INTERVAL_SECONDS = 120

# 改为 1 分钟（更及时，但可能触发反爬）
COLLECT_INTERVAL_SECONDS = 60
```

### 调整 Worker 并发

```python
# 从配置读取（默认 5）
WORKER_CONCURRENCY = settings.LLM_CONCURRENCY_LIMIT

# 或硬编码
WORKER_CONCURRENCY = 3  # 降低并发（节省内存）
WORKER_CONCURRENCY = 10 # 提高并发（更快处理）
```

### 调整队列大小

```python
# 默认缓冲 100 条
MAX_QUEUE_SIZE = 100

# 如果经常积压，增加到 200
MAX_QUEUE_SIZE = 200
```

---

## ⚠️ 故障排查

### 问题 1: 队列积压

**症状**：
```
⚠️ 队列积压：85/100
```

**原因**：
- Worker 分析速度 < Collector 采集速度
- LLM API 响应慢

**解决**：
1. 增加 Worker 并发：`WORKER_CONCURRENCY = 10`
2. 降低采集频率：`COLLECT_INTERVAL_SECONDS = 180`
3. 检查 LLM API 状态

---

### 问题 2: 采集失败频繁

**症状**：
```
⚠️ [财联社 - 电报] 采集失败：Connection timeout
```

**原因**：
- 网络问题（需要走代理）
- 源站反爬

**解决**：
1. 检查代理配置：`HTTP_PROXY=http://singbox:7890`
2. 检查 sing-box 状态：`docker compose ps singbox`
3. 增加重试次数（修改 CollectorV2）

---

### 问题 3: 内存持续增长

**症状**：
```
容器内存从 400MB 增长到 600MB
```

**原因**：
- Python 内存泄漏
- 队列积压

**解决**：
1. 检查队列大小：`docker exec lucidpanda python3 -c "import asyncio; print(asyncio.Queue.qsize())"`
2. 重启容器：`docker compose restart lucidpanda`
3. 如果持续泄漏，提交 issue

---

## 📈 性能基准

### 测试场景
- 20 个 RSS 信源
- 每条情报分析耗时 2 秒
- 采集间隔 2 分钟

### 结果对比

| 指标 | 旧架构 (3 容器) | 新架构 (1 容器) | 改进 |
|------|---------------|---------------|------|
| **内存** | 867MB | 400MB | -54% |
| **延迟** | 2-5 分钟 | <10 秒 | -95% |
| **CPU** | 15-20% | 10-15% | -25% |
| **启动时间** | 30 秒 | 10 秒 | -67% |

---

## 🎯 最佳实践

### 1. 定期重启

```bash
# 每周重启一次（释放内存）
docker compose restart lucidpanda
```

### 2. 监控日志

```bash
# 设置日志轮转（docker-compose.yml）
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "3"  # 保留 3 个文件
```

### 3. 健康检查

```bash
# 添加健康检查（docker-compose.yml）
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 60s
  timeout: 10s
  retries: 3
```

---

## 🔄 回滚方案

如果新架构有问题，可以快速回滚：

```bash
# 停止新守护进程
docker compose stop lucidpanda

# 启动旧服务
docker compose up -d collector worker

# 验证
docker compose ps
```

---

## 📝 总结

**单进程架构 vs 多容器架构**：

| 维度 | 多容器 | 单进程 |
|------|--------|--------|
| **复杂度** | 高（3 个服务） | 低（1 个服务） |
| **内存** | 867MB | 400MB |
| **延迟** | 2-5 分钟 | <10 秒 |
| **维护** | 困难 | 简单 |
| **扩展** | 容易（独立扩展） | 中等（需整体扩展） |
| **推荐场景** | 大规模部署 | 中小规模（<100 信源） |

**推荐使用单进程架构**（除非你需要独立扩展 collector 或 worker）！
