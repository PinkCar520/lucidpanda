# LucidPanda — AI Assistant System Context
> **所有AI助手（Claude / Gemini / Codex）必须在开始任何任务前完整阅读本文件。**
> 最后更新: 2026-03-27

---

## 项目简介

**LucidPanda** 是一个面向中国用户的量化投资信号平台，提供基金研究、智能投研资讯、回测分析功能。

| 端 | 技术栈 | 目录 |
|----|--------|------|
| 后端 API | Python 3.11 + FastAPI + SQLModel + PostgreSQL + Redis | `apps/api/src/lucidpanda/` |
| Web 前端 | Next.js 16 + TypeScript + TailwindCSS + React Query | `apps/web/` |
| iOS 移动端 | SwiftUI + Swift 5.9 | `mobile/ios/LucidPanda/` |

**部署方式**：Docker Compose (`docker-compose.yml` + `docker-compose.override.yml`)
**包管理**：整个 monorepo 统一使用 **pnpm**。
**数据库初始化**：schema 随容器启动通过 `DBBase._init_db` 自动初始化（含 WebAuthn 和用户中心表）。**无需手动运行 `migrations/` 下的旧脚本**，除非是为了迁移存量数据。

---

## 🚀 快速启动与部署 (新服务器)

1. **基础启动**：
   ```bash
   pnpm install
   docker compose up -d
   ```
2. **初始化数据** (仅首次需手动执行一次)：
   ```bash
   # 进入 API 容器执行
   docker exec -it lucid_panda_api /bin/bash
   
   # 同步基金/股票基础信息
   python apps/api/scripts/backfills/sync_fund_metadata.py
   python apps/api/scripts/backfills/sync_stock_metadata.py
   # 补全拼音搜索字段
   python apps/api/scripts/backfills/backfill_all_pinyin.py
   ```

