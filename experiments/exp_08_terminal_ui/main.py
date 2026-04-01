"""
Experiment 08 — Terminal UI

Demonstrates terminal UI patterns using Rich, inspired by Claude Code's
Ink-based rendering architecture.

Key concepts demonstrated:
  1. Rich Live display for streaming output
  2. Message rendering pipeline (user/assistant/tool)
  3. Styled prompt input
  4. Markdown rendering in terminal
  5. Simulated agent loop with live UI updates

Run:
    python -m exp_08_terminal_ui.main --mock
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, colored, setup_argparser

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ---------------------------------------------------------------------------
# Message types and rendering
# ---------------------------------------------------------------------------

def render_user_message(console: Any, content: str) -> None:
    console.print(Panel(
        Text(content, style="white"),
        title="[bold blue]User[/bold blue]",
        border_style="blue",
        padding=(0, 1),
    ))


def render_assistant_message(console: Any, content: str) -> None:
    try:
        md = Markdown(content)
        console.print(Panel(
            md,
            title="[bold green]Assistant[/bold green]",
            border_style="green",
            padding=(0, 1),
        ))
    except Exception:
        console.print(Panel(content, title="Assistant", border_style="green"))


def render_tool_call(console: Any, name: str, args: dict[str, Any]) -> None:
    import json
    content = Text()
    content.append(f"Tool: ", style="bold")
    content.append(f"{name}\n", style="bold magenta")
    content.append(f"Args: ", style="bold")
    content.append(json.dumps(args, indent=2), style="cyan")
    console.print(Panel(content, title="[bold yellow]Tool Call[/bold yellow]", border_style="yellow", padding=(0, 1)))


def render_tool_result(console: Any, name: str, result: str) -> None:
    content = Text()
    content.append(f"{name}: ", style="bold magenta")
    content.append(result[:200], style="dim")
    console.print(Panel(content, title="[bold cyan]Tool Result[/bold cyan]", border_style="cyan", padding=(0, 1)))


# ---------------------------------------------------------------------------
# Simulated streaming display
# ---------------------------------------------------------------------------

async def simulate_streaming_output(console: Any) -> None:
    """Simulate streaming text output character by character."""
    from rich.live import Live
    text = ("Here's a summary of the codebase:\n\n"
            "## Architecture\n\n"
            "The project follows a **layered architecture**:\n\n"
            "1. **Entry Layer** — CLI parsing and mode dispatch\n"
            "2. **Core Layer** — Agent loop and state machine\n"
            "3. **Service Layer** — API calls, tools, MCP\n"
            "4. **UI Layer** — Terminal rendering with Ink\n\n"
            "### Key Files\n\n"
            "- `src/query.ts` — Core agent loop\n"
            "- `src/Tool.ts` — Tool interface\n"
            "- `src/main.tsx` — Application entry\n")

    accumulated = ""
    with Live(console=console, refresh_per_second=15) as live:
        for char in text:
            accumulated += char
            try:
                live.update(Panel(
                    Markdown(accumulated),
                    title="[bold green]Assistant (streaming)[/bold green]",
                    border_style="green",
                ))
            except Exception:
                live.update(Panel(accumulated, title="Assistant", border_style="green"))
            await asyncio.sleep(0.02)


# ---------------------------------------------------------------------------
# Component tree visualization
# ---------------------------------------------------------------------------

def show_component_tree(console: Any) -> None:
    """Show the Claude Code UI component hierarchy."""
    tree = Tree("[bold]REPL.tsx[/bold]")
    messages = tree.add("[blue]Messages.tsx[/blue]")
    messages.add("[cyan]Message.tsx[/cyan] (per message)")
    messages.add("[cyan]ToolCallView[/cyan]")
    messages.add("[cyan]MarkdownRenderer[/cyan]")

    input_node = tree.add("[blue]PromptInput.tsx[/blue]")
    input_node.add("[cyan]InputArea[/cyan]")
    input_node.add("[cyan]CompletionMenu[/cyan]")

    status = tree.add("[blue]StatusBar[/blue]")
    status.add("[cyan]TokenCounter[/cyan]")
    status.add("[cyan]ModelIndicator[/cyan]")
    status.add("[cyan]CostTracker[/cyan]")

    tree.add("[blue]PermissionDialog[/blue]")
    tree.add("[blue]CompactIndicator[/blue]")

    console.print(Panel(tree, title="Component Tree (Ink Architecture)", border_style="bright_blue"))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 08: Terminal UI")
    parser.parse_args()

    if not HAS_RICH:
        header("Experiment 08: Terminal UI")
        print("\n  This experiment requires the 'rich' library.")
        print("  Install it with: pip install rich")
        print("  Then re-run this experiment.")
        return

    console = Console()

    header("Experiment 08: Terminal UI")

    section("1. Component Tree (Ink Architecture)")
    show_component_tree(console)

    section("2. Message Rendering Pipeline")
    step(1, "Rendering different message types...")

    render_user_message(console, "Read the main.py file and explain the architecture.")

    render_tool_call(console, "read_file", {"path": "src/main.py"})
    render_tool_result(console, "read_file", "def main():\n    app = Application()\n    app.run()")

    render_assistant_message(console, (
        "The `main.py` file contains the **application entry point**.\n\n"
        "It creates an `Application` instance and calls `run()`, which:\n"
        "1. Initializes the configuration\n"
        "2. Sets up the agent loop\n"
        "3. Starts the REPL interface\n\n"
        "```python\ndef main():\n    app = Application()\n    app.run()\n```"
    ))

    section("3. Streaming Output")
    step(2, "Simulating streaming text with live update...")
    await simulate_streaming_output(console)

    section("4. Status Display")
    table = Table(title="Session Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Model", "claude-sonnet-4-20250514")
    table.add_row("Input Tokens", "1,234")
    table.add_row("Output Tokens", "567")
    table.add_row("Cost", "$0.0089")
    table.add_row("Turn", "3")
    table.add_row("Context Usage", "15%")
    console.print(table)

    section("Summary")
    info("Claude Code uses React+Ink for terminal rendering (custom fork)")
    info("Messages are rendered through a pipeline: raw -> styled -> layout -> terminal")
    info("Rich provides similar capabilities in Python (panels, markdown, live updates)")


if __name__ == "__main__":
    asyncio.run(main())
