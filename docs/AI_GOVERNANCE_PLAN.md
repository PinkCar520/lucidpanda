# LucidPanda AI代码治理落地方案 (V2.0)
> 基于实际项目结构定制 | 技术栈: Python/FastAPI + Next.js + SwiftUI
> 更新日期: 2026-03-19

---

## 一、仓库策略

### 当前状态：已是 Monorepo ✅（无需迁移）
```
LucidPanda/  ← 单一Git仓库
├── src/LucidPanda/   # Python 后端
├── web/               # Next.js 前端
└── mobile/ios/        # SwiftUI iOS
```

### 为何不需要 Turborepo/Nx？
我们是 **Python+JS+Swift 混合栈**，Turborepo/Nx 主要针对纯 JS Monorepo。  
对 LucidPanda 更实用的是：**轻量脚本 + GitHub Actions** 替代重量级 Monorepo 工具。

### 依赖边界规则

| 方向 | 允许 | 禁止 |
|------|------|------|
| Web → 后端 | 通过 HTTP API | 直接 import Python 模块 |
| iOS → 后端 | 通过 HTTP API | 直接 import Python 模块 |
| Web ↔ iOS | 无直接依赖 | 任何直接引用 |
| 后端内部 | Router→Service→DB→Model | 逆向依赖 |

---

## 二、架构治理（防止AI胡来）

### 2.1 后端分层（强制执行）

```
HTTP Request
    ↓
[api/v1/routers/]   ← 只做：参数验证、Auth检查、调用Service
    ↓
[services/]          ← 只做：业务逻辑、编排多个Repository
    ↓
[db/]               ← 只做：SQL/ORM、数据读写
    ↓
[models/]           ← SQLModel 实体定义
```

**强制规则（CI检查）**：
```python
# ✅ 正确：router 调用 service
@router.get("/funds/{fund_id}")
async def get_fund(fund_id: str, svc: FundService = Depends()):
    return await svc.get_by_id(fund_id)

# ❌ 错误：router 直接查数据库（AI最爱干的事！）
@router.get("/funds/{fund_id}")
async def get_fund(fund_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fund).where(Fund.id == fund_id))
    return result.first()
```

### 2.2 前端分层（强制执行）

```
app/[locale]/页面   ← 只做：布局、组合组件
    ↓
components/         ← UI展示，通过props接收数据
    ↓
hooks/              ← React Query hooks，封装所有数据获取
    ↓  
lib/                ← API client，axios/fetch封装
```

### 2.3 iOS分层（强制执行）

```
Features/{Name}/Views/         ← SwiftUI View（只做UI）
Features/{Name}/ViewModels/    ← @Observable ViewModel（业务逻辑）
Data/                          ← API响应 Codable 模型
Core/NetworkClient.swift       ← 统一网络层
```

### 2.4 接口契约（OpenAPI优先）

```bash
# 每次修改API后执行（强制）
cd /workspace/LucidPanda
python -m scripts.generate_openapi
# 生成: docs/api/openapi.json
# iOS和Web前端以此为唯一真理
```

---

## 三、代码质量门禁

### 3.1 Python 质量检查

```toml
# pyproject.toml（新增）
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "UP", "B", "C90"]
ignore = ["E501"]

[tool.ruff.mccabe]
max-complexity = 10   # 圈复杂度超10则报错（AI爱写嵌套地狱）

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

```bash
# 安装质量工具
pip install ruff mypy pytest-cov

# pre-commit hook（.pre-commit-config.yaml）
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### 3.2 TypeScript 质量检查

```json
// web/tsconfig.json 强化（添加 strict 规则）
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

```javascript
// web/eslint.config.mjs 强化
export default [
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-floating-promises": "error",
      "max-lines": ["warn", { max: 300 }],  // 组件超300行警告
      "complexity": ["error", 10],
    }
  }
]
```

### 3.3 测试策略

**后端（pytest）**：
```python
# tests/ 目录结构
tests/
├── unit/
│   ├── test_fund_service.py
│   └── test_intelligence_service.py
├── integration/
│   └── test_fund_api.py    # 真实DB测试
└── conftest.py              # fixtures

# AI 生成代码的核心测试：边界值 + 异常路径
def test_get_fund_not_found():
    """AI常忘记测试404场景"""
    result = fund_service.get_by_id("nonexistent")
    assert result is None  # 或 raise HTTPException(404)

