"""
Experiment 16 — Design Patterns Cookbook

Demonstrates 6 key design patterns used in Claude Code, each as an
isolated, runnable example.

Key patterns demonstrated:
  1. Async Generator Pipeline
  2. Immutable State Machine
  3. Dependency Injection
  4. Factory with Defaults
  5. Layered Config Merge
  6. Concurrent Batch Partitioning

Run:
    python -m exp_16_design_patterns.main --mock
"""

from __future__ import annotations

import asyncio
import copy
import os
import sys
from dataclasses import dataclass, replace
from typing import Any, AsyncIterator, Protocol

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, colored, setup_argparser


# ===================================================================
# Pattern 1: Async Generator Pipeline
# ===================================================================

async def source(items: list[str]) -> AsyncIterator[str]:
    """Source generator: emits raw items."""
    for item in items:
        await asyncio.sleep(0.01)
        yield item


async def transform(upstream: AsyncIterator[str]) -> AsyncIterator[str]:
    """Transform: uppercase and filter."""
    async for item in upstream:
        if len(item) > 3:
            yield item.upper()


async def enrich(upstream: AsyncIterator[str]) -> AsyncIterator[dict[str, Any]]:
    """Enrich: add metadata to each item."""
    index = 0
    async for item in upstream:
        index += 1
        yield {"text": item, "index": index, "length": len(item)}


async def demo_async_generator_pipeline() -> None:
    section("Pattern 1: Async Generator Pipeline")
    info("Compose generators with yield* (Python: async for + yield)")

    items = ["hi", "hello", "world", "ok", "generator", "pipeline"]
    pipeline = enrich(transform(source(items)))

    step(1, "Pipeline: source -> transform -> enrich")
    async for result in pipeline:
        print(f"    {colored(str(result), 'cyan')}")

    info("Key insight: each stage lazily processes items; no intermediate lists")


# ===================================================================
# Pattern 2: Immutable State Machine
# ===================================================================

@dataclass(frozen=True)
class AppState:
    counter: int = 0
    status: str = "idle"
    history: tuple[str, ...] = ()


def transition(state: AppState, action: str) -> AppState:
    """Pure function: state + action -> new state (never mutates)."""
    if action == "start":
        return replace(state, status="running", history=(*state.history, "started"))
    elif action == "increment":
        return replace(state, counter=state.counter + 1, history=(*state.history, f"count={state.counter + 1}"))
    elif action == "stop":
        return replace(state, status="stopped", history=(*state.history, "stopped"))
    return state


async def demo_immutable_state_machine() -> None:
    section("Pattern 2: Immutable State Machine")
    info("State transitions return new states; originals are never mutated")

    state = AppState()
    actions = ["start", "increment", "increment", "increment", "stop"]

    step(2, "Applying actions to immutable state:")
    for action in actions:
        old_id = id(state)
        state = transition(state, action)
        new_id = id(state)
        mutated = "SAME" if old_id == new_id else "NEW"
        print(f"    {action:12s} -> counter={state.counter}, status={state.status} (object: {mutated})")

    info(f"History (audit trail): {list(state.history)}")
    info("Key insight: frozen dataclass + replace() ensures immutability")


# ===================================================================
# Pattern 3: Dependency Injection
# ===================================================================

class LLMProvider(Protocol):
    async def complete(self, prompt: str) -> str: ...

class ToolExecutor(Protocol):
    async def run(self, name: str, args: dict) -> str: ...


class MockLLM:
    async def complete(self, prompt: str) -> str:
        return f"Mock response to: {prompt[:30]}"

class MockTools:
    async def run(self, name: str, args: dict) -> str:
        return f"Mock result from {name}"


@dataclass
class AgentDeps:
    """Dependency container — swap implementations without changing agent logic."""
    llm: LLMProvider
    tools: ToolExecutor
    max_turns: int = 5


async def run_agent(deps: AgentDeps, query: str) -> str:
    """Agent logic that depends on abstractions, not concrete implementations."""
    response = await deps.llm.complete(query)
    tool_result = await deps.tools.run("search", {"q": query})
    return f"{response} | {tool_result}"


async def demo_dependency_injection() -> None:
    section("Pattern 3: Dependency Injection")
    info("Agent logic depends on protocols, not concrete classes")

    deps = AgentDeps(llm=MockLLM(), tools=MockTools(), max_turns=3)
    step(3, "Running agent with mock deps:")
    result = await run_agent(deps, "What is the weather?")
    print(f"    Result: {colored(result, 'green')}")

    info("Key insight: swap MockLLM/MockTools for real implementations without changing run_agent()")


# ===================================================================
# Pattern 4: Factory with Defaults
# ===================================================================

