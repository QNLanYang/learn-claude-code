#!/usr/bin/env python3
"""Dataclass-based tool schemas, registry, and dispatch from a mock LLM response."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CalcIn:
    expression: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CalcIn:
        if "expression" not in d or not isinstance(d["expression"], str):
            raise ValueError("expression must be a string")
        return cls(expression=d["expression"])


@dataclass
class GreetIn:
    name: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GreetIn:
        n = d.get("name", "")
        if not isinstance(n, str) or not n.strip():
            raise ValueError("name must be non-empty string")
        return cls(name=n.strip())


def run_calc(inp: CalcIn) -> str:
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in inp.expression):
        return "error: bad chars"
    try:
        return str(eval(inp.expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


def run_greet(inp: GreetIn) -> str:
    return f"Hello, {inp.name}!"


ToolFn = Callable[[Any], str]
REGISTRY: dict[str, tuple[type, ToolFn]] = {
    "calculator": (CalcIn, lambda x: run_calc(x)),
    "greet": (GreetIn, lambda x: run_greet(x)),
}


def dispatch(name: str, args: dict[str, Any]) -> str:
    if name not in REGISTRY:
        return f"unknown tool: {name}"
    cls, fn = REGISTRY[name]
    try:
        inp = cls.from_dict(args)
    except Exception as e:
        return f"validation error: {e}"
    return fn(inp)


def mock_llm_tool_calls() -> list[dict[str, Any]]:
    return [
        {"name": "greet", "input": {"name": "Ada"}},
        {"name": "calculator", "input": {"expression": "(1+2)*3"}},
    ]


def main() -> None:
    for call in mock_llm_tool_calls():
        result = dispatch(call["name"], call["input"])
        print(call["name"], "->", result)

    bad = dispatch("calculator", {"expression": 123})
    print("bad call ->", bad)


if __name__ == "__main__":
    main()
