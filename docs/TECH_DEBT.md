# LucidPanda 技术债务追踪
> 优先级: P1=紧急（影响稳定性） | P2=重要（影响开发效率） | P3=优化
> 更新日期: 2026-03-19

---

## 🔴 P1 - 紧急（下个Sprint必须处理）

### DEBT-001: `web.py` 路由混入业务逻辑
- **文件**: `src/LucidPanda/api/v1/routers/web.py` (~40K)
- **问题**: 大量业务逻辑直接写在路由中，违反分层架构
- **影响**: AI修改路由时容易引发连锁破坏，新功能无法复用逻辑
- **解决方案**: 将业务逻辑迁移到 `services/` 层，Router 只保留参数验证和调用
- **估时**: 3-5天
- **代码标记**: `# DEBT[P1][DEBT-001]`

### DEBT-002: `watchlist_v2.py` 路由混入业务逻辑
- **文件**: `src/LucidPanda/api/v1/routers/watchlist_v2.py` (~40K)
- **问题**: 同 DEBT-001
- **影响**: 同 DEBT-001
- **解决方案**: 创建 `services/watchlist_service.py`
- **估时**: 2-3天
- **代码标记**: `# DEBT[P1][DEBT-002]`

---

## 🟠 P2 - 重要（本季度处理）

### DEBT-003: `fund_engine.py` 单文件过大
- **文件**: `src/LucidPanda/core/fund_engine.py` (~77K, ~2000行)
- **问题**: 基金评分、过滤、缓存、数据拉取逻辑全混在一个文件
- **影响**: AI修改一处容易破坏其他功能，难以测试
- **解决方案**: 拆分为:
  - `core/fund_scoring.py` (评分算法)
  - `core/fund_filter.py` (筛选逻辑)
  - `core/fund_data_fetcher.py` (数据拉取)
- **估时**: 3-4天
- **注意**: 拆分前必须有完整的集成测试覆盖

### DEBT-004: `db/intelligence.py` 单文件过大
- **文件**: `src/LucidPanda/db/intelligence.py` (~79K)
- **问题**: 资讯数据所有操作集中在一个文件
- **解决方案**: 按功能拆分子模块
- **估时**: 2天

### DEBT-005: `web/components/BacktestStats.tsx` 组件过大
- **文件**: `web/components/BacktestStats.tsx` (~53K)
- **问题**: 单组件超5000行，包含多个独立功能
- **解决方案**: 拆分为多个子组件
- **估时**: 1-2天

### DEBT-006: 前端直连 PostgreSQL
- **文件**: `web/` 中使用 `pg` 包直连 DB
- **问题**: 前端绕过后端直接查 DB，破坏安全边界
- **影响**: 数据库凭证暴露风险，无法统一权限控制
- **解决方案**: 迁移到后端 API 端点
- **优先级**: 安全问题，宜早处理

---

## 🟡 P3 - 优化（有空处理）

### DEBT-007: 缺少 API 类型同步机制
- **问题**: iOS 的 Codable struct 与后端 Pydantic 模型手动维护，容易不一致
- **解决方案**: 设置 `scripts/generate_openapi.py`，从 Pydantic 自动生成 OpenAPI 规范

### DEBT-008: 测试覆盖率不足
- **文件**: `tests/` 目录内容较少
- **目标**: 核心 Service 层覆盖率 > 70%
- **重点**: `fund_engine.py`、`intelligence.py` 的核心函数

### DEBT-009: `docs/` 目录文档过多且缺乏组织
- **问题**: 47个文档文件，无结构，AI难以定位相关文档
- **解决方案**: 建立 ADR 体系，归档历史文档到 `docs/archive/`

---

## 📊 债务统计

| 优先级 | 数量 | 估计总工时 |
|--------|------|-----------|
| P1 🔴 | 2 | 5-8天 |
| P2 🟠 | 4 | 8-12天 |
| P3 🟡 | 3 | 4-6天 |
| **合计** | **9** | **17-26天** |

---

## 更新规范

在代码中标记技术债务使用以下格式：
```python
# DEBT[P1][DEBT-001]: 描述，参考本文档
# DEBT[P2][DEBT-003]: 描述
```

每个Sprint开始时回顾此文档，将已解决项目标记删除线并注明解决日期。
