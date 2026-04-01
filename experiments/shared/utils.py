"""
Common utilities for experiments: token counting, CLI setup, pretty output.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any


def count_tokens(text: str, method: str = "approximate") -> int:
    """Count tokens using tiktoken (if available) or char/4 approximation."""
    if method == "tiktoken":
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4o")
            return len(enc.encode(text))
        except ImportError:
            pass
    return max(1, len(text) // 4)


def count_messages_tokens(messages: list[dict[str, Any]], method: str = "approximate") -> int:
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content, method)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    total += count_tokens(block["text"], method)
    return total


def colored(text: str, color: str) -> str:
    """Return ANSI-colored text for terminal output."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "gray": "\033[90m",
        "bold": "\033[1m",
    }
    reset = "\033[0m"
    return f"{colors.get(color, '')}{text}{reset}"


def truncate_text(text: str, max_chars: int = 200) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def header(title: str) -> None:
    width = max(60, len(title) + 8)
    print(colored("=" * width, "cyan"))
    print(colored(f"    {title}", "bold"))
    print(colored("=" * width, "cyan"))


def section(title: str) -> None:
    print(f"\n{colored('--- ' + title + ' ---', 'yellow')}\n")


def step(num: int, desc: str) -> None:
    print(f"  {colored(f'[Step {num}]', 'green')} {desc}")


def info(msg: str) -> None:
    print(f"  {colored('INFO:', 'blue')} {msg}")


def warn(msg: str) -> None:
    print(f"  {colored('WARN:', 'yellow')} {msg}")


def error(msg: str) -> None:
    print(f"  {colored('ERROR:', 'red')} {msg}", file=sys.stderr)


def setup_argparser(description: str) -> argparse.ArgumentParser:
    """Create an argument parser with common --provider and --mock flags."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "mock"],
        default="mock",
        help="LLM provider to use (default: mock)",
    )
    parser.add_argument(
        "--mock",
        action="store_const",
        const="mock",
        dest="provider",
        help="Shorthand for --provider mock",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name override (provider-specific)",
    )
    return parser
