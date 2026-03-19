# ADR 索引
> 架构决策记录 (Architecture Decision Records)
> 每个重大技术决策必须有对应ADR，AI操作前必须查阅相关ADR

| ADR | 标题 | 状态 | 日期 |
|-----|------|------|------|
| [ADR-001](ADR-001-sqlmodel-choice.md) | 选择SQLModel作为ORM | 已接受 | 2025-Q4 |
| [ADR-002](ADR-002-monorepo-strategy.md) | Monorepo仓库策略 | 已接受 | 2026-03-19 |
| [ADR-003](ADR-003-ios-web-api-separation.md) | iOS与Web独立路由策略 | 已接受 | 2026-03-19 |

---

## 如何创建新ADR

1. 复制 `ADR-000-template.md`
2. 命名为 `ADR-{序号}-{简短描述}.md`
3. 更新本索引文件
4. 在 CLAUDE.md 的"关键技术决策"部分添加摘要
