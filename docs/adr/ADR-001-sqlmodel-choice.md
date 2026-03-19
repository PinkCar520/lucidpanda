# ADR-001: 选择 SQLModel 作为 ORM

**日期**: 2025-Q4（推算）
**状态**: 已接受  
**决策者**: 项目团队

---

## 背景

需要一个 ORM 框架来管理 PostgreSQL 数据库操作，同时需要 Pydantic 来做 FastAPI 的请求/响应验证。

## 决策

使用 **SQLModel**（由 SQLAlchemy + Pydantic 融合的库），让数据库模型同时承担 ORM 实体和 Pydantic 模型的角色。

## 详细说明

- 数据库模型定义在 `src/lucidpanda/models/`（`table=True` 的 SQLModel 类）
- 这些模型既可以用于数据库操作，也可以直接作为 FastAPI 的响应模型
- API 专属的请求/响应体（不对应数据库表的）用普通 `BaseModel`

## 被拒绝的方案

| 方案 | 被拒原因 |
|------|---------|
| SQLAlchemy + 独立Pydantic | 需维护两套模型，代码重复 |
| Django ORM | 与 FastAPI 集成复杂，过重 |
| Tortoise ORM | 生态较小，团队经验不足 |

## 后果

**正面影响**:
- 减少 ORM 模型和 API 模型的重复定义
- FastAPI 自动文档更准确

**负面影响/需要接受的妥协**:
- SQLModel 版本更新有时破坏性强，需谨慎升级
- 复杂查询仍需回退到 SQLAlchemy Core

## AI操作指引

- 新增数据库实体：在 `src/lucidpanda/models/` 创建 SQLModel 类（`table=True`）
- 新增纯API模型（无DB）：在对应 router 文件顶部用 `BaseModel`，或放在 `models/` 中标注
- **禁止**：在 router 或 service 中定义 `table=True` 的 SQLModel
- 相关文件: `src/lucidpanda/models/fund.py`, `models/intelligence.py`
