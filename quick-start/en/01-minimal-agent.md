# Build Your First Agent in 50 Lines of Python

This walkthrough implements a **minimal agent loop**: call an LLM, parse `tool_use`, run a calculator tool, and stop when the model no longer requests tools.

## Prerequisites

- Python 3.11+
- Optional: `pip install anthropic` and `ANTHROPIC_API_KEY` in the environment

If no API key is set, the script uses a **built-in mock model** so you can run it offline.

## Runnable script

Save as `minimal_agent.py` and run `python minimal_agent.py`.

```python
"""Minimal agent loop with calculator tool (~50 lines)."""
from __future__ import annotations

import json
import os
from typing import Any

USE_ANTHROPIC = bool(os.environ.get("ANTHROPIC_API_KEY"))

TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate a safe arithmetic expression with + - * / and parentheses.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    }
]

def run_calculator(expression: str) -> str:
    if not all(c in "0123456789+-*/(). " for c in expression):
        return "error: only digits and +-*/(). allowed"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"

def mock_llm(messages: list[dict[str, Any]]) -> dict[str, Any]:
    last = messages[-1]["content"]
    if isinstance(last, str) and ("2+2" in last):
        return {
            "content": [],
            "tool_calls": [{"name": "calculator", "input": {"expression": "2+2"}}],
        }
    if any(m.get("role") == "user" for m in messages[-2:]):
        return {"content": [{"type": "text", "text": "The answer is 4."}], "tool_calls": []}
    return {"content": [{"type": "text", "text": "Hello from mock model."}], "tool_calls": []}

def call_llm(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if not USE_ANTHROPIC:
        return mock_llm(messages)
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=TOOLS,
        messages=messages,
    )
    tool_calls = []
    text_parts = []
    for b in resp.content:
        if b.type == "text":
            text_parts.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            tool_calls.append({"name": b.name, "input": b.input})
    return {"content": text_parts, "tool_calls": tool_calls}

def main() -> None:
    messages: list[dict[str, Any]] = [{"role": "user", "content": "Use the calculator for 2+2"}]
    for _ in range(8):
        out = call_llm(messages)
        if out["tool_calls"]:
            messages.append({"role": "assistant", "content": out["content"] + [
                {"type": "tool_use", "name": tc["name"], "input": tc["input"]}
                for tc in out["tool_calls"]
            ]})
            for tc in out["tool_calls"]:
                if tc["name"] == "calculator":
                    result = run_calculator(tc["input"]["expression"])
                    messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": "local", "content": result}],
                    })
            continue
        print(out["content"][-1]["text"] if out["content"] else "(no text)")
        break

if __name__ == "__main__":
    main()
```

> **Do not use `eval` in production.** This keeps the line count tiny; real code should parse safely (e.g., `ast`) or use a math library.

## How it works

1. **`messages`** holds the full transcript including tool results.
2. **`call_llm`** uses the mock when no key is present; otherwise Anthropic Messages API.
3. **If there are tool calls**: append the assistant turn, execute tools, append `tool_result` user content (real APIs need proper `tool_use_id`; the mock uses a placeholder).
4. **If no tools**: print assistant text and exit the loop.

## Next steps

- [02-add-a-tool.md](./02-add-a-tool.md) — validation and registering multiple tools.
- `docs/en/03-core-loop.md` — how Claude Code models the loop with async generators.
