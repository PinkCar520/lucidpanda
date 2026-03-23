# 新闻抓取与分类逻辑说明

LucidPanda 的新闻抓取系统将情报分为三个核心维度：
1. **macro_gold** (黄金宏观)
2. **equity_cn** (A股政策与快讯)
3. **equity_us** (美股权益与行业)

### 分类处理流程

分类逻辑分为两个阶段执行：

#### 1. 基于配置的分组 (抓取前)
每个 RSS 信源在配置文件中预先分配了所属分类 ([rsshub.py](file:///Users/caomeifengli/workspace/lucidpanda/apps/api/src/lucidpanda/providers/data_sources/rsshub.py))。

- **黄金 (macro_gold)**: 包含 Trump Truth Social、白宫行政令、美联储演讲、彭博经济新闻等宏观相关渠道。
- **A股 (equity_cn)**: 包含华尔街见闻-A股、上交所、深交所等国内权威渠道。
- **美股 (equity_us)**: 包含 CNBC 科技、彭博市场、WSJ 市场、路透商业等国际金融渠道。

#### 2. 关键词动态过滤 (抓取后，入库前)
在从信源获取原始数据后，系统会根据该分类对应的关键词桶进行二次验证 ([_passes_category_filter](file:///Users/caomeifengli/workspace/lucidpanda/apps/api/src/lucidpanda/providers/data_sources/rsshub.py#L116-125))。
- **黄金宏观过滤**: 匹配 `gold`, `xau`, `fed`, `inflation`, `cpi`, `trump`, `tariff` 等词。
- **A股政策过滤**: 匹配 `指导意见`, `降准`, `降息`, `证监会`, `半导体`, `新质生产力` 等词，或内容长度 > 100 字。
- **美股权益过滤**: 匹配 `earnings`, `revenue`, `nvidia`, `apple`, `tesla`, `fed` 等词。

### 数据库存储
经过过滤的新闻会被保存到 PostgreSQL 的 `intelligence` 表中，并持久化其 `category` 字段 ([intelligence.py](file:///Users/caomeifengli/workspace/lucidpanda/apps/api/src/lucidpanda/db/intelligence.py#L565))。

### 总结
- **是否分组？** 是对的，分为 3 大核心类别。
- **抓取前还是后？** 混合模式：**信源**在抓取前按分类配置，**内容**在抓取后按关键词精细过滤。

---

### 移动端 API 过滤策略

在后端 API 层（`apps/api/src/lucidpanda/api/v1/routers/mobile.py`），对展示给 iOS 端的情报进行了进一步过滤：

1. **信息流 (Feed) 过滤**:
   - 接口 `GET /api/v1/mobile/intelligence` 显式过滤了 `category == "macro_gold"`。
   - **结果**: 目前 iOS 的主信息流中仅展示“黄金宏观”类情报。

2. **状态与质量过滤**:
   - 仅展示 `status == "COMPLETED"`（已完成 AI 分析）且 `summary`（摘要）非空的记录。

3. **紧急度聚合 (Market Pulse)**:
   - 接口 `GET /api/v1/mobile/market/pulse` 会聚合过去 24 小时内所有分类中 `urgency_score >= 7` 的高紧急度情报。
