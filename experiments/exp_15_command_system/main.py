"""
Experiment 15 — Command System

Replicates the slash command system from src/commands/.

Key concepts demonstrated:
  1. Command interface with name, type, call()
  2. Command registry and discovery
  3. Local vs prompt command types
  4. Command parsing from user input
  5. Command queue and lifecycle management

Run:
    python -m exp_15_command_system.main --mock
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# Command interface
# ---------------------------------------------------------------------------

@dataclass
class CommandResult:
    output: str
    inject_as_user_message: str | None = None  # for "prompt" type commands


@dataclass
class Command:
    name: str
    description: str
    cmd_type: str  # "local" (run directly) or "prompt" (inject into agent loop)
    aliases: list[str] = field(default_factory=list)
    is_enabled: Callable[[], bool] = field(default=lambda: True)
    handler: Callable[..., Awaitable[CommandResult]] | None = None
    prompt_template: str = ""

    async def call(self, args: str, context: dict[str, Any]) -> CommandResult:
        if self.cmd_type == "local" and self.handler:
            return await self.handler(args, context)
        elif self.cmd_type == "prompt":
            injected = self.prompt_template.replace("{args}", args).strip()
            return CommandResult(
                output=f"Injecting prompt for /{self.name}",
                inject_as_user_message=injected,
            )
        return CommandResult(output=f"No handler for /{self.name}")


# ---------------------------------------------------------------------------
# Built-in command handlers
# ---------------------------------------------------------------------------

async def compact_handler(args: str, ctx: dict[str, Any]) -> CommandResult:
    tokens_before = ctx.get("total_tokens", 5000)
    tokens_after = max(tokens_before // 3, 500)
    return CommandResult(
        output=f"Compacted: {tokens_before} -> {tokens_after} tokens (saved {tokens_before - tokens_after})"
    )


async def memory_handler(args: str, ctx: dict[str, Any]) -> CommandResult:
    parts = args.strip().split(maxsplit=1)
    action = parts[0] if parts else "list"
    memories = ctx.get("memories", ["User prefers Python", "Project uses asyncio"])

    if action == "list":
        mem_list = "\n".join(f"  - {m}" for m in memories)
        return CommandResult(output=f"Stored memories:\n{mem_list}")
    elif action == "save" and len(parts) > 1:
        memories.append(parts[1])
        return CommandResult(output=f"Saved: '{parts[1]}'")
    return CommandResult(output=f"Usage: /memory [list|save <text>]")


async def config_handler(args: str, ctx: dict[str, Any]) -> CommandResult:
    config = ctx.get("config", {"model": "claude-sonnet-4-20250514", "theme": "dark"})
    if args.strip():
        key = args.strip()
        val = config.get(key, "(not set)")
        return CommandResult(output=f"config.{key} = {val}")
    lines = "\n".join(f"  {k}: {v}" for k, v in config.items())
    return CommandResult(output=f"Current configuration:\n{lines}")


async def help_handler(args: str, ctx: dict[str, Any]) -> CommandResult:
    registry: CommandRegistry = ctx.get("registry")  # type: ignore[assignment]
    if not registry:
        return CommandResult(output="No registry available")
    commands = registry.get_enabled_commands()
    lines = [f"  /{c.name:15s} {c.description}" for c in commands]
    return CommandResult(output="Available commands:\n" + "\n".join(lines))


async def clear_handler(args: str, ctx: dict[str, Any]) -> CommandResult:
    return CommandResult(output="Conversation cleared. Starting fresh.")


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def find(self, name: str) -> Command | None:
        return self._commands.get(name)

    def get_enabled_commands(self) -> list[Command]:
        seen = set()
        result = []
        for cmd in self._commands.values():
            if cmd.name not in seen and cmd.is_enabled():
                seen.add(cmd.name)
                result.append(cmd)
        return sorted(result, key=lambda c: c.name)

    def get_completions(self, prefix: str) -> list[str]:
        return sorted(
            name for name in self._commands
            if name.startswith(prefix)
        )


# ---------------------------------------------------------------------------
# Command parsing
# ---------------------------------------------------------------------------

def parse_command_input(text: str) -> tuple[str, str] | None:
    """
    Parse '/command args' from user input.
    Returns (command_name, args) or None if not a command.
    """
    text = text.strip()
    if not text.startswith("/"):
        return None
    parts = text[1:].split(maxsplit=1)
    if not parts:
        return None
    name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    return name, args


# ---------------------------------------------------------------------------
# Command queue & lifecycle
# ---------------------------------------------------------------------------

@dataclass
class QueuedCommand:
    id: str
    name: str
    args: str
    status: str = "pending"  # pending, running, completed, failed


class CommandQueue:
    def __init__(self):
        self._queue: deque[QueuedCommand] = deque()
        self._history: list[QueuedCommand] = []

    def enqueue(self, name: str, args: str) -> QueuedCommand:
        cmd = QueuedCommand(id=str(uuid.uuid4())[:8], name=name, args=args)
        self._queue.append(cmd)
        return cmd

    def drain(self) -> list[QueuedCommand]:
        """Drain all pending commands."""
        commands = list(self._queue)
        self._queue.clear()
        return commands

    def complete(self, cmd: QueuedCommand, status: str = "completed") -> None:
        cmd.status = status
        self._history.append(cmd)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 15: Command System")
    parser.parse_args()

    header("Experiment 15: Command System")

    # Build registry
    registry = CommandRegistry()
    commands = [
        Command("compact", "Compact conversation context", "local", ["c"], handler=compact_handler),
        Command("memory", "Manage agent memory", "local", ["mem", "m"], handler=memory_handler),
        Command("config", "Show/get configuration", "local", ["cfg"], handler=config_handler),
        Command("help", "Show available commands", "local", ["h", "?"], handler=help_handler),
        Command("clear", "Clear conversation", "local", handler=clear_handler),
        Command("review", "Code review the current file", "prompt",
                prompt_template="Please review the following code for quality, security, and best practices:\n{args}"),
        Command("explain", "Explain code in detail", "prompt",
                prompt_template="Please explain this code in detail, covering the logic, patterns, and design decisions:\n{args}"),
    ]
    for cmd in commands:
        registry.register(cmd)

    context: dict[str, Any] = {
        "total_tokens": 5000,
        "memories": ["User prefers Python", "Project uses asyncio"],
        "config": {"model": "claude-sonnet-4-20250514", "theme": "dark", "vim_mode": True},
        "registry": registry,
    }

    section("1. Command Registry")
    step(1, f"Registered {len(registry.get_enabled_commands())} commands:")
    for cmd in registry.get_enabled_commands():
        type_color = "green" if cmd.cmd_type == "local" else "magenta"
        aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
        print(f"    /{cmd.name:<15s} [{colored(cmd.cmd_type, type_color)}] {cmd.description}{aliases}")

    section("2. Command Parsing")
    test_inputs = [
        "/compact",
        "/memory save Remember to use type hints",
        "/config model",
        "/review def add(a, b): return a+b",
        "Hello, this is not a command",
        "/",
        "/nonexistent foo",
    ]

    for text in test_inputs:
        parsed = parse_command_input(text)
        if parsed:
            name, args = parsed
            found = registry.find(name)
            status = colored("found", "green") if found else colored("not found", "red")
            print(f"    '{text[:50]:<50s}' -> /{name} ({status})")
        else:
            print(f"    '{text[:50]:<50s}' -> {colored('not a command', 'gray')}")

    section("3. Command Execution")
    executions = [
        "/help",
        "/compact",
        "/memory list",
        "/memory save Always validate inputs",
        "/config model",
        "/review def multiply(a, b): return a * b",
    ]

    for text in executions:
        parsed = parse_command_input(text)
        if not parsed:
            continue
        name, args = parsed
        cmd = registry.find(name)
        if not cmd:
            warn(f"Unknown command: /{name}")
            continue

        step(2, f"Executing: {text}")
        result = await cmd.call(args, context)
        for line in result.output.split("\n"):
            print(f"    {colored(line, 'green')}")
        if result.inject_as_user_message:
            print(f"    {colored('[Injected prompt]:', 'magenta')} {result.inject_as_user_message[:80]}...")

    section("4. Command Queue & Lifecycle")
    queue = CommandQueue()
    step(3, "Enqueuing commands...")
    q1 = queue.enqueue("compact", "")
    q2 = queue.enqueue("memory", "save queued item")
    info(f"Queue size: {len(queue._queue)}")

    step(4, "Draining queue...")
    drained = queue.drain()
    for qc in drained:
        info(f"  Processing: /{qc.name} {qc.args} (id={qc.id})")
        qc.status = "running"
        cmd = registry.find(qc.name)
        if cmd:
            await cmd.call(qc.args, context)
        queue.complete(qc)
        info(f"  -> {colored(qc.status, 'green')}")

    info(f"Queue empty: {len(queue._queue) == 0}, History: {len(queue._history)} commands")

    section("5. Tab Completion")
    step(5, "Completions for 'c': " + str(registry.get_completions("c")))
    step(6, "Completions for 'mem': " + str(registry.get_completions("mem")))

    section("Summary")
    info("Commands: /name args pattern, parsed from user input")
    info("Types: 'local' (run handler directly) vs 'prompt' (inject into agent loop)")
    info("Queue: enqueue -> drain -> execute -> complete lifecycle")


if __name__ == "__main__":
    asyncio.run(main())
