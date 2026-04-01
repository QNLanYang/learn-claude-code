# Add a Custom Tool to Your Agent

Building on a minimal loop, use **Pydantic** for tool inputs, a single **registry**, and a small **dispatcher** so new tools stay testable.

## Prerequisites

```bash
pip install pydantic anthropic
```

## Approach

1. Define each tool's arguments as a Pydantic `BaseModel`.
2. Keep a map from tool name to a runner that accepts validated models.
3. In the loop, `model_validate` the model JSON, then call the runner.

## Full example

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
    if isinstance(text, str) and "uppercase" in text.lower():
        return {"tool_calls": [{"name": "uppercase", "input": {"text": "hello"}}], "text": ""}
    if messages and "HELLO" in str(messages[-1]):
        return {"tool_calls": [], "text": "Done."}
    return {"tool_calls": [], "text": "Ask me to uppercase something."}

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
    messages: list[dict[str, Any]] = [{"role": "user", "content": "Uppercase the word hello"}]
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

## Takeaways

- **`input_schema`**: `Model.model_json_schema()` matches Claude tool definitions.
- **`dispatch`**: one place for validation errors and unknown tools.
- **Adding a tool**: new `BaseModel`, function, and two registry entries.

## Next

- [03-streaming-chat.md](./03-streaming-chat.md)
- `docs/en/04-tool-system.md`
