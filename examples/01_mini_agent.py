#!/usr/bin/env python3
"""Minimal agent + calculator; mock if no ANTHROPIC_API_KEY."""
from __future__ import annotations

import os
from typing import Any

USE_API = bool(os.environ.get("ANTHROPIC_API_KEY"))
TOOLS = [{
    "name": "calculator",
    "description": "Evaluate arithmetic (+ - * / parentheses).",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
}]


def calculator(expression: str) -> str:
    ok = set("0123456789+-*/(). ")
    if not all(c in ok for c in expression):
        return "error: invalid characters"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


def mock_complete(messages: list[dict[str, Any]]) -> dict[str, Any]:
    last = str(messages[-1].get("content", ""))
    if "3*4" in last or "12" in last:
        return {"blocks": [{"type": "text", "text": "The result is 12."}]}
    return {"blocks": [{"type": "tool_use", "id": "m1", "name": "calculator",
                        "input": {"expression": "3*4"}}]}


def anthropic_complete(messages: list[dict[str, Any]]) -> dict[str, Any]:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=256, tools=TOOLS, messages=messages)
    blocks: list[dict[str, Any]] = []
    for b in resp.content:
        if b.type == "text":
            blocks.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": dict(b.input)})
    return {"blocks": blocks}


def main() -> None:
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "What is 3*4? Use the calculator."}]
    for _ in range(6):
        out = anthropic_complete(messages) if USE_API else mock_complete(messages)
        tools = [b for b in out["blocks"] if b["type"] == "tool_use"]
        texts = [b["text"] for b in out["blocks"] if b["type"] == "text"]
        if not tools:
            print(texts[-1] if texts else "(no text)")
            break
        messages.append({"role": "assistant", "content": out["blocks"]})
        for t in tools:
            if t["name"] != "calculator":
                continue
            expr = t["input"].get("expression", "")
            res = calculator(expr)
            if USE_API:
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": t["id"], "content": res}]})
            else:
                messages.append({"role": "user", "content": f"tool_result: {res}"})


if __name__ == "__main__":
    main()
