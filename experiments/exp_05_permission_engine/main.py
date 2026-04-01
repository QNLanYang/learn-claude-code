"""
Experiment 05 — Permission Engine

Replicates the permission decision flow from src/permissions/.

Key concepts demonstrated:
  1. Permission modes (default, plan, accept_edits, bypass)
  2. Rule-based allow/deny/ask with source priorities
  3. Pure decision function
  4. Interactive approval simulation
  5. Bypass-immune tool checks

Run:
    python -m exp_05_permission_engine.main --mock
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# Permission Modes
# ---------------------------------------------------------------------------

class PermissionMode(str, Enum):
    DEFAULT = "default"
    PLAN = "plan"
    ACCEPT_EDITS = "accept_edits"
    BYPASS = "bypass"


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


# ---------------------------------------------------------------------------
# Rule system
# ---------------------------------------------------------------------------

class RuleSource(str, Enum):
    SYSTEM = "system"
    PROJECT = "project"
    USER = "user"
    SESSION = "session"

RULE_PRIORITY = {
    RuleSource.SESSION: 0,
    RuleSource.USER: 1,
    RuleSource.PROJECT: 2,
    RuleSource.SYSTEM: 3,
}


@dataclass(frozen=True)
class PermissionRule:
    tool_pattern: str
    input_pattern: str | None
    decision: Decision
    source: RuleSource
    reason: str = ""

    @property
    def priority(self) -> int:
        return RULE_PRIORITY[self.source]


BYPASS_IMMUNE_TOOLS = frozenset({"bash", "write_file"})


# ---------------------------------------------------------------------------
# Permission decision engine (pure function)
# ---------------------------------------------------------------------------

def _pattern_matches(pattern: str, value: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def decide(
    tool_name: str,
    tool_input: dict[str, Any],
    mode: PermissionMode,
    rules: list[PermissionRule],
) -> tuple[Decision, str]:
    """
    Pure function: determine whether a tool call is allowed.

    Decision order:
      1. Mode-level overrides (plan blocks writes, bypass allows most)
      2. Explicit deny rules (highest priority first)
      3. Explicit allow rules
      4. Default: ask
    """
    if mode == PermissionMode.PLAN:
        if tool_name in ("write_file", "bash", "notebook_edit"):
            return Decision.DENY, f"Plan mode blocks write tool '{tool_name}'"

    if mode == PermissionMode.BYPASS:
        if tool_name not in BYPASS_IMMUNE_TOOLS:
            return Decision.ALLOW, "Bypass mode"

    if mode == PermissionMode.ACCEPT_EDITS:
        if tool_name in ("write_file", "notebook_edit"):
            return Decision.ALLOW, "Accept-edits mode auto-allows file writes"

    sorted_rules = sorted(rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        if not _pattern_matches(rule.tool_pattern, tool_name):
            continue
        if rule.input_pattern:
            input_str = str(tool_input)
            if not _pattern_matches(rule.input_pattern, input_str):
                continue
        return rule.decision, f"Rule: {rule.tool_pattern} ({rule.source.value}) -> {rule.decision.value}: {rule.reason}"

    return Decision.ASK, "No matching rule; asking user"


# ---------------------------------------------------------------------------
# Interactive approval simulation
# ---------------------------------------------------------------------------

async def interactive_approve(
    tool_name: str,
    tool_input: dict[str, Any],
    auto_approve: bool = True,
) -> bool:
    desc = f"{tool_name}({tool_input})"
    if auto_approve:
        info(f"Auto-approved: {desc}")
        return True
    print(f"  {colored('PERMISSION REQUEST:', 'yellow')} Allow {desc}? [y/n]")
    return True


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

SAMPLE_RULES = [
    PermissionRule("read_file", None, Decision.ALLOW, RuleSource.SYSTEM, "Reading is always safe"),
    PermissionRule("grep_search", None, Decision.ALLOW, RuleSource.SYSTEM, "Searching is safe"),
    PermissionRule("bash", "rm *", Decision.DENY, RuleSource.PROJECT, "Dangerous delete commands blocked"),
    PermissionRule("bash", None, Decision.ASK, RuleSource.USER, "Bash requires approval"),
    PermissionRule("write_file", "/etc/*", Decision.DENY, RuleSource.SYSTEM, "System files protected"),
    PermissionRule("write_file", None, Decision.ASK, RuleSource.USER, "File writes need approval"),
]


async def main() -> None:
    parser = setup_argparser("Experiment 05: Permission Engine")
    parser.parse_args()

    header("Experiment 05: Permission Engine")

    test_cases = [
        ("read_file", {"path": "src/main.py"}, PermissionMode.DEFAULT),
        ("write_file", {"path": "notes.txt", "content": "hello"}, PermissionMode.DEFAULT),
        ("write_file", {"path": "/etc/passwd", "content": "hacked"}, PermissionMode.DEFAULT),
        ("bash", {"command": "ls -la"}, PermissionMode.DEFAULT),
        ("bash", {"command": "rm -rf /tmp/test"}, PermissionMode.DEFAULT),
        ("write_file", {"path": "out.txt", "content": "ok"}, PermissionMode.PLAN),
        ("read_file", {"path": "data.json"}, PermissionMode.PLAN),
        ("bash", {"command": "echo hi"}, PermissionMode.BYPASS),
        ("write_file", {"path": "out.txt", "content": "ok"}, PermissionMode.BYPASS),
        ("write_file", {"path": "out.txt", "content": "ok"}, PermissionMode.ACCEPT_EDITS),
    ]

    section("Permission Decision Matrix")
    print(f"  {'Tool':<15} {'Input (summary)':<30} {'Mode':<15} {'Decision':<8} {'Reason'}")
    print(f"  {'-'*15} {'-'*30} {'-'*15} {'-'*8} {'-'*40}")

    for tool_name, tool_input, mode in test_cases:
        decision, reason = decide(tool_name, tool_input, mode, SAMPLE_RULES)

        input_summary = str(tool_input)[:28]
        color = {"allow": "green", "deny": "red", "ask": "yellow"}[decision.value]
        print(f"  {tool_name:<15} {input_summary:<30} {mode.value:<15} {colored(decision.value, color):<20} {reason}")

    section("Rule Priority Demonstration")
    step(1, "Rules sorted by priority (lower = higher priority):")
    for rule in sorted(SAMPLE_RULES, key=lambda r: r.priority):
        print(f"    [{rule.priority}] {rule.source.value:8s} | {rule.tool_pattern:15s} | {rule.decision.value:5s} | {rule.reason}")

    section("Bypass-Immune Tools")
    info(f"Even in bypass mode, these tools still require permission: {BYPASS_IMMUNE_TOOLS}")
    for tool in ["read_file", "bash", "write_file", "grep_search"]:
        decision, reason = decide(tool, {}, PermissionMode.BYPASS, SAMPLE_RULES)
        status = colored(decision.value, "green" if decision == Decision.ALLOW else "yellow")
        print(f"    {tool:20s} in bypass mode -> {status}  ({reason})")


if __name__ == "__main__":
    asyncio.run(main())
