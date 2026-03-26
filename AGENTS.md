# LucidPanda — AI Assistant System Context
> **所有AI助手（Codex / Gemini / Codex）必须在开始任何任务前完整阅读本文件。**
> 最后更新: 2026-03-19

---

## 项目简介

**LucidPanda** 是一个面向中国用户的量化投资信号平台，提供基金研究、智能投研资讯、回测分析功能。

| 端 | 技术栈 | 目录 |
|----|--------|------|
| 后端 API | Python 3.11 + FastAPI + SQLModel + PostgreSQL | `src/lucidpanda/` |
| Web 前端 | Next.js 16 + TypeScript + TailwindCSS + React Query | `web/` |
| iOS 移动端 | SwiftUI + Swift 5.9 | `mobile/ios/LucidPanda/` |

---

## 🚫 架构红线（不可违反，违反则CI拦截）

### 后端分层规则（严格单向依赖）
```
API Routers → Services → DB Repositories → SQLModel Models
```
1. **Router 只做路由**：参数验证（Pydantic）+ 调用 Service + 返回响应。**禁止在 router 中写业务逻辑或 SQL**
2. **Service 只做业务逻辑**：调用 Repository，不直接导入 `db/` 以外的数据库对象
3. **DB 层只做数据读写**：`src/lucidpanda/db/` 是唯一允许写 SQL/ORM 查询的地方
4. **禁止 SQL 字符串拼接**：所有 SQL 必须用参数化查询或 SQLModel ORM
5. **禁止在 async 函数中直接调用同步 I/O**：yfinance / akshare 必须用 `run_in_executor`

### 前端分层规则
```
Pages (app/) → Components → Hooks (hooks/) → API calls (lib/)
```
1. **Pages 只做组合**：不写业务逻辑，只组合 Components
2. **数据获取统一用 React Query**：禁止在组件内直接 fetch，必须通过 `hooks/` 中的自定义 hook
3. **组件文件 < 300行**：超过则必须拆分子组件

### 跨端规则
1. **API 变更必须先更新 Pydantic 模型**，再改路由，再改前端/iOS
2. **禁止前端直接查数据库**（`web/` 中出现 `pg` 直连是临时方案，后续需迁移）

---

## ✅ 强制约定

### Python 后端
- 所有公共函数必须有类型注解（`def foo(x: int) -> str:`）
- 错误处理：在 Router 边界用 `try/except`，Service 层可以抛出自定义异常
- 日志：使用 `src/lucidpanda/core/logger.py` 中的 logger，**禁止裸 `print()`**
- 异步：`async def` 路由处理器中的阻塞操作必须用 `asyncio.run_in_executor`

### TypeScript 前端
- 禁止 `any` 类型（有临时理由须加 `// TODO: fix type`)
- API 响应类型定义在 `web/types.d.ts` 或对应 feature 目录内
- 组件 props 必须有显式类型定义

### Swift iOS
- 遵循 MVVM 模式：`Features/{Name}/Views/` + `Features/{Name}/ViewModels/`
- API 层统一在 `Core/` 或 `Data/` 中，Views 不直接调用 URLSession
- 字段命名与后端 JSON key 保持一致（用 `CodingKeys` 映射）

---

## ⚠️ 已知技术债务（操作这些区域请格外谨慎）

| 文件 | 问题 | 风险 |
|------|------|------|
| `src/lucidpanda/api/v1/routers/web.py` (~40K) | 路由文件混入了大量业务逻辑 | 🔴 修改易引发连锁反应 |
| `src/lucidpanda/api/v1/routers/watchlist_v2.py` (~40K) | 同上 | 🔴 |
| `src/lucidpanda/core/fund_engine.py` (~77K) | 单文件过大，职责混乱 | 🔴 |
| `src/lucidpanda/db/intelligence.py` (~79K) | 单文件过大 | 🟠 |
| `web/components/BacktestStats.tsx` (~53K) | 组件过大 | 🟠 |
| `web/app/[locale]/page.tsx` (~18K) | 页面组件含业务逻辑 | 🟡 |
| `web/` 中的 `pg` 直连 | 前端直查DB，绕过后端 | 🟠 |

> **AI操作指引**：修改上述文件前，必须先理解完整上下文，仅做最小改动。不要趁机重构无关逻辑。

---

## 📁 目录速查

```
src/lucidpanda/
├── api/v1/routers/     # ⚠️ 路由（web.py/mobile.py/watchlist_v2.py）
├── services/           # 业务逻辑（agent_tools/market_service等）
├── db/                 # 数据访问（base/fund/intelligence/market）
├── models/             # SQLModel ORM模型（fund/intelligence/macro_event）
├── core/               # 核心引擎（engine/fund_engine/deduplication）
├── infra/              # 基础设施（Redis/外部API客户端）
├── auth/               # JWT认证
└── config.py           # 全局配置（用 os.getenv，勿硬编码）

web/
├── app/[locale]/       # Next.js 页面路由
├── components/         # 共享UI组件
├── hooks/              # React Query hooks（数据获取）
├── lib/                # API client / 工具函数
└── types.d.ts          # 全局类型定义

mobile/ios/LucidPanda/LucidPanda/
├── Features/           # 按功能分模块（Auth/Funds/Market/Dashboard...）
├── Core/               # 核心服务（网络/认证）
├── Data/               # 数据层（API响应模型）
└── UIComponents/       # 可复用UI组件
```

---

## 🔑 关键技术决策（ADR摘要）

- **为什么用 SQLModel**：同时作为 ORM 和 Pydantic 模型，减少重复定义（见 docs/adr/ADR-001）
- **为什么 iOS 和 Web 共用同一后端**：移动端路由在 `mobile.py`，Web 路由在 `web.py`（接口已隔离）
- **为什么用 Redis**：缓存金融数据（yfinance/akshare 限速），缓存 embedding 向量
- **为什么用 pgvector + embedding**：AI 语义去重新闻资讯（见 `embedding_service.py`）

---

## 🤖 AI 操作规范

### 开始任务前必须做
1. 阅读本文件
2. `grep_search` 查找相关现有实现，避免重复造轮子
3. 对于涉及 `web.py`/`watchlist_v2.py`/`fund_engine.py` 的任务，先完整读取目标函数上下文

### 代码生成规范
- 新的 API 端点：先在对应的 Pydantic 模型定义请求/响应体，再写路由
- 新的 iOS 功能：参考 `Features/Funds/` 的结构作为模板
- 新的 React 组件：参考 `components/IntelligenceCard.tsx`（结构清晰，有测试）

### 完成任务后必须确认
- [ ] Python: `mypy` 或 IDE 类型检查无错误
- [ ] Python: 新函数有类型注解
- [ ] TypeScript: `tsc --noEmit` 无错误
- [ ] 未引入不必要的新依赖

---

## 📞 常见陷阱（历史经验总结）

1. **日期范围差一天**：`today + timedelta(days=N)` 产生 N+1 天。用 `timedelta(days=N-1)` 得到 N 天
2. **事件循环阻塞**：`yfinance.download()` 是同步的，必须 `await loop.run_in_executor(None, ...)`
3. **去重 Bug**：用 `set` 去重时，确保 key 包含所有有意义字段
4. **SSE 连接**：前端 SSE 客户端断线重连逻辑在 `web/hooks/` 中，修改时注意
5. **iOS 中文本地化**：所有用户可见字符串必须在 `Localizable.xcstrings` 中注册
