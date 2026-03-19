# LucidPanda 智能 Agent 架构改造计划 (Phase 3)

## 0. 实施进度（更新于 2026-03-16）

**✅ 已完成**
- **Phase A 基础设施升级**：实现 `mcp_server.py` 与 `agent_tools.py` 基础框架。
- **Phase B 推理引擎改造**：`AlphaEngine` 成功集成 ReAct 推理循环，支持 `agent_trace` 记录。
- **Phase C 量化技能深度化**：
    - 完成 `alpha_return` 与 `expectation_gap` 数据库闭环。
    - 修复了 `alpha_return` 在回填脚本中的回归逻辑 bug。
    - 升级 Web 端 `/stats` 接口，支持超额收益统计与分布分析。
- **Phase E 稳定性与工具链补全**：
    - 解决 Gemini Embedding SSL/EOF 错误，实现本地模型自动降级 (Local Fallback)。
    - 补全 `get_historical_perf` (历史胜率)、`get_entity_influence` (图谱权重)、`get_market_positioning` (持仓分位) 核心工具。

**持续进行中**
- **语料积累**：持续收集 `agent_trace` 语料，为 Phase D 微调做准备。

**待开始**
- **Phase D 专有模型微调**：训练语料清洗并进行 LoRA 微调。

---

## 1. 背景与愿景 (保持不变)
...

## 2. 架构转型 (保持不变)
...

---

## 3. 核心组件补全计划

目前 `agent_tools.py` 的核心武器库已补全上线：

| 工具名称 | 状态 | 功能描述 | 依赖组件 |
| :--- | :--- | :--- | :--- |
| `query_macro_expectation` | ✅ 已上线 | 获取宏观指标预期差 | `MacroEvent` |
| `calculate_alpha_return` | ✅ 已上线 | 剥离因子计算超额收益 | `quant_skills.py` |
| `get_historical_perf` | ✅ 已上线 | 查询特定关键词新闻的历史胜率 | `BacktestEngine.get_confidence_stats` |
| `get_entity_influence` | ✅ 已上线 | 查询实体在知识图谱中的中心度与权重 | `IntelligenceRepo.get_entity_graph` |
| `get_market_positioning` | ✅ 已上线 | 获取 COT 黄金净持仓分位数及情绪挤压度 | `market_indicators` |


---

## 4. 详细需求计划 (Phase D & E)

### Phase E：稳定性修复与工具链补全 (Weeks 1-2)
**目标**：消除生产环境报错，使 Agent 具备完整的查证能力。
1.  **修复 Embedding 连接**：
    - 排查 `singbox` 代理容器对 Google Gemini Embedding API 的 SSL 握手异常。
    - 增加 API 重试机制与 Local Embedding 自动降级逻辑。
2.  **实现 `get_historical_perf` 工具**：
    - 允许 Agent 针对当前新闻关键词（如 "Hormuz Strait"）反查历史 1h 胜率。
3.  **实现 `get_market_positioning` 工具**：
    - 对接 `market_indicators` 表，计算最近一次 `COT_GOLD_NET` 的百分位。

### Phase D：专有模型微调与评估 (Weeks 3-6)
**目标**：将 LucidPanda 的研究逻辑内化到模型中。
1.  **语料构建 (Data Distillation)**：
    - 筛选 `agent_trace` 中工具调用逻辑正确、且最终预测与 1h 价格走势方向一致的“黄金样本”。
    - 格式化为 `Prompt -> Thought -> Tool Calls -> Response` 结构。
2.  **微调实施 (LoRA Fine-tuning)**：
    - 基于 DeepSeek-7B 或 Llama-3-8B 进行微调。
    - 重点强化对 `expectation_gap` 结果的解读能力（例如：Z-Score > 2 时的极端反应）。
3.  **闭环评估**：
    - 使用回测系统对微调前后的 Agent 信号进行胜率对比。

---

## 5. 风险评估与应对 (更新)
*   **SSL 协议中断**：当前 `worker` 频繁报告 SSL EOF。*应对：升级 `google-genai` SDK，或将 Embedding 服务独立部署为外部微服务。*
*   **工具过度调用**：多轮工具查询导致响应延迟。*应对：强制执行 `AGENT_TOOL_MAX_CALLS=3`，并引入工具结果的 Redis 缓存。*

---

## 6. 生产环境执行参考

### 数据库现状 (已执行)
```sql
-- 已确认列存在，无需重复执行
-- agent_trace, alpha_return, expectation_gap, category 已添加
```

### 回填指令 (维护用)
```bash
# 若发现 alpha_return 缺失，执行此脚本
docker exec -it LucidPanda_worker python -m src.LucidPanda.scripts.backfill_intelligence_metrics --limit 500 --window 200
```

---
**核准人**：LucidPanda 架构委员会
**最后更新**：2026-03-16
