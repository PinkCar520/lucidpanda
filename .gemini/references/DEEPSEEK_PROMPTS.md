# DeepSeek Prompt Library (Best Practices)

## 1. 结构化提示词 (Structured Prompting)
DeepSeek (尤其是非推理版本 `deepseek-v4-flash`) 对结构化提示词非常敏感。推荐使用清晰的边界符和编号来指导输出。

### 1.1 角色设定 (System Persona)
- **示例**: `你是一位大模型提示词生成专家...`
- **作用**: 设定上下文边界，限制模型自由发挥的范围。

### 1.2 明确格式 (Format Constraints)
- **示例**: `要求：1. 以 Markdown 格式输出`
- **作用**: 确保下游程序（如解析器）能够稳定解析输出。

### 1.3 负向约束 (Negative Constraints)
- **示例**: `4. 只输出提示词，不要输出多余解释`
- **作用**: 这是 API 调用中最核心的一点！防止模型输出 "好的，这是你的代码：" 这种破坏 JSON 或代码提取的开场白。

## 2. 核心场景模板 (Common Templates)

### 2.1 数据提取 (Data Extraction)
```text
[System]
你是一个数据提取专家。请从以下文本中提取所有的公司名称和股票代码。
必须以 JSON 数组格式输出，不要包含任何其他文字。
字段：company_name, stock_code

[User]
文本内容：...
```

### 2.2 代码重构 (Code Refactoring)
```text
[System]
你是一个资深的 Python 架构师。请重构以下代码：
要求：
1. 提高代码的可测试性（如依赖注入）。
2. 添加必要的类型提示 (Type Hints)。
3. 只输出重构后的代码，不解释。

[User]
代码：...
```

### 2.3 元提示词 (Meta-Prompting)
这就是你刚才展示的代码示例。让 AI 扮演“提示词工程师”，为你生成特定任务的完美提示词。

## 3. 参数配合建议
- **创意写作 / 角色扮演**: 提高 `temperature` (0.7 - 1.0)。
- **代码生成 / 数据提取**: 降低 `temperature` (0.0 - 0.3)，开启 `response_format={"type": "json_object"}`。