def build_config(
    name: str,
    *,
    timeout: float = 30.0,
    retries: int = 3,
    verbose: bool = False,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Factory that fills sensible defaults — caller only specifies what they need."""
    return {
        "name": name,
        "timeout": timeout,
        "retries": retries,
        "verbose": verbose,
        "headers": headers or {"User-Agent": "claude-experiment/1.0"},
    }


async def demo_factory_defaults() -> None:
    section("Pattern 4: Factory with Defaults")
    info("buildTool() pattern: sensible defaults, override only what you need")

    configs = [
        build_config("minimal"),
        build_config("custom", timeout=60.0, retries=5),
        build_config("verbose", verbose=True, headers={"Auth": "Bearer xxx"}),
    ]

    step(4, "Creating configs with varying specificity:")
    for cfg in configs:
        print(f"    {colored(cfg['name'], 'cyan')}: timeout={cfg['timeout']}, retries={cfg['retries']}, "
              f"verbose={cfg['verbose']}, headers={list(cfg['headers'].keys())}")

    info("Key insight: caller complexity scales with customization needs")


# ===================================================================
# Pattern 5: Layered Config Merge
# ===================================================================

def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


async def demo_layered_config() -> None:
    section("Pattern 5: Layered Config Merge")
    info("Multiple config sources merged by priority")

    layers = [
        ("defaults", {"model": "sonnet", "max_tokens": 4096, "features": {"vim": False, "mcp": True}}),
        ("user", {"model": "opus", "features": {"vim": True}}),
        ("project", {"max_tokens": 8192}),
        ("cli", {"features": {"mcp": False}}),
    ]

    step(5, "Merging layers (last wins):")
    merged: dict[str, Any] = {}
    for name, layer in layers:
        merged = deep_merge(merged, layer)
        print(f"    + {name:12s} -> {merged}")

    info("Key insight: deep merge for nested dicts, replace for scalars and arrays")


# ===================================================================
# Pattern 6: Concurrent Batch Partitioning
# ===================================================================

@dataclass
class Task:
    name: str
    is_safe: bool

    async def run(self) -> str:
        await asyncio.sleep(0.05)
        return f"{self.name}: done"


def partition(tasks: list[Task]) -> list[list[Task]]:
    """Split tasks: consecutive safe tasks form concurrent batches, unsafe run alone."""
    batches: list[list[Task]] = []
    current: list[Task] = []
    for task in tasks:
        if task.is_safe:
            current.append(task)
        else:
            if current:
                batches.append(current)
                current = []
            batches.append([task])
    if current:
        batches.append(current)
    return batches


async def demo_batch_partitioning() -> None:
    section("Pattern 6: Concurrent Batch Partitioning")
    info("Safe tasks run concurrently; unsafe tasks run serially")

    tasks = [
        Task("read_A", True),
        Task("read_B", True),
        Task("read_C", True),
        Task("write_X", False),
        Task("read_D", True),
        Task("write_Y", False),
    ]

    batches = partition(tasks)
    step(6, f"Partitioned {len(tasks)} tasks into {len(batches)} batches:")

    all_results = []
    for i, batch in enumerate(batches):
        names = [t.name for t in batch]
        mode = "CONCURRENT" if len(batch) > 1 else "SERIAL"
        print(f"    Batch {i + 1} ({mode}): {names}")

        if len(batch) > 1:
            results = await asyncio.gather(*(t.run() for t in batch))
        else:
            results = [await batch[0].run()]
        all_results.extend(results)

    info(f"Results: {all_results}")
    info("Key insight: maximize parallelism while respecting ordering constraints")


# ===================================================================
# Main
# ===================================================================

async def main() -> None:
    parser = setup_argparser("Experiment 16: Design Patterns Cookbook")
    parser.parse_args()

    header("Experiment 16: Design Patterns Cookbook")
    info("6 patterns extracted from Claude Code's architecture\n")

    await demo_async_generator_pipeline()
    await demo_immutable_state_machine()
    await demo_dependency_injection()
    await demo_factory_defaults()
    await demo_layered_config()
    await demo_batch_partitioning()

    section("Design Philosophy Summary")
    patterns = [
        ("Async Generators", "Lazy, composable data pipelines"),
        ("Immutable State", "Safe transitions, audit trail, no hidden mutations"),
        ("Dependency Injection", "Swap implementations via protocols"),
        ("Factory Defaults", "Complexity scales with customization"),
        ("Layered Config", "Multiple sources, deep merge, clear precedence"),
        ("Batch Partitioning", "Maximize concurrency within ordering constraints"),
    ]
    for name, desc in patterns:
        print(f"    {colored(name, 'cyan'):>40s}  {desc}")


if __name__ == "__main__":
    asyncio.run(main())
