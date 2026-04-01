"""
Experiment 04 — Tool System

Replicates the tool definition, registration, and dispatch patterns from
src/Tool.ts, src/tools.ts, and src/services/tools/toolOrchestration.ts.

Key concepts demonstrated:
  1. Tool protocol with Pydantic input validation
  2. build_tool() factory with sensible defaults
  3. Tool registry with feature gates and filtering
  4. Batch execution: concurrent vs serial partitioning
  5. Result size limits with disk-spill simulation

Run:
    python -m exp_04_tool_system.main --mock
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# 1. Tool Interface (mirrors src/Tool.ts)
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    data: Any
    new_messages: list[dict[str, Any]] | None = None


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str
    is_concurrency_safe: bool
    is_read_only: bool
    is_enabled: bool

    def validate_input(self, raw_input: dict[str, Any]) -> Any: ...
    async def call(self, validated_input: Any, context: dict[str, Any]) -> ToolResult: ...
    def check_permissions(self, validated_input: Any, mode: str) -> str: ...
    def map_result(self, result: ToolResult, tool_use_id: str) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# 2. build_tool() factory (mirrors buildTool in src/Tool.ts)
# ---------------------------------------------------------------------------

def build_tool(
    *,
    name: str,
    description: str,
    input_model: type[BaseModel],
    call_fn: Any,
    is_concurrency_safe: bool = True,
    is_read_only: bool = True,
    is_enabled: bool = True,
    max_result_chars: int = 30_000,
) -> Tool:
    """Factory that builds a Tool with sensible defaults."""

    class BuiltTool:
        def __init__(self):
            self.name = name
            self.description = description
            self.is_concurrency_safe = is_concurrency_safe
            self.is_read_only = is_read_only
            self.is_enabled = is_enabled
            self._input_model = input_model
            self._call_fn = call_fn
            self._max_result_chars = max_result_chars

        def validate_input(self, raw_input: dict[str, Any]) -> Any:
            return self._input_model.model_validate(raw_input)

        async def call(self, validated_input: Any, context: dict[str, Any]) -> ToolResult:
            return await self._call_fn(validated_input, context)

        def check_permissions(self, validated_input: Any, mode: str) -> str:
            return "allow"

        def map_result(self, result: ToolResult, tool_use_id: str) -> dict[str, Any]:
            content = json.dumps(result.data) if not isinstance(result.data, str) else result.data
            if len(content) > self._max_result_chars:
                path = self._spill_to_disk(content, tool_use_id)
                content = f"[Result too large ({len(content)} chars). Saved to {path}. First 200 chars:]\n{content[:200]}"
            return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}

        def _spill_to_disk(self, content: str, tool_use_id: str) -> str:
            fd, path = tempfile.mkstemp(suffix=f"_{tool_use_id}.txt")
            with os.fdopen(fd, "w") as f:
                f.write(content)
            return path

    return BuiltTool()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 3. Concrete tools built with the factory
# ---------------------------------------------------------------------------

class GrepInput(BaseModel):
    pattern: str
    path: str = "."

async def grep_call(inp: GrepInput, ctx: dict[str, Any]) -> ToolResult:
    await asyncio.sleep(0.05)
    return ToolResult(data={"matches": [f"line 10: {inp.pattern} found", f"line 25: {inp.pattern} found"]})

grep_tool = build_tool(
    name="grep_search",
    description="Search files for a pattern",
    input_model=GrepInput,
    call_fn=grep_call,
    is_concurrency_safe=True,
    is_read_only=True,
)


class ReadFileInput(BaseModel):
    path: str

async def read_file_call(inp: ReadFileInput, ctx: dict[str, Any]) -> ToolResult:
    await asyncio.sleep(0.05)
    return ToolResult(data={"content": f"[content of {inp.path}]", "size": 1024})

read_file_tool = build_tool(
    name="read_file",
    description="Read a file's content",
    input_model=ReadFileInput,
    call_fn=read_file_call,
    is_concurrency_safe=True,
    is_read_only=True,
)


class WriteFileInput(BaseModel):
    path: str
    content: str

async def write_file_call(inp: WriteFileInput, ctx: dict[str, Any]) -> ToolResult:
    await asyncio.sleep(0.1)
    return ToolResult(data={"written": True, "path": inp.path, "bytes": len(inp.content)})

write_file_tool = build_tool(
    name="write_file",
    description="Write content to a file",
    input_model=WriteFileInput,
    call_fn=write_file_call,
    is_concurrency_safe=False,
    is_read_only=False,
)


class BashInput(BaseModel):
    command: str

async def bash_call(inp: BashInput, ctx: dict[str, Any]) -> ToolResult:
    await asyncio.sleep(0.1)
    return ToolResult(data={"stdout": f"[mock output of: {inp.command}]", "exit_code": 0})

bash_tool = build_tool(
    name="bash",
    description="Execute a shell command",
    input_model=BashInput,
    call_fn=bash_call,
    is_concurrency_safe=False,
    is_read_only=False,
)


class LargeResultInput(BaseModel):
    size: int = 50000

async def large_result_call(inp: LargeResultInput, ctx: dict[str, Any]) -> ToolResult:
    return ToolResult(data="x" * inp.size)

large_result_tool = build_tool(
    name="large_result",
    description="Returns a very large result to demo disk spill",
    input_model=LargeResultInput,
    call_fn=large_result_call,
    is_concurrency_safe=True,
    is_read_only=True,
    max_result_chars=1000,
    is_enabled=True,
)


# ---------------------------------------------------------------------------
# 4. Tool registry (mirrors src/tools.ts)
# ---------------------------------------------------------------------------

ALL_BASE_TOOLS: list[Tool] = [grep_tool, read_file_tool, write_file_tool, bash_tool, large_result_tool]

FEATURE_FLAGS = {"large_result": True}


def get_all_tools() -> list[Tool]:
    return list(ALL_BASE_TOOLS)


def get_tools(permission_mode: str = "default") -> list[Tool]:
    """Filter tools based on mode and feature flags."""
    result = []
    for tool in get_all_tools():
        if not tool.is_enabled:
            continue
        if tool.name in FEATURE_FLAGS and not FEATURE_FLAGS[tool.name]:
            continue
        if permission_mode == "plan" and not tool.is_read_only:
            continue
        result.append(tool)
    return result


def assemble_tool_pool(
    built_ins: list[Tool],
    mcp_tools: list[Tool],
) -> list[Tool]:
    """Merge built-in and MCP tools (built-ins win on name collision)."""
    by_name: dict[str, Tool] = {}
    for t in sorted(built_ins, key=lambda x: x.name):
        by_name.setdefault(t.name, t)
    for t in sorted(mcp_tools, key=lambda x: x.name):
        by_name.setdefault(t.name, t)
    return list(by_name.values())


def find_tool(name: str, pool: list[Tool]) -> Tool | None:
    for t in pool:
        if t.name == name:
            return t
    return None


# ---------------------------------------------------------------------------
# 5. Tool orchestration: partition and execute
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


def partition_tool_calls(
    calls: list[ToolCall],
    pool: list[Tool],
) -> list[list[ToolCall]]:
    """
    Partition tool calls into batches.
    Consecutive concurrency-safe tools form one concurrent batch.
    Non-safe tools each get their own serial batch.
    Mirrors partitionToolCalls in toolOrchestration.ts.
    """
    batches: list[list[ToolCall]] = []
    current_batch: list[ToolCall] = []

    for call in calls:
        tool = find_tool(call.name, pool)
        is_safe = tool.is_concurrency_safe if tool else False

        if is_safe:
            current_batch.append(call)
        else:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
            batches.append([call])

    if current_batch:
        batches.append(current_batch)

    return batches


async def execute_batch(
    batch: list[ToolCall],
    pool: list[Tool],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute a batch of tool calls (concurrently if >1)."""
    async def run_one(tc: ToolCall) -> dict[str, Any]:
        tool = find_tool(tc.name, pool)
        if not tool:
            return {"tool_use_id": tc.id, "error": f"Unknown tool: {tc.name}"}
        try:
            validated = tool.validate_input(tc.input)
        except ValidationError as e:
            return {"tool_use_id": tc.id, "error": str(e)}

        result = await tool.call(validated, context)
        return tool.map_result(result, tc.id)

    if len(batch) == 1:
        return [await run_one(batch[0])]
    return list(await asyncio.gather(*(run_one(tc) for tc in batch)))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 04: Tool System")
    parser.parse_args()

    header("Experiment 04: Tool System")

    # --- Registry demo ---
    section("Tool Registry")
    all_tools = get_tools("default")
    info(f"Default mode: {len(all_tools)} tools available")
    for t in all_tools:
        safe = colored("concurrent", "green") if t.is_concurrency_safe else colored("serial", "yellow")
        ro = "read-only" if t.is_read_only else "read-write"
        print(f"    {t.name:20s} [{safe}] [{ro}]  {t.description}")

    plan_tools = get_tools("plan")
    info(f"Plan mode: {len(plan_tools)} tools (read-only only)")

    # --- Validation demo ---
    section("Input Validation (Pydantic)")
    step(1, "Valid input for grep_search:")
    try:
        validated = grep_tool.validate_input({"pattern": "TODO", "path": "src/"})
        print(f"    Validated: pattern={validated.pattern}, path={validated.path}")
    except ValidationError as e:
        warn(f"Unexpected error: {e}")

    step(2, "Invalid input (missing required field):")
    try:
        grep_tool.validate_input({"path": "src/"})
        warn("Should have raised ValidationError!")
    except ValidationError as e:
        print(f"    Caught: {e.error_count()} error(s) — 'pattern' is required")

    # --- Batch execution demo ---
    section("Batch Execution (Concurrent vs Serial)")
    tool_calls = [
        ToolCall(id="tc_1", name="grep_search", input={"pattern": "TODO"}),
        ToolCall(id="tc_2", name="read_file", input={"path": "README.md"}),
        ToolCall(id="tc_3", name="write_file", input={"path": "out.txt", "content": "hello"}),
        ToolCall(id="tc_4", name="grep_search", input={"pattern": "FIXME"}),
    ]

    pool = get_tools()
    batches = partition_tool_calls(tool_calls, pool)
    info(f"4 tool calls partitioned into {len(batches)} batch(es):")
    for i, batch in enumerate(batches):
        mode = "CONCURRENT" if len(batch) > 1 else "SERIAL"
        names = [tc.name for tc in batch]
        print(f"    Batch {i + 1} ({mode}): {names}")

    step(3, "Executing all batches...")
    context = {"working_dir": "/tmp"}
    all_results = []
    for batch in batches:
        results = await execute_batch(batch, pool, context)
        all_results.extend(results)

    for r in all_results:
        tid = r.get("tool_use_id", "?")
        content = r.get("content", r.get("error", "?"))
        print(f"    {colored(tid, 'cyan')}: {content[:100]}")

    # --- Large result spill demo ---
    section("Result Size Limit & Disk Spill")
    step(4, "Calling large_result tool (50k chars, limit=1000)...")
    lt = find_tool("large_result", pool)
    if lt:
        validated = lt.validate_input({"size": 50000})
        result = await lt.call(validated, context)
        mapped = lt.map_result(result, "tc_large")
        print(f"    {colored('Mapped result:', 'yellow')} {mapped['content'][:120]}...")

    # --- Pool merge demo ---
    section("Tool Pool Assembly (Built-in + MCP)")
    mcp_grep = build_tool(
        name="grep_search",
        description="MCP grep (should be overridden by built-in)",
        input_model=GrepInput,
        call_fn=grep_call,
    )
    mcp_weather = build_tool(
        name="mcp__weather__forecast",
        description="MCP weather forecast",
        input_model=GrepInput,
        call_fn=grep_call,
    )
    merged = assemble_tool_pool(get_tools(), [mcp_grep, mcp_weather])
    info(f"Merged pool: {len(merged)} tools")
    for t in merged:
        origin = "MCP" if t.name.startswith("mcp__") else "built-in"
        print(f"    {t.name:30s}  [{origin}]")


if __name__ == "__main__":
    asyncio.run(main())