**TypeScript 类型规范（Web）**
官方推荐做法（核心）
1. 对象结构优先用 `interface`
   接口用来“命名对象的形状/契约”，适合 API 返回结构、组件 props 等。(https://www.typescriptlang.org/docs/handbook/interfaces.html)
2. 联合/元组/基础类型组合用 `type`
   类型别名更适合联合类型、元组、原始类型组合等场景。(https://www.typescriptlang.org/docs/handbook/advanced-types.html)
3. 需要可扩展/合并的类型，用 `interface`
   `interface` 支持声明合并（declaration merging），而 `type` 不能“重新打开”扩展。(https://www.typescriptlang.org/docs/handbook/declaration-merging.html)
4. 声明文件用 `.d.ts`
   `.d.ts` 是纯类型声明文件，不会生成 JS，适合给无类型库补类型或做全局/模块增强。(https://www.typescriptlang.org/docs/handbook/2/type-declarations)
5. 扩展第三方模块或全局类型，用模块增强/全局增强
   需要给已有模块或全局对象补类型时，使用 module augmentation / global augmentation。(https://www.typescriptlang.org/docs/handbook/declaration-merging.html)
6. 避免 `any`，优先 `unknown` + 类型收窄
   `any` 会关闭类型检查，应尽量避免；`unknown` 更安全。(https://www.typescriptlang.org/docs/handbook/basic-types.html)
7. 开启严格模式 / `noImplicitAny`
   官方建议开启 `strict`，尤其是 `noImplicitAny`，避免隐式 `any`。(https://www.typescriptlang.org/docs/handbook/2/basic-types.html)

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
6. **禁止新增路径冲突端点**：同一前缀下若存在历史端点和新端点，必须先检查 FastAPI router 注册顺序，避免旧路由抢占新路由
7. **兼容接口不得静默删除**：已被 Web / iOS / 测试使用的旧路径，若要替换，必须提供兼容层或同步更新所有调用方

### 前端分层规则
```
Pages (app/) → Components → Hooks (hooks/api/) → API calls (lib/)
```
1. **Pages 只做组合**：不写业务逻辑，只组合 Components
2. **数据获取统一用 React Query**：禁止在组件内直接 fetch，必须通过 `hooks/api/` 中的自定义 hook
3. **组件文件 < 300行**：超过则必须拆分子组件
4. **接口类型必须先于页面实现**：新增或变更接口时，先更新 `lib/` 请求层和类型定义，再改页面或组件
5. **禁止页面兜底猜接口**：不得用“404 后再试另一个路径”的方式长期兼容接口漂移，临时兜底必须注明迁移计划

### 跨端规则
1. **API 变更必须先更新 Pydantic 模型**，再改路由，再改前端/iOS
2. **禁止前端直接查数据库**（`apps/web/` 中出现 `pg` 直连是临时方案，后续需迁移）
3. **返回结构必须稳定**：`data` / `groups` / `sync_time` / `success` 这类跨端依赖字段不得随意改名
4. **兼容变更必须列出影响面**：至少明确 Web、iOS、测试、历史接口四类调用方是否受影响

---

## 🔒 补全规则（高质量代码 / 可维护性 / 接口演进）

### 后端补全规则
1. **先补模型，再补实现**：请求体、响应体、数据库字段、测试夹具四者必须同步补齐，禁止只改其中一层
2. **禁止在 Router 中堆叠临时补丁**：如果一个端点已经出现“兼容旧参数 + 兼容旧路径 + SQL 直写 + 业务判断”四种以上职责，必须停止继续叠加并先拆分
3. **新增字段必须检查测试 SQLite schema**：若 `tests/conftest.py` 手工建表，新增列后必须同步补齐测试表结构
4. **依赖覆盖必须稳定**：测试里的 `get_session`、`get_current_user` override 不得使用随机用户或随机上下文，除非测试目标就是随机性
5. **时间统一使用 timezone-aware UTC**：禁止新写 `datetime.utcnow()`，统一用 `datetime.now(UTC)`
6. **优先 `select()` / `session.get()`**：新增或修改 SQLModel / SQLAlchemy 查询时，禁止继续扩散 `query(...).get(...)` 旧写法
7. **兼容接口必须显式命名**：例如 `*_legacy`、`*_compat`，并写清兼容原因，避免后续看不出为什么保留旧路径

### 前端补全规则
1. **页面只能消费稳定接口**：页面和组件不得直接拼 URL 或猜测返回结构，统一通过 `lib/` 和 `hooks/api/`
2. **接口字段名由后端定义，前端适配层转换**：若展示层命名不同，转换放在 hook / mapper，不要散落到组件里
3. **禁止“边修边猜”接口**：如果接口不确定，先读取后端响应模型或现有 hook，再写组件
4. **接口变更必须补类型和空态**：新增字段时，同时补 loading / empty / error 状态，不允许只补 happy path

### 提交与变更边界规则
1. **禁止生成物入库**：`coverage.xml`、临时快照、运行产物、调试输出不得提交
2. **禁止无关文档删除**：修 API / 前端 / 测试时，不得顺带删除 `docs/`、图片或历史设计文档，除非任务明确要求
3. **禁止超范围提交**：一次任务只允许修改和目标直接相关的代码、测试、类型、文档；大批量 unrelated 改动必须拆分
4. **禁止使用无信息量提交名**：`fix`、`update`、`tmp` 这类提交名不可接受，提交信息必须体现作用域和意图

---

## 🧨 最近真实踩坑（必须规避）

以下问题都已经在最近提交中真实出现，后续 AI 不得重复：

1. **路由遮蔽**
   `watchlist_v2` 已注册，但 `/api/v1/web/watchlist` 被旧版 `web.py` 同路径端点先匹配，导致写入走新逻辑、读取走旧逻辑，行为分裂。
   规避：
   修改或新增路由前，必须检查 `api/v1/main.py` 的 include 顺序与路径冲突。

2. **测试夹具与真实用户不一致**
   测试向固定用户插入数据，但 `override_api_auth` 返回随机用户，导致“写入成功、读取为空”的伪故障。
   规避：
   测试认证 override 默认使用稳定测试用户 ID；只有在测试权限隔离时才允许自定义。

3. **测试表结构漂移**
   `watchlist_v2` 使用了 `id/group_id/updated_at`，但 SQLite 测试表缺列，导致接口行为和测试环境不一致。
   规避：
   每次改数据库读写逻辑时，同时检查 `tests/conftest.py` 手工建表定义。

4. **兼容路径被遗漏**
   新逻辑只保留 `POST /batch-remove`，但历史调用方仍在用 `DELETE /batch`。
   规避：
   改 API 前先搜索所有调用点、测试和移动端约定，确认是否需要兼容层。

5. **生成物和无关删除被带入主分支**
   最近提交里出现了 `apps/api/coverage.xml` 入库，以及大量 `docs/` 删除混入功能提交。
   规避：
   合并前必须检查 `git show --stat`；若出现生成物或无关删除，必须先拆分提交再合并。

---

## ✅ 强制约定

### Python 后端
- 所有公共函数必须有类型注解（`def foo(x: int) -> str:`）
- 错误处理：在 Router 边界用 `try/except`，Service 层可以抛出自定义异常
- 日志：使用 `src/lucidpanda/core/logger.py` 中的 logger，**禁止裸 `print()`**
- 异步：`async def` 路由处理器中的阻塞操作必须用 `asyncio.run_in_executor`

### TypeScript 前端
- 禁止 `any` 类型（有临时理由须加 `// TODO: fix type`）
- API 响应类型定义在 `apps/web/types.d.ts` 或对应 feature 目录内
- 组件 props 必须有显式类型定义

### Swift iOS
- 遵循 MVVM 模式：`Features/{Name}/Views/` + `Features/{Name}/ViewModels/`
- API 层统一在 `Core/` 或 `Data/` 中，Views 不直接调用 URLSession
- 字段命名与后端 JSON key 保持一致（用 `CodingKeys` 映射）

---

## ⚠️ 已知技术债务（操作这些区域请格外谨慎）

### 后端

| 文件 | 行数 | 问题 | 风险 |
|------|------|------|------|
| `api/v1/routers/web.py` | ~1065行 / 28端点 | Router 混入大量业务逻辑和 SQL | 🔴 修改易引发连锁反应 |
| `api/v1/routers/watchlist_v2.py` | ~1028行 | 同上 | 🔴 |
| `core/fund_engine.py` | ~1772行 | 单文件过大（已开始拆分至 `core/fund/`，进行中） | 🔴 |
| `db/intelligence.py` | ~1745行 | 单文件过大 | 🟠 |
| `db/base.py` | ~559行 | 通用查询混入了过多特定业务逻辑 | 🟡 |

### 前端

| 文件 | 行数 | 问题 | 风险 |
|------|------|------|------|
| `components/BacktestStats.tsx` | ~727行 | 超300行限制2.4x，含内嵌业务逻辑 | 🔴 |
| `app/[locale]/page.tsx` | ~401行 | 页面含业务逻辑，超出限制 | 🟠 |
| `components/Shell.tsx` | ~18KB | 布局组件较大，含状态管理 | 🟡 |
| `components/FundSearch.tsx` | ~19KB | 搜索功能逻辑复杂 | 🟡 |
| `apps/web/` 中的 `pg` 直连 | 多处 | 前端直查DB，绕过后端 | 🟠 |

### 类型安全
- `apps/web/app/` 下约 **36处 `: any`** 未附 `// TODO: fix type` 注释，不符合规范

> **AI操作指引**：修改上述文件前，必须先理解完整上下文，仅做最小改动。不要趁机重构无关逻辑。不得私自变更包管理器或大幅改动 Dockerfile。

---

## 📁 目录速查

```
apps/api/src/lucidpanda/
├── api/v1/routers/     # ⚠️ 路由（web.py / mobile.py / watchlist_v2.py / calendar.py）
├── services/           # 业务逻辑（agent_tools / market_service / embedding_service 等）
├── db/                 # 数据访问（base / fund / intelligence / market）
├── models/             # SQLModel ORM 模型
├── core/               # 核心引擎
│   ├── fund/           # 🆕 fund_engine.py 的拆分目标（进行中）
│   ├── fund_engine.py  # ⚠️ 待拆分
│   ├── di_container.py # 依赖注入容器
│   ├── engine.py       # 主引擎（654行）
│   └── taskiq_broker.py
├── infra/              # 基础设施（Redis / 外部API客户端）
├── auth/               # JWT 认证
└── config/             # 全局配置

apps/web/
├── app/[locale]/       # Next.js 页面路由（App Router）
│   ├── page.tsx        # ⚠️ 主页（401行，含业务逻辑）
│   ├── funds/monitor/  # 基金监控
│   ├── backtest/       # 回测
│   ├── intelligence/   # 投研资讯
│   └── settings/       # 用户设置
├── components/         # 共享UI组件
│   ├── BacktestStats.tsx    # ⚠️ 过大（727行）
│   └── IntelligenceCard.tsx # ✅ 参考模板（清晰，有测试）
├── hooks/api/          # React Query hooks（数据获取）
├── lib/                # API client / 工具函数
├── auth.ts             # NextAuth.js 配置（依赖环境变量 AUTH_SECRET，不可硬编码）
├── middleware.ts        # 认证/国际化路由守卫
└── types.d.ts          # 全局类型定义

mobile/ios/LucidPanda/LucidPanda/
├── Features/           # 按功能模块（Auth/Funds/Market/Dashboard...）
├── Core/               # 核心服务（网络/认证）
├── Data/               # 数据层
└── UIComponents/       # 可复用UI组件
```

---

## 🔑 关键技术决策（ADR摘要）

- **为什么用 SQLModel**：同时作为 ORM 和 Pydantic 模型，减少重复定义（见 docs/adr/ADR-001）
- **为什么 iOS 和 Web 共用同一后端**：移动端路由在 `mobile.py`，Web 路由在 `web.py`（接口已隔离）
- **为什么用 Redis**：缓存金融数据（yfinance/akshare 限速），缓存 embedding 向量
- **为什么用 pgvector + embedding**：AI 语义去重新闻资讯（见 `embedding_service.py`）
- **为什么用 TaskIQ**：替代 Celery，实现异步任务调度
- **API 代理**：`apps/web/next.config.ts` 中的 `rewrites` 将 `/api/v1/*` 转发至后端容器 `http://api:8001`

---

## 🤖 AI 操作规范

### 开始任务前必须做
1. 阅读本文件
2. 用 `rg` / `git grep` 查找相关现有实现，避免重复造轮子
3. 对于涉及 `web.py`/`watchlist_v2.py`/`fund_engine.py`/`BacktestStats.tsx` 的任务，先完整读取目标函数上下文
4. **确认改动范围，不得扩大边界**
5. 若涉及接口变更，先检查：
   - 路由是否与历史路径冲突
   - Web / iOS / tests 是否已有调用
   - `tests/conftest.py` 是否需要同步

### 代码生成规范
- 新的 API 端点：先在对应的 Pydantic 模型定义请求/响应体，再写路由
- 新的 iOS 功能：参考 `Features/Funds/` 的结构
- 新的 React 组件：参考 `components/IntelligenceCard.tsx`
- 新的 React Query hook：参考 `hooks/api/use-fund-query.ts`

### ❌ 严禁行为（历史教训）
- **禁止在修复 Bug 期间顺带重构架构**（例如修复认证问题时擅自更换包管理器）
- **禁止试错式（Trial & Error）修改**：每次改动前必须先推演完整因果链
- **禁止在没有用户明确授权的情况下修改 Dockerfile 构建架构**
- **禁止将未注释的 `any` 类型直接提交**
- **禁止提交生成文件**：尤其是 `coverage.xml`、日志、缓存文件、运行时快照
- **禁止一次提交混入无关文件删除**：尤其是 `docs/`、图片、历史设计文档
- **禁止为了“让测试过”修改测试语义**：测试夹具可以修，但不能通过降低断言强度掩盖真实问题

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
4. **SSE 连接**：前端 SSE 客户端断线重连逻辑在 `apps/web/hooks/useSSE.ts` 中，修改时注意
5. **iOS 中文本地化**：所有用户可见字符串必须在 `Localizable.xcstrings` 中注册
6. **AUTH_SECRET**：NextAuth 依赖系统环境变量，不应在代码中硬编码。生产环境通过 `docker-compose.yml` 的 `env_file: .env` 注入
7. **Docker 构建上下文**：`apps/web` 的 Dockerfile 构建上下文为 `./apps/web`，不是根目录

---

## 📊 代码质量现状（2026-03-27）

| 维度 | 当前状态 | 目标 |
|------|---------|------|
| 后端 Router 单文件大小 | `web.py` 1065行，28个端点 | < 300行/文件 |
| 后端 DB 单文件大小 | `intelligence.py` 1745行 | < 500行/文件 |
| 前端组件大小 | `BacktestStats.tsx` 727行 | < 300行/文件 |
| TypeScript `any` 未注释 | ~36处（仅 app/ 目录） | 0处，或全部加 TODO |
| 测试覆盖 | 仅 `IntelligenceCard.test.tsx` 1个前端测试 | 关键组件均有测试 |
| 架构分层遵从度 | Router 混入业务逻辑（🔴 违规） | 严格分层 |

---

## ✅ 合并前自检清单（AI必须执行）

- [ ] `git diff --stat` 中没有生成物、缓存文件、coverage 文件
- [ ] `git diff --stat` 中没有无关 `docs/` 删除
- [ ] 若改了 API：已检查路由冲突、调用方兼容、测试夹具同步
- [ ] 若改了数据库访问：已检查测试 SQLite schema 是否同步
- [ ] 若改了前端接口：类型、hook、页面状态三层都已更新
- [ ] 提交说明不是 `fix` / `update` / `tmp`