def test_async_io_not_blocking():
    """测试 yfinance 调用是否走了 executor"""
    # 确保没有直接 await yfinance（同步库）
```

**前端（Jest + Testing Library）**：
```typescript
// web/__tests__/  已存在，继续在此添加
// 重点测试：hooks 中的 API 调用逻辑（mock fetch）
```

---

## 四、上下文管理

### 4.1 AI上下文文件体系

```
LucidPanda/
├── CLAUDE.md          # ← 已创建！Claude/Gemini自动读取
├── .cursorrules       # ← Cursor IDE 自动读取（内容同CLAUDE.md）
└── docs/
    ├── GEMINI.md      # ← 已存在，需整合到CLAUDE.md
    ├── adr/           # ← 架构决策记录（新建）
    │   ├── ADR-001-sqlmodel-choice.md
    │   ├── ADR-002-monorepo-strategy.md
    │   └── ADR-003-ios-web-api-separation.md
    └── AI_GOVERNANCE_PLAN.md  # ← 本文件
```

### 4.2 模块级上下文注释（规范）

```python
"""
Module: fund_engine.py
Responsibility: 基金评分与排名计算引擎

⚠️  AI操作警告:
- calculate_alpha_score() 算法经过专项优化，不要重写
- 此文件依赖 Redis 缓存，修改查询逻辑需同步更新缓存键
- 相关ADR: docs/adr/ADR-004-fund-scoring-algorithm.md

Architecture:
- 上游调用者: api/v1/routers/web.py → services/ → 本模块
- 下游依赖: db/fund.py (数据读取), infra/redis_client.py (缓存)
"""
```

```typescript
/**
 * @module FundSearch
 * @description 基金搜索与筛选组件
 * 
 * @ai-context
 * - 数据通过 useFundSearch() hook 获取，不要改成直接 fetch
 * - 筛选条件通过 URL params 持久化（useSearchParams）
 * - 虚拟滚动由 @tanstack/react-virtual 处理，不要替换实现
 */
```

---

## 五、迭代与维护

### 5.1 技术债务追踪（见 docs/TECH_DEBT.md）

代码内标记规范：
```python
# DEBT[P1][#issue-123]: web.py 中的业务逻辑需迁移到 services/
# DEBT[P2][#issue-456]: fund_engine.py 超过 2000 行，需拆分
# DEBT[P3]: 前端直连 PostgreSQL，需改走后端 API
```

### 5.2 向后兼容策略

```python
# API 版本化
# 新增字段：可选字段，有默认值
class FundResponse(BaseModel):
    id: str
    name: str
    annual_return: float
    risk_level: int
    # v2 新增字段，iOS老版本不会报错
    ai_score: Optional[float] = None  

# 字段废弃流程：先标记，下个版本移除
    year_return: Optional[float] = None  # @deprecated: 使用 annual_return，v3移除
```

### 5.3 功能开关

```python
# src/LucidPanda/config.py 中管理
FEATURE_FLAGS = {
    "AI_FUND_RECOMMENDATION": os.getenv("FF_AI_FUND", "false") == "true",
    "NEW_INTELLIGENCE_DEDUP": os.getenv("FF_NEW_DEDUP", "false") == "true",
}

# 使用
if settings.FEATURE_FLAGS["AI_FUND_RECOMMENDATION"]:
    score = await ai_scoring_service.score(fund)
else:
    score = legacy_score(fund)
```

---

## 六、多端协同

### 6.1 类型同步流程（最重要！）

```
Pydantic Models (Python)
    ↓ python -m scripts.generate_openapi
docs/api/openapi.json
    ↓ Web: openapi-typescript
web/lib/api-types.ts (自动生成，勿手改)
    ↓ iOS: 手动对照实现 Codable struct
mobile/ios/.../Data/APIModels.swift
```

### 6.2 移动端路由分离（已实施）

```
mobile.py  ← iOS专用接口（数据结构针对移动端优化）
web.py     ← Web端接口（可返回更多字段）
```

### 6.3 多端AI协作提示词

```markdown
## 多端功能开发检查顺序

你正在为 [功能名] 实现多端支持，按以下顺序操作：

