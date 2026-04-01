"""
Experiment 06 — Prompt Assembly

Replicates the three-part context assembly from src/constants/prompts/.

Key concepts demonstrated:
  1. Static prefix + dynamic suffix with CACHE_BOUNDARY marker
  2. CLAUDE.md chain loading (cwd -> parent -> home)
  3. System context injection (git status, directory listing)
  4. Cache key computation (hash of static prefix)
  5. Final message array assembly for API call

Run:
    python -m exp_06_prompt_assembly.main --mock
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import UnifiedLLMClient
from shared.utils import (
    header, section, step, info, warn, colored, setup_argparser, count_tokens,
)


CACHE_BOUNDARY = "\n\n--- SYSTEM_PROMPT_DYNAMIC_BOUNDARY ---\n\n"

STATIC_SYSTEM_PROMPT = """You are Claude, an AI assistant made by Anthropic.

You are an expert software engineer with deep knowledge of:
- Multiple programming languages and frameworks
- Software architecture and design patterns
- Testing, debugging, and code review
- DevOps and deployment

You help users with coding tasks by reading files, searching code, writing code, and running commands.

IMPORTANT RULES:
- Always read before editing
- Prefer editing existing files over creating new ones
- Use immutable patterns where possible
- Handle errors explicitly
- Validate inputs at system boundaries"""


# ---------------------------------------------------------------------------
# Section helpers (mirrors cached / DANGEROUS_uncached pattern)
# ---------------------------------------------------------------------------

class PromptSection:
    def __init__(self, name: str, content: str, cached: bool = True):
        self.name = name
        self.content = content
        self.cached = cached

    def render(self) -> str:
        return f"\n## {self.name}\n{self.content}"


def get_system_prompt(sections: list[PromptSection]) -> str:
    """Assemble system prompt with cache boundary between static and dynamic parts."""
    static_parts = [STATIC_SYSTEM_PROMPT]
    dynamic_parts = []

    for s in sections:
        if s.cached:
            static_parts.append(s.render())
        else:
            dynamic_parts.append(s.render())

    static_text = "\n".join(static_parts)
    dynamic_text = "\n".join(dynamic_parts)

    if dynamic_text:
        return static_text + CACHE_BOUNDARY + dynamic_text
    return static_text


def compute_cache_key(system_prompt: str) -> str:
    """Hash only the static prefix (before CACHE_BOUNDARY) for prompt caching."""
    boundary_idx = system_prompt.find(CACHE_BOUNDARY)
    static_part = system_prompt[:boundary_idx] if boundary_idx >= 0 else system_prompt
    return hashlib.sha256(static_part.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# User context: CLAUDE.md chain
# ---------------------------------------------------------------------------

def get_user_context(cwd: str, sample_dir: str | None = None) -> str:
    """
    Load CLAUDE.md files walking from cwd up to root, plus ~/.claude/CLAUDE.md.
    Mirrors getUserContext() in src/constants/context.ts.
    """
    context_parts: list[str] = []

    if sample_dir:
        for name in ["CLAUDE.md", ".claude/CLAUDE.md"]:
            path = Path(sample_dir) / name
            if path.exists():
                context_parts.append(f"# From {path}\n{path.read_text()}")

    current = Path(cwd).resolve()
    visited = set()
    while current != current.parent:
        if current in visited:
            break
        visited.add(current)
        for name in ["CLAUDE.md", ".claude/CLAUDE.md"]:
            path = current / name
            if path.exists():
                context_parts.append(f"# From {path}\n{path.read_text()}")
        current = current.parent

    home_claude = Path.home() / ".claude" / "CLAUDE.md"
    if home_claude.exists():
        context_parts.append(f"# From {home_claude}\n{home_claude.read_text()}")

    return "\n\n".join(context_parts) if context_parts else "(no CLAUDE.md files found)"


# ---------------------------------------------------------------------------
# System context: git status, directory info
# ---------------------------------------------------------------------------

def get_system_context(cwd: str) -> str:
    """Gather runtime context (git status, directory listing, date)."""
    import datetime
    lines = [
        f"Current date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Working directory: {cwd}",
        f"OS: {sys.platform}",
        "",
        "Directory listing (simulated):",
        "  src/",
        "  tests/",
        "  docs/",
        "  README.md",
        "  pyproject.toml",
        "",
        "Git status (simulated):",
        "  On branch main",
        "  Your branch is up to date with 'origin/main'.",
        "  nothing to commit, working tree clean",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full assembly
# ---------------------------------------------------------------------------

def assemble_messages(
    system_prompt: str,
    user_context: str,
    system_context: str,
    user_message: str,
) -> dict[str, Any]:
    """Assemble the complete API request structure."""
    messages = []

    if user_context and user_context != "(no CLAUDE.md files found)":
        messages.append({
            "role": "user",
            "content": f"[User Context]\n{user_context}",
        })
        messages.append({
            "role": "assistant",
            "content": "I've read your project context. How can I help?",
        })

    messages.append({"role": "user", "content": user_message})

    if system_context:
        messages[-1]["content"] += f"\n\n[System Context]\n{system_context}"

    return {
        "system": system_prompt,
        "messages": messages,
    }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 06: Prompt Assembly")
    args = parser.parse_args()

    header("Experiment 06: Prompt Assembly")

    # Create sample CLAUDE.md files in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_md = Path(tmpdir) / "CLAUDE.md"
        claude_md.write_text(
            "# Project Guidelines\n\n"
            "- Use Python 3.11+\n"
            "- Follow PEP 8\n"
            "- Tests required for all new features\n"
            "- Use type hints everywhere\n"
        )

        section("1. System Prompt Assembly")
        sections = [
            PromptSection("Tool Usage", "Use tools to help the user. Always read before editing.", cached=True),
            PromptSection("Available Tools", "- read_file\n- write_file\n- bash\n- grep_search", cached=True),
            PromptSection("Current Session", "Session ID: abc123\nUser: developer", cached=False),
        ]

        system_prompt = get_system_prompt(sections)
        step(1, f"System prompt assembled: {count_tokens(system_prompt)} tokens")

        boundary_idx = system_prompt.find(CACHE_BOUNDARY)
        if boundary_idx >= 0:
            static_part = system_prompt[:boundary_idx]
            dynamic_part = system_prompt[boundary_idx + len(CACHE_BOUNDARY):]
            info(f"Static prefix: {count_tokens(static_part)} tokens (cacheable)")
            info(f"Dynamic suffix: {count_tokens(dynamic_part)} tokens (changes per session)")
        else:
            info("No cache boundary found (fully static prompt)")

        section("2. Cache Key Demonstration")
        key1 = compute_cache_key(system_prompt)
        step(2, f"Cache key: {key1}")

        sections_modified = sections.copy()
        sections_modified[-1] = PromptSection("Current Session", "Session ID: xyz789\nUser: admin", cached=False)
        system_prompt_2 = get_system_prompt(sections_modified)
        key2 = compute_cache_key(system_prompt_2)
        step(3, f"Same static, different dynamic -> key: {key2}")
        info(f"Keys match: {key1 == key2} (dynamic changes don't invalidate cache)")

        sections_modified[0] = PromptSection("Tool Usage", "CHANGED tool instructions", cached=True)
        system_prompt_3 = get_system_prompt(sections_modified)
        key3 = compute_cache_key(system_prompt_3)
        step(4, f"Changed static section -> key: {key3}")
        info(f"Keys match: {key1 == key3} (static changes DO invalidate cache)")

        section("3. User Context (CLAUDE.md Chain)")
        user_context = get_user_context(os.getcwd(), tmpdir)
        step(5, f"User context loaded: {count_tokens(user_context)} tokens")
        for line in user_context.split("\n")[:8]:
            print(f"    {colored(line, 'gray')}")

        section("4. System Context")
        system_context = get_system_context(os.getcwd())
        step(6, f"System context: {count_tokens(system_context)} tokens")
        for line in system_context.split("\n")[:6]:
            print(f"    {colored(line, 'gray')}")

        section("5. Full Message Assembly")
        request = assemble_messages(
            system_prompt=system_prompt,
            user_context=user_context,
            system_context=system_context,
            user_message="How do I add a new tool to the system?",
        )
        step(7, f"API request has {len(request['messages'])} messages")
        total_tokens = count_tokens(request["system"])
        for msg in request["messages"]:
            tokens = count_tokens(msg["content"])
            total_tokens += tokens
            role = msg["role"]
            preview = msg["content"][:80].replace("\n", " ")
            print(f"    [{colored(role, 'cyan')}] ({tokens} tokens) {preview}...")

        info(f"Total context: ~{total_tokens} tokens")


if __name__ == "__main__":
    asyncio.run(main())
