# LucidPanda 技术参考锚点 (Tech Reference Anchors)

> **原则**：针对新技术（2024年以后面世或大幅更新的库），Gemini 严禁使用内部陈旧记忆。在编写代码前，必须通过 `web_fetch` 查阅下述官方文档或源码。

## 1. MCP (Model Context Protocol)
*   **官方 Python SDK**: [https://github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
*   **FastMCP (推荐)**: [https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/fastmcp.py](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/fastmcp.py)
*   **示例代码 (Examples)**: [https://github.com/modelcontextprotocol/python-sdk/tree/main/examples](https://github.com/modelcontextprotocol/python-sdk/tree/main/examples)
*   **测试用例 (Tests)**: [https://github.com/modelcontextprotocol/python-sdk/tree/main/tests](https://github.com/modelcontextprotocol/python-sdk/tree/main/tests)

## 2. Pydantic AI (Agent Framework)
*   **官方文档**: [https://pydantic-ai.pydantic.dev/](https://pydantic-ai.pydantic.dev/)
*   **GitHub 源码**: [https://github.com/pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai)
*   **Tools 示例**: [https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai/tools.py](https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai/tools.py)

## 3. Financial Quant (Math & Stats)
*   **Statsmodels OLS**: [https://www.statsmodels.org/stable/examples/notebooks/generated/ols.html](https://www.statsmodels.org/stable/examples/notebooks/generated/ols.html)
*   **QuantStats**: [https://github.com/ranaroussi/quantstats](https://github.com/ranaroussi/quantstats)

---

## 使用说明 (How to use)
1.  **禁止猜测**：凡是涉及 `FastMCP` 的类方法或参数，必须通过 `web_fetch` 抓取上述 `tests/` 或 `examples/` 中的 Raw 内容进行核实。
2.  **API 签名锚定**：抓取到的代码片段应优先关注装饰器格式（如 `@mcp.tool()`）、参数类型提示及异步 `async` 关键字的使用。
3.  **TDD 强制执行**：在正式集成到 `src/` 前，必须在 `tests/demo_...` 中运行抓取到的最小闭环代码。
