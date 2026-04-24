# DeepSeek V4 API Specification (Machine-Readable Context)

## 1. Global Configurations
- **Authentication**: `Authorization: Bearer <DEEPSEEK_API_KEY>`
- **Content-Type**: `application/json`
- **Base URLs**:
  - Standard (Chat, Balance): `https://api.deepseek.com`
  - Beta (FIM, Prefix Completion): `https://api.deepseek.com/beta`
  - Anthropic Compatible: `https://api.deepseek.com/anthropic`
- **Models**:
  - `deepseek-v4-pro`: Full reasoning, coding, long context (1M).
  - `deepseek-v4-flash`: Low cost, high speed, standard tasks.

---

## 2. Endpoints & Schemas

### 2.1 Chat Completions (Thinking Mode & Tool Calls)
**Endpoint**: `POST /chat/completions` (Standard Base URL)

**Request Body Schema**:
```json
{
  "model": "deepseek-v4-pro",
  "messages": [
    {
      "role": "system|user|assistant|tool",
      "content": "string",
      "name": "string (optional, for tool role)",
      "tool_call_id": "string (optional, for tool role)",
      "prefix": "boolean (optional, Beta only, forces continuation from this assistant message)",
      "reasoning_content": "string (optional, MUST be included for 'assistant' role if the previous turn contained tool_calls and thinking was enabled)"
    }
  ],
  "thinking": { "type": "enabled" | "disabled" },
  "reasoning_effort": "low|medium|high|max",
  "frequency_penalty": "number (-2.0 to 2.0, default 0, IGNORED if thinking=enabled)",
  "presence_penalty": "number (-2.0 to 2.0, default 0, IGNORED if thinking=enabled)",
  "temperature": "number (0.0 to 2.0, default 1.0, IGNORED if thinking=enabled)",
  "top_p": "number (0.0 to 1.0, default 1.0, IGNORED if thinking=enabled)",
  "max_tokens": "integer (up to 8192)",
  "response_format": { "type": "text" | "json_object" },
  "stop": ["string array"],
  "stream": "boolean",
  "stream_options": { "include_usage": true },
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "string",
        "description": "string",
        "parameters": { "type": "object", "properties": {} },
        "strict": "boolean (Beta, forces JSON schema compliance)"
      }
    }
  ],
  "tool_choice": "auto|none|required|{\"type\":\"function\",\"function\":{\"name\":\"...\"}}"
}
```

**Response Schema (Non-Streaming)**:
```json
{
  "id": "string",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-v4-pro",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "string (Final answer)",
        "reasoning_content": "string (Chain-of-thought, exists if thinking=enabled)",
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": { "name": "string", "arguments": "JSON string" }
          }
        ]
      },
      "finish_reason": "stop|length|tool_calls|content_filter"
    }
  ],
  "usage": {
    "prompt_tokens": "integer",
    "completion_tokens": "integer",
    "total_tokens": "integer",
    "prompt_cache_hit_tokens": "integer (Billed at 0.1 CNY/1M)",
    "prompt_cache_miss_tokens": "integer (Billed at 1.0 CNY/1M)"
  }
}
```

**Response Schema (Streaming - `stream: true`)**:
```json
{
  "id": "string",
  "object": "chat.completion.chunk",
  "created": 1234567890,
  "model": "deepseek-v4-pro",
  "choices": [
    {
      "index": 0,
      "delta": {
        "role": "assistant (optional)",
        "content": "string (partial answer)",
        "reasoning_content": "string (partial thought process)"
      },
      "finish_reason": "null|stop|length"
    }
  ]
}
```
*Note on Streaming*: If `stream_options.include_usage: true`, the final chunk will have empty choices and contain the `usage` object.

### 2.2 FIM Completion (Fill-In-The-Middle / Code Completion)
**Endpoint**: `POST /completions` (MUST use Beta Base URL)

**Request Body Schema**:
```json
{
  "model": "deepseek-v4-pro",
  "prompt": "string (Code before the cursor)",
  "suffix": "string (Code after the cursor, optional)",
  "max_tokens": "integer (Max 4000)",
  "temperature": "number",
  "top_p": "number",
  "stop": ["string array"]
}
```

**Response Schema**:
```json
{
  "id": "string",
  "object": "text_completion",
  "choices": [
    {
      "text": "string (The inserted code bridging prompt and suffix)",
      "index": 0,
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30 }
}
```

### 2.3 User Balance
**Endpoint**: `GET /user/balance` (Standard Base URL)

**Response Schema**:
```json
{
  "is_available": true,
  "balance_infos": [
    {
      "currency": "CNY",
      "total_balance": "100.00",
      "granted_balance": "10.00",
      "topped_up_balance": "90.00"
    }
  ]
}
```

---

## 3. Critical AI Implementation Rules (The "Soul")

### Rule 1: Tool Call Context Stitching (HTTP 400 Prevention)
When processing a multi-turn conversation where `tool_calls` occurred:
1. You MUST append the `assistant` message containing the `tool_calls` to the history.
2. If `thinking` was enabled, this `assistant` message MUST include the `reasoning_content` field exactly as returned by the API.
3. Omission of `reasoning_content` in a turn with `tool_calls` guarantees an **HTTP 400** error.
4. If NO tool calls occurred, `reasoning_content` does NOT need to be passed back.

### Rule 2: Context Caching Alignment
To hit the cache (`prompt_cache_hit_tokens`):
1. Prefix must be exactly identical (character for character).
2. Minimum length to trigger: 128 tokens.
3. Cache block size: 64 tokens (Only multiples of 64 are cached).
4. **Action**: Always put static `system` prompts and massive retrieved documents at the `index[0]` of the `messages` array. Never inject dynamic timestamps into the `system` prompt if caching is desired.

### Rule 3: JSON Mode Requirements
When `response_format={"type": "json_object"}` is set:
1. The word `"json"` (case-insensitive) MUST be present in either the `system` or `user` prompt.
2. If omitted, the model will return undefined behavior or loop indefinitely.

### Rule 4: OpenAI SDK Integration
DeepSeek V4 specific parameters (`thinking`, `reasoning_effort`) must be passed via `extra_body` in the official Python SDK, as they are not standard OpenAI kwargs:
```python
response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[...],
    extra_body={
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high" # or "max"
    }
)
# Extract reasoning:
reasoning = response.choices[0].message.reasoning_content
```
