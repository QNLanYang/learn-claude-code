# 给 Agent 添加自定义工具

在最小循环之上，用 **Pydantic** 为工具参数建模，统一 **注册表** 与 **调度**，便于扩展与测试。

## 前置条件

```bash
pip install pydantic anthropic
```

## 思路

1. 用 Pydantic `BaseModel` 描述每个工具的输入。
2. 维护 `dict[str, Callable]`：名称 → 校验后的执行函数。
3. Agent 循环里根据模型返回的 `name` + `input` 字典，先 `model_validate` 再调用。

## 完整示例

```python
"""Agent with Pydantic-validated custom tools."""
from __future__ import annotations

import os
from typing import Any, Callable

from pydantic import BaseModel, Field

class UpperArgs(BaseModel):
    text: str = Field(min_length=1, max_length=500)

class WordCountArgs(BaseModel):
    text: str

def tool_upper(args: UpperArgs) -> str:
    return args.text.upper()

def tool_word_count(args: WordCountArgs) -> str:
    return str(len(args.text.split()))

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "uppercase",
        "description": "Convert text to uppercase.",
        "input_schema": UpperArgs.model_json_schema(),
    },
    {
        "name": "word_count",
        "description": "Count whitespace-separated words.",
        "input_schema": WordCountArgs.model_json_schema(),
    },
]

TOOL_RUNNERS: dict[str, tuple[type[BaseModel], Callable[[Any], str]]] = {
    "uppercase": (UpperArgs, lambda a: tool_upper(a)),
    "word_count": (WordCountArgs, lambda a: tool_word_count(a)),
}

def dispatch(name: str, raw: dict[str, Any]) -> str:
    if name not in TOOL_RUNNERS:
        return f"unknown tool: {name}"
    model_cls, fn = TOOL_RUNNERS[name]
    try:
        validated = model_cls.model_validate(raw)
    except Exception as e:
        return f"validation error: {e}"
    return fn(validated)

def mock_llm(messages: list[dict[str, Any]]) -> dict[str, Any]:
    text = messages[-1]["content"]
    if isinstance(text, str) and "大写" in text:
        return {"tool_calls": [{"name": "uppercase", "input": {"text": "hello"}}], "text": ""}
    if messages and "HELLO" in str(messages[-1]):
        return {"tool_calls": [], "text": "已转为大写。"}
    return {"tool_calls": [], "text": "请说「转大写」。"}

def call_llm(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return mock_llm(messages)
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        tools=TOOL_SPECS,
        messages=messages,
    )
    tool_calls = []
    text = ""
    for b in resp.content:
        if b.type == "text":
            text += b.text
        elif b.type == "tool_use":
            tool_calls.append({"name": b.name, "input": b.input})
    return {"tool_calls": tool_calls, "text": text}

def main() -> None:
    messages: list[dict[str, Any]] = [{"role": "user", "content": "请把 hello 转大写"}]
    for _ in range(6):
        out = call_llm(messages)
        if out["tool_calls"]:
            for tc in out["tool_calls"]:
                result = dispatch(tc["name"], tc["input"])
                messages.append({"role": "assistant", "content": out["text"]})
                messages.append({"role": "user", "content": f"tool_result: {result}"})
            continue
        print(out["text"] or "(empty)")
        break

if __name__ == "__main__":
    main()
```

## 要点

- **`input_schema`**：直接用 `Model.model_json_schema()` 生成 JSON Schema，与 Claude 工具格式对齐。
- **`dispatch`**：单一入口做校验与错误信息，避免在每个工具里重复 `try/except`。
- **注册新工具**：增加 `BaseModel`、实现函数、在 `TOOL_SPECS` 与 `TOOL_RUNNERS` 各加一项即可。

## 延伸阅读

- [03-streaming-chat.md](./03-streaming-chat.md)
- 本仓库 `docs/zh/04-tool-system.md`