1. 更新 Pydantic 模型 (src/LucidPanda/models/)
2. 更新数据库层 (src/LucidPanda/db/)  
3. 更新 Service 层 (src/LucidPanda/services/)
4. 更新后端路由 (api/v1/routers/web.py 或 mobile.py)
5. 运行 `python -m scripts.generate_openapi` 更新API文档
6. 更新前端 hooks 和组件 (web/hooks/, web/components/)
7. 更新 iOS 数据模型和 ViewModel

每步完成后验证，不要一口气写完再测。
```

---

## 七、AI提示词模板库

### 7.1 新 API 端点开发

```markdown
# 角色
你是遵循 LucidPanda 架构规范的高级后端工程师。
请先阅读 CLAUDE.md 了解架构红线。

# 任务
在 [web.py / mobile.py] 中添加 [功能] API 端点。

# 约束（必须遵守）
- Router 只做参数验证 + 调用 Service，不写业务逻辑
- 业务逻辑写在 services/ 中的新方法或现有方法
- 请求/响应体用 Pydantic BaseModel 定义，放在 router 文件顶部
- 所有 DB 操作必须在 db/ 层，不在 service 中直接 execute SQL
- 参考 [get_fund_list()] 的实现风格

# 完成标准
- ruff check 无错误
- 有对应的 pytest 测试用例
- 类型注解完整
```

### 7.2 iOS 新功能模块

```markdown
# 角色
你是遵循 SwiftUI MVVM 规范的 iOS 工程师。
请先阅读 CLAUDE.md 和参考 Features/Funds/ 的结构。

# 任务
实现 [功能名] 功能模块。

# 约束
- 目录结构: Features/{Name}/Views/ + Features/{Name}/ViewModels/
- ViewModel 用 @Observable（iOS 17+）
- 网络请求统一走 Core/NetworkClient（或 APIClient）
- 新增的 API 响应字段先在 Data/ 中定义 Codable struct
- 所有用户可见字符串必须加入 Localizable.xcstrings

# 参考实现
参考 Features/Funds/ 的结构和风格
```

### 7.3 Bug修复（防止AI扩大影响范围）

```markdown
# 任务: 修复 Bug

## 问题描述
[具体现象，如何复现]

## 约束（严格遵守）
- 只修改导致 bug 的最小范围代码
- 不重构无关函数，不改变无关变量名
- 先写 failing test，修复后 test 应 pass
- 如果修复需要改动 web.py/watchlist_v2.py/fund_engine.py 这类高风险文件，
  先说明影响范围，等待确认

## 相关文件
[列出你认为相关的文件，我会确认]
```

---

## 八、CI/CD 质量门禁（见 .github/workflows/ci.yml）

```
每次 PR → 自动执行以下检查（全部通过才能合并）:
┌─────────────────────────────────────────┐
│ 1. ruff check (Python linting)          │
│ 2. mypy (Python 类型检查)               │
│ 3. pytest (后端单元测试，覆盖率 > 70%)  │
│ 4. tsc --noEmit (TypeScript 类型检查)   │
│ 5. eslint (前端代码规范)                │
│ 6. jest (前端单元测试)                  │
│ 7. 检测超大文件（> 500行发警告）        │
│ 8. 检测禁用模式（直连DB、裸print等）    │
└─────────────────────────────────────────┘
```

---

## 九、代码审查标准（AI代码专项）

### Review Checklist

```markdown
## AI生成代码审查清单

### 架构合规
- [ ] Router 是否直接写了业务逻辑或 SQL？（最常见问题）
- [ ] Service 是否直接 import 了数据库连接对象？
- [ ] 前端组件是否绕过 hooks 直接 fetch？
- [ ] iOS View 是否直接调用了网络请求？

### Python 特定
- [ ] async 函数中是否有未包装的同步 I/O（yfinance/akshare等）？
- [ ] 是否使用了裸 `print()` 而非 logger？
- [ ] SQL 是否使用了字符串拼接（SQL注入风险）？
- [ ] 是否有未处理的 None 值（AI常忽略 Optional）？

### TypeScript 特定
- [ ] 是否有 any 类型？（需注释说明理由）
- [ ] Promise 是否都有 await 或 .catch？
- [ ] 组件是否超过 300 行？（需拆分）

### AI特有问题
- [ ] 是否引入了已有库能解决的新依赖？
- [ ] 注释是否与代码逻辑一致？（AI常生成过时注释）
- [ ] 是否有复制粘贴的重复逻辑？
- [ ] 是否修改了不在任务范围内的代码？
```
