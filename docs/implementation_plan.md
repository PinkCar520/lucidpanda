# 实现方案：Market Pulse 悬浮胶囊 + 长按基金 AI 分析

## 背景

经过对项目代码的深度分析，梳理出以下现有能力和缺口：

### ✅ 现有能力（可直接利用）
| 资产 | 位置 | 用途 |
|------|------|------|
| [Intelligence](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/models/intelligence.py#36-40) 表 | [models/intelligence.py](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/models/intelligence.py) | 有 [summary(zh)](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/api/v1/routers/mobile.py#38-52), `actionable_advice(zh)`, [entities](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/db/intelligence.py#19-37), `sentiment`, `market_implication` 等 AI 生成字段 |
| `market_terminal_service` | [services/market_terminal_service.py](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/services/market_terminal_service.py) | 实时黄金/美元指数/原油/美债快照，15s 缓存 |
| `/api/v1/market/snapshot` | [routers/mobile.py](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/api/v1/routers/mobile.py) | 已有市场快照 endpoint |
| `/api/v1/intelligence` | [routers/mobile.py](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/api/v1/routers/mobile.py) | 已有情报 feed endpoint |
| `IntelligenceDB.get_recent_intelligence()` | [db/intelligence.py](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/db/intelligence.py) | 可获取最近 N 条已分析情报 |
| `fund_watchlist` 表 | DB | 用户自选列表，有 `fund_code`, `fund_name` |

### ✅ 已实现能力
- **宏观摘要 API**: `GET /api/v1/mobile/market/pulse` 已上线，支持行情快照与情绪聚合。
- **基金 AI 分析 API**: `GET /api/v1/web/watchlist/{fund_code}/ai_analysis` 已上线，支持 **混合检索 (Hybrid Search)**：
    - **关键词匹配**: 基于 `normalize_fund_name` 剥离冗余后缀，提升匹配精度。
    - **语义检索**: 接入 `pgvector`，通过 `BERT` 向量计算实现跨语意关联。
- **性能优化**: 核心计算逻辑已切换至 `sentiment_score` 浮点列，性能大幅提升。
- **Redis 缓存**: 已实现全局与个人级别的读穿/写回缓存机制（30s/60s）。

---

## 功能一：悬浮胶囊 Market Pulse（全局宏观视角）

### 定位
点击胶囊 → 打开 AI 宏观分析弹窗，内容覆盖：**今日大盘情绪 + 四大品种行情 + 最新高紧急度情报摘要**

### 后端 API 设计

**新增 endpoint：`GET /api/v1/market/pulse`**

```python
# routers/mobile.py 新增

@router.get("/market/pulse", response_model=Dict[str, Any])
async def get_market_pulse(db: Session = Depends(get_session)):
    """
    宏观市场脉搏：四大品种快照 + 今日整体情绪 + Top3 高紧急情报摘要
    """
    # 1. 四大品种快照（已有）
    snapshot = market_terminal_service.get_market_snapshot()

    # 2. 最新 Top3 高紧急度情报摘要（从 intelligence 表，urgency_score >= 7）
    stmt = select(Intelligence).where(
        Intelligence.urgency_score >= 7
    ).order_by(Intelligence.timestamp.desc()).limit(3)
    top_alerts = db.exec(stmt).all()
    
    # 3. 聚合今日整体情绪（sentiment_score 均值）
    # 用近 24h 情报的 sentiment_score 均值
    # SELECT AVG(sentiment_score) FROM intelligence WHERE timestamp > NOW() - INTERVAL '24h'

    return {
        "market_snapshot": snapshot,
        "top_alerts": [...],  # 展平的情报摘要列表
        "overall_sentiment": "bullish|bearish|neutral",
        "sentiment_score": 0.32,
        "generated_at": now
    }
```

### 数据流

```
iOS 点击胶囊
  → GET /api/v1/market/pulse
  → MarketTerminalService（实时行情）
  → Intelligence 表（近24h高紧急度情报）
  → 返回聚合 JSON
  → iOS 展示 Bottom Sheet
```

### iOS UI 设计
```
┌─────────────────────────────────────┐
│ 🌐 市场脉搏  [今日整体：偏多 ▲]     │
├─────────────────────────────────────┤
│ 黄金 ▲1.2%   美元↓-0.3%            │
│ 原油 ▲2.1%   美债 4.21%↑           │
├─────────────────────────────────────┤
│ 🔴 高紧急  | 美联储官员暗示...       │
│ 🟡 中紧急  | 非农数据超预期...       │
│ 🟢 低紧急  | 中国PMI公布...         │
└─────────────────────────────────────┘
```

---

## 功能二：长按基金 → AI 市场分析弹窗

### 定位
长按自选列表中的基金 → 弹出该基金的专项 AI 分析，包含：**基金基本信息 + 关联情报（通过 entities 字段匹配）+ AI 可操作建议**

### 核心难点：情报 ↔ 基金关联

当前 `Intelligence.entities` 是 JSONB 数组，结构如：
```json
[{"name": "华夏基金", "type": "company"}, {"name": "科技ETF", "type": "etf"}]
```

关联策略（成本从低到高）：
1. **关键词匹配（优先）**：用 `fund_name` 对 [entities](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/db/intelligence.py#19-37) JSONB 做 `@>` 或 `content` 做 `ILIKE` 全文搜索
2. **pgvector 语义搜索（后续）**：[embedding_vec](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/db/intelligence.py#93-107) 字段已存在，后续可做语义检索

### 后端 API 设计

**新增 endpoint：`GET /api/v1/watchlist/{fund_code}/ai_analysis`**

```python
# routers/watchlist_v2.py 新增

@router.get("/{fund_code}/ai_analysis", response_model=Dict[str, Any])
async def get_fund_ai_analysis(
    fund_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    单支基金 AI 分析：
    - 验证基金在用户自选列表中
    - 查询关联情报（entities 匹配 or content ILIKE）
    - 返回市场行情快照 + 情报摘要 + 可操作建议
    """
    # 1. 验证权限并获取基金名
    row = db.execute(text("""
        SELECT fund_name FROM fund_watchlist
        WHERE user_id = :uid AND fund_code = :code AND is_deleted = FALSE
    """), {"uid": str(current_user.id), "code": fund_code}).first()
    if not row:
        raise HTTPException(404, "基金不在自选列表")
    fund_name = row[0]
    core_name = normalize_fund_name(fund_name)

    # 2. 混合检索（近7天，Top 5）
    # 2.1 关键词 ILIKE
    kw_results = db.execute(text("SELECT ... FROM intelligence WHERE ... ILIKE :kw ..."), {"kw": f"%{core_name}%"}).all()
    # 2.2 语义 pgvector
    vec = embedding_service.encode(core_name)
    vec_results = db.execute(text("SELECT ... FROM intelligence ORDER BY embedding_vec <=> :vec LIMIT 5"), {"vec": vec}).all()

    # 3. 结果去重与排序
    related = merge_and_sort(kw_results, vec_results)

    # 3. 市场快照
    snapshot = market_terminal_service.get_market_snapshot()

    return {
        "fund_code": fund_code,
        "fund_name": fund_name,
        "market_snapshot": snapshot,
        "related_intelligence": [...],  # 情报摘要列表
        "has_data": len(related) > 0,
        "generated_at": now
    }
```

### 数据流

```
iOS 长按基金 cell
  → 触发 haptic feedback
  → GET /api/v1/watchlist/{fund_code}/ai_analysis
  → 1. 验证权限
  → 2. pg ILIKE 匹配关联情报
  → 3. MarketTerminalService 快照
  → 返回聚合 JSON
  → iOS 展示 Bottom Sheet / 半展开 Modal
```

### iOS UI 设计
```
┌─────────────────────────────────────┐
│ 📊 华夏科技ETF (515230)             │
│ [今日行情] [相关情报] [AI建议]       │
├─────────────────────────────────────┤
│ 🤖 AI 分析                          │
│ "近期半导体板块受地缘因素压制，      │
│  建议关注下周三美联储议息决议对      │
│  科技股的估值影响..."               │
├─────────────────────────────────────┤
│ 📰 最新关联情报                      │
│ · 美联储暗示降息 → 科技股受益        │
│ · 中芯国际季报超预期                 │
├─────────────────────────────────────┤
│         [查看完整分析]               │
└─────────────────────────────────────┘
```

---

## 实施阶段

### Phase 1（后端与核心逻辑 - 已完成 ✅）
| 任务 | 文件 | 状态 |
|------|------|--------|
| 新增 `GET /market/pulse` | `routers/mobile.py` | ✅ 已上线 |
| 新增 `GET /watchlist/{code}/ai_analysis` | `routers/watchlist_v2.py` | ✅ 已上线 |
| SQL 性能优化 (Float 列) | `mobile.py` / `watchlist_v2.py` | ✅ 已完成 |
| 企业级缓存开发 | `infra/cache.py` | ✅ 已完成 |
| 财经日历显示修复 (7天) | `calendar.py` | ✅ 已完成 |

### Phase 2（iOS 接入与质量提升 - 已完成 ✅）
| 任务 | 说明 | 状态 |
|------|------|--------|
| iOS 悬浮胶囊接入 | MainTabView 全局悬浮组件 | ✅ 已上线 |
| iOS 长按手势面板 | FundCompactCard 触发 Bottom Sheet | ✅ 已上线 |
| 分析结果 Redis 缓存 | per-fund 分析缓存 | ✅ 已完成 |
| 基金实体标准化识别 | 补充 A股基金实体识别规则 | ✅ 已完成 |
| pgvector 语义检索 | 向量化语义匹配情报 | ✅ 已上线 |

---

## 风险与注意事项

> [!WARNING]
> `fund_name ILIKE` 匹配可能精度不高（如"华夏"会匹配所有华夏系基金），Phase 2 必须用向量搜索或精确 entity 匹配来提升准确率。

> [!NOTE]
> 当前 [Intelligence](file:///Users/caomeifengli/workspace/AlphaSignal/src/alphasignal/models/intelligence.py#36-40) 大多数情报为宏观/黄金方向，与 A 股 ETF 的关联情报可能较少。`has_data: false` 时 iOS 端需要有优雅降级展示（如"暂无关联情报，显示市场整体情绪"）。

> [!TIP]
> `market/pulse` 接口可以加 30s Redis 缓存（非用户级），避免多用户同时触发频繁查询。
