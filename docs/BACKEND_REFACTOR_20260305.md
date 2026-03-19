# LucidPanda 后端架构重构文档

> 本文记录 2026-03 迭代完成的所有后端重构，包括部署方案与验证清单。

---

## 一、本次迭代内容概览

| 模块 | 变更 | 影响 |
|------|------|------|
| **RSS采集/AI分析解耦** | `RSSCollector` 独立进程 | 采集失败不影响分析 |
| **监管信源扩充** | +Fed/SEC/CFTC 4个 feed | 24 → 29 个信源 |
| **DB 分域拆分** | `database.py` 1803行 → 5模块 | 可维护性大幅提升 |
| **事件聚类** | Union-Find + pg_trgm | 同事件去重，只推 1 条 |

---

## 二、新文件清单

```
src/lucidpanda/
├── core/
│   ├── rss_collector.py        # 采集器（生产者）
│   ├── event_clusterer.py      # 事件聚类（Union-Find + pg_trgm）
│   └── engine.py               # 纯分析消费者（修改）
├── db/                         # NEW — 数据库分域模块
│   ├── __init__.py             # IntelligenceDB facade
│   ├── base.py                 # 连接池 + 建表 Schema
│   ├── intelligence.py         # 情报 CRUD / 去重 / 向量
│   ├── market.py               # 市场快照 / 指标 / 时段
│   └── fund.py                 # 基金 / 持仓 / 估值 / 自选单
run_collector.py                # 采集器入口（每2分钟）
```

**兼容性**：`core/database.py` 保留为 5 行转发层，全项目所有导入无需修改。

---

## 三、数据库变更（Migration）

新增字段（worker 启动时自动 ALTER TABLE，幂等安全）：

```sql
-- 事件聚类
ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS event_cluster_id TEXT;
ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS is_cluster_lead BOOLEAN DEFAULT TRUE;
```

新 status 值：`CLUSTERED` — 同事件被抑制，跳过AI分析和推送。

---

## 四、部署步骤

### 4.1 构建新镜像

```bash
# 在服务器上拉取最新代码
cd ~/lucidpanda
git pull origin main

# 构建并推送镜像
docker build -t pincar/lucidpanda-backend:latest .
docker push pincar/lucidpanda-backend:latest
```

### 4.2 滚动更新（零停机）

```bash
# 重启 collector（新进程）
docker compose pull
docker compose up -d --no-deps collector

# 重启 worker（包含新 EventClusterer）
docker compose up -d --no-deps worker

# 查看状态
docker compose ps
```

### 4.3 Migration 验证（DB字段）

```bash
# 登录 DB 确认新字段存在
docker exec -it lucidpanda_db psql -U lucidpanda -d lucidpanda -c \
  "SELECT column_name FROM information_schema.columns
   WHERE table_name='intelligence' AND column_name LIKE 'event_%';"

# 期望输出:
#  event_cluster_id
#  is_cluster_lead
```

---

## 五、验证清单

### 5.1 容器健康

```bash
# 全部容器应处于 Up 状态
docker compose ps

# 采集器：每2分钟应有日志
docker compose logs -f collector | grep "✅ 本轮采集"

# Worker：应处理 PENDING 记录
docker compose logs -f worker | grep "完成"
```

### 5.2 信源采集验证（29个）

```bash
# 查询最近1小时新增记录数，按 source_name 分组
docker exec lucidpanda_db psql -U lucidpanda -d lucidpanda -c "
  SELECT source_name, COUNT(*) as cnt
  FROM intelligence
  WHERE timestamp > NOW() - INTERVAL '1 hour'
  GROUP BY source_name
  ORDER BY cnt DESC;"

# 期望：应看到 Fed/SEC/CFTC 的记录出现
```

### 5.3 事件聚类验证

```bash
# 查询被聚类抑制的记录
docker exec lucidpanda_db psql -U lucidpanda -d lucidpanda -c "
  SELECT
    event_cluster_id,
    COUNT(*) AS total,
    SUM(CASE WHEN is_cluster_lead THEN 1 ELSE 0 END) AS leads,
    SUM(CASE WHEN status='CLUSTERED' THEN 1 ELSE 0 END) AS suppressed
  FROM intelligence
  WHERE event_cluster_id IS NOT NULL
  GROUP BY event_cluster_id
  ORDER BY total DESC
  LIMIT 10;"

# Worker 日志中应出现聚类日志
docker compose logs worker | grep "🔗 聚类压制"
```

### 5.4 信源可信度

```bash
# 查询信源可信度排名（需要一定数据积累后才有结果）
docker exec lucidpanda_db psql -U lucidpanda -d lucidpanda -c "
  SELECT source_name, ROUND(AVG(source_credibility_score)::numeric,3) AS accuracy
  FROM intelligence
  WHERE source_credibility_score IS NOT NULL
  GROUP BY source_name
  ORDER BY accuracy DESC LIMIT 10;"
```

### 5.5 DB 分域模块导入测试

```bash
# 在服务器容器内验证新模块可正确导入
docker exec lucidpanda_worker python -c "
from src.lucidpanda.core.database import IntelligenceDB
print('Import OK — methods:', len([m for m in dir(IntelligenceDB) if not m.startswith('_')]))"

# 期望: Import OK — methods: 48
```

### 5.6 端到端流测试

```bash
# 新增一条测试记录，观察完整流程
docker exec lucidpanda_worker python -c "
from src.lucidpanda.db import IntelligenceDB
db = IntelligenceDB()
exists = db.source_id_exists('test-deploy-check-001')
print('DB连接正常:', not exists or '已存在')"
```

---

## 六、回滚方案

```bash
# 如需回滚到上一版本
IMAGE_TAG=<previous_tag>  # 从 docker hub 查历史 tag
docker compose down worker collector
IMAGE_TAG=$IMAGE_TAG docker compose up -d worker collector
```

> [!WARNING]
> 回滚后 `event_cluster_id` 和 `is_cluster_lead` 字段仍存在（ALTER TABLE IF NOT EXISTS 是幂等的），不影响已有数据。

---

## 七、监控建议

```bash
# 推荐加入 crontab 或 Prometheus 监控指标
# 每小时统计：
# - PENDING 积压量（> 50 需告警）
# - CLUSTERED 抑制比例（正常 5~30%）
# - COMPLETED 分析量

docker exec lucidpanda_db psql -U lucidpanda -d lucidpanda -c "
  SELECT status, COUNT(*) FROM intelligence
  WHERE timestamp > NOW() - INTERVAL '1 hour'
  GROUP BY status ORDER BY count DESC;"
```
