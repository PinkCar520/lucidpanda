# LucidPanda 编码规范与架构准则 (v1.0)

> 本文档是 LucidPanda 项目的最高编码准则。Gemini 在进行任何代码修改、重构或新功能开发时，必须严格遵守。

## 1. 架构分层规范 (Architecture Layers)

### 1.1 Router (api/v1/routers/)
- **职责**：处理 HTTP 请求/响应，解析参数，处理 FastAPI 依赖注入。
- **禁令**：禁止写 SQL 语句，禁止写复杂的业务逻辑（如回测计算、情报聚类）。
- **规范**：必须定义 `response_model`，确保返回结构稳定。

### 1.2 Service (services/)
- **职责**：实现跨模块的业务逻辑。如 `AlphaEngine` 是典型的 Service，它调度 AI、DB 和推送通道。
- **规范**：Service 函数应是幂等的或具备良好的副作用说明。

### 1.3 Repository/CRUD (db/ / db/models/)
- **职责**：直接与数据库交互。
- **规范**：
    - 简单的查询使用 SQLModel/SQLAlchemy ORM。
    - 复杂的聚合查询（如 `/fused` 接口对应的 SQL）必须封装在特定的 Repo 类方法中（如 `IntelligenceRepo`）。
    - 严禁在 Repository 之外的地方手动归还连接池。

### 1.4 Models/Schemas (models/)
- **职责**：定义数据库表结构（SQLModel）和 API 传输对象（DTO）。
- **规范**：针对 JSONB 字段，必须在模型中明确其结构（使用 `Dict[str, Any]` 或嵌套模型）。

---

## 2. 编码风格与规范 (Coding Style)

### 2.1 命名约定
- **变量/函数**：`snake_case` (小写加下划线)。
- **类名**：`PascalCase` (大写首字母)。
- **常量**：`UPPER_SNAKE_CASE` (全大写加下划线)。

### 2.2 类型提示 (Type Hints)
- 所有函数签名必须包含参数类型和返回类型提示。
- 使用 `Optional`, `List`, `Dict` 等标准类型。

### 2.3 异常处理
- 禁止使用裸 `except:` 或 `except Exception: pass`。
- 关键路径必须记录日志：`logger.error(f"Failed to ..., error: {e}")`。

### 2.4 JSONB 字段规范
- 对于 `Intelligence` 表中的 `summary`, `sentiment`, `entities` 等字段，读写时必须确保其符合预期的 JSON 结构。

---

## 3. 技术路线守则 (Tech Stack)

### 3.1 数据库
- **PostgreSQL** 是唯一的持久化存储。
- **pgvector (HNSW)** 用于语义搜索，严禁在生产环境使用内存循环进行大规模语义比对。

### 3.2 AI 与新技术 (MCP/Skills)
- 遵循 **TDD (Test-Driven Development)**：在引入新技术（如 FastMCP）时，必须先编写测试 Demo (`tests/test_...`) 验证 API 正确性后再集成。
- **官方文档优先级**：模型在处理新技术时，如果内部知识与文档冲突，**必须以官方最新文档或源码示例为准**。

---

## 4. 特殊业务逻辑 (Domain Knowledge)

- **黄金 (Gold)** 是核心标的。分析时必须注入 `DXY`, `US10Y`, `GVZ` 等宏观快照。
- **实体归一化**：必须使用 `src/lucidpanda/utils/entity_normalizer.py` 处理实体名称。
- **置信度计算**：必须统一使用 `src/lucidpanda/utils/confidence.py`。
