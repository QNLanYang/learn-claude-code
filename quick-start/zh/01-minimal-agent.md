# 用 50 行 Python 构建你的第一个 Agent

本教程实现一个**最小 Agent 循环**：调用大模型、解析 `tool_use`、执行计算器工具，直到模型不再请求工具。

## 前置条件

- Python 3.11+
- 可选：`pip install anthropic`，并设置环境变量 `ANTHROPIC_API_KEY`

若不配置 API，下面代码会使用**内置 mock 模型**，可直接运行。

## 完整可运行代码

将下列内容保存为 `minimal_agent.py` 后执行 `python minimal_agent.py`。

```python
"""Minimal agent loop with calculator tool (~50 lines)."""
from __future__ import annotations

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
    if "2+2" in last or "计算" in last:
        return {
            "content": [],
            "tool_calls": [{"name": "calculator", "input": {"expression": "2+2"}}],
        }
    if any(m.get("role") == "user" for m in messages[-2:]):
        return {"content": [{"type": "text", "text": "结果是 4。"}], "tool_calls": []}
    return {"content": [{"type": "text", "text": "你好，我是 mock 模型。"}], "tool_calls": []}

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
    messages: list[dict[str, Any]] = [{"role": "user", "content": "请用计算器算 2+2"}]
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

> **生产环境请勿使用 `eval`**。此处仅为最短示例；真实项目请用 `ast` 限制表达式或专用数学库。

## 流程说明

1. **消息列表** `messages` 保存多轮对话与工具结果。
2. **`call_llm`**：无 key 时走 `mock_llm`，否则走 Anthropic Messages API。
3. **若有 `tool_calls`**：把 assistant 消息追加到历史，执行工具，再以 `tool_result` 形式写回（Anthropic 真 API 需使用真实的 `tool_use_id`，此处 mock 用占位符）。
4. **若无工具**：打印文本并结束循环。

## 下一步

- 阅读 [02-add-a-tool.md](./02-add-a-tool.md) 学习结构化校验与多工具注册。
- 对照本仓库 `docs/zh/03-core-loop.md` 理解 Claude Code 中的异步生成器状态机。
