"""
Experiment 14 — Context Compaction

Replicates the compaction strategies from src/services/context/compact.ts.

Key concepts demonstrated:
  1. Token counting and threshold management
  2. Microcompact: truncate old tool results
  3. Autocompact: summarize middle messages when over threshold
  4. Force compact: user-triggered via /compact command
  5. Session memory extraction during compaction

Run:
    python -m exp_14_context_compaction.main --mock
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field, replace
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import UnifiedLLMClient
from shared.utils import (
    header, section, step, info, warn, colored, setup_argparser,
    count_tokens, count_messages_tokens,
)


# ---------------------------------------------------------------------------
# Token tracking state
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompactState:
    messages: tuple[dict[str, Any], ...]
    compact_boundary: int = 0  # index of last compaction point
    total_tokens: int = 0
    compaction_count: int = 0


@dataclass
class CompactConfig:
    autocompact_threshold: int = 2000  # tokens (low for demo)
    microcompact_after_turns: int = 2
    preserve_recent_messages: int = 4
    max_tool_result_chars: int = 200


# ---------------------------------------------------------------------------
# Microcompact: truncate old tool results
# ---------------------------------------------------------------------------

def microcompact(
    messages: list[dict[str, Any]],
    config: CompactConfig,
    current_turn: int,
) -> list[dict[str, Any]]:
    """
    Replace old tool_result content with truncated summaries.
    This reduces token count without losing structural information.
    Mirrors the per-iteration microcompact in query.ts.
    """
    result = []
    for i, msg in enumerate(messages):
        if (
            msg.get("role") == "tool_result"
            and i < len(messages) - config.preserve_recent_messages
        ):
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > config.max_tool_result_chars:
                truncated = content[:config.max_tool_result_chars]
                new_msg = {
                    **msg,
                    "content": f"[microcompacted] {truncated}...",
                    "_original_size": len(content),
                }
                result.append(new_msg)
                continue
        result.append(msg)
    return result


# ---------------------------------------------------------------------------
# Autocompact: summarize middle messages
# ---------------------------------------------------------------------------

async def autocompact(
    messages: list[dict[str, Any]],
    config: CompactConfig,
    client: UnifiedLLMClient,
) -> tuple[list[dict[str, Any]], str]:
    """
    When total tokens exceed threshold, summarize middle messages.
    Preserves: system prompt context + first user msg + last N messages.
    Mirrors compactConversation() in compact.ts.
    """
    total = count_messages_tokens(messages)
    if total <= config.autocompact_threshold:
        return messages, ""

    preserve_start = 1
    preserve_end = config.preserve_recent_messages
    middle = messages[preserve_start:-preserve_end] if preserve_end > 0 else messages[preserve_start:]

    if not middle:
        return messages, ""

    middle_text = "\n".join(
        f"[{m.get('role', '?')}]: {str(m.get('content', ''))[:200]}"
        for m in middle
    )

    summary_response = await client.chat(
        messages=[{
            "role": "user",
            "content": f"Summarize this conversation concisely:\n\n{middle_text}",
        }],
    )
    summary = summary_response.text

    compacted = (
        messages[:preserve_start]
        + [{"role": "user", "content": f"[Previous conversation summary]\n{summary}"},
           {"role": "assistant", "content": "I've reviewed the conversation summary. How can I continue helping?"}]
        + messages[-preserve_end:]
    )

    return compacted, summary


# ---------------------------------------------------------------------------
# Session memory extraction during compaction
# ---------------------------------------------------------------------------

def extract_session_memory(messages: list[dict[str, Any]]) -> list[str]:
    """Extract key facts from messages that are about to be compacted."""
    facts = []
    for msg in messages:
        content = str(msg.get("content", ""))
        if any(kw in content.lower() for kw in ["always", "prefer", "never", "important", "remember"]):
            fact = content[:150].strip()
            if fact:
                facts.append(fact)
    return facts


# ---------------------------------------------------------------------------
# Token warning states
# ---------------------------------------------------------------------------

def calculate_warning_state(
    total_tokens: int,
    threshold: int,
) -> str:
    ratio = total_tokens / threshold if threshold > 0 else 0
    if ratio < 0.5:
        return "normal"
    elif ratio < 0.8:
        return "warning"
    elif ratio < 1.0:
        return "critical"
    return "over_limit"


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def build_sample_conversation() -> list[dict[str, Any]]:
    """Build a sample conversation with tool calls to demonstrate compaction."""
    return [
        {"role": "user", "content": "I prefer using Python with type hints for everything. Please always follow PEP 8."},
        {"role": "assistant", "content": "Understood! I'll use Python with type hints and follow PEP 8 conventions."},
        {"role": "user", "content": "Read the main.py file and tell me what it does."},
        {"role": "assistant", "content": "I'll read the file for you."},
        {"role": "tool_result", "tool_use_id": "tu_1", "content": "def main():\n    " + "# Long function body\n    " * 50 + "pass"},
        {"role": "assistant", "content": "The main.py file contains a main() function with extensive logic."},
        {"role": "user", "content": "Now search for all TODO comments in the project."},
        {"role": "assistant", "content": "I'll search for TODO comments."},
        {"role": "tool_result", "tool_use_id": "tu_2", "content": "Found TODOs:\n" + "\n".join(f"src/file{i}.py:line{i*10}: TODO fix this" for i in range(30))},
        {"role": "assistant", "content": "I found 30 TODO comments across the project."},
        {"role": "user", "content": "Run the test suite with coverage."},
        {"role": "assistant", "content": "Running tests now."},
        {"role": "tool_result", "tool_use_id": "tu_3", "content": "Test Results:\n" + "\n".join(f"test_{i}: PASSED" for i in range(40)) + "\nCoverage: 87%"},
        {"role": "assistant", "content": "All 40 tests passed with 87% coverage. Important: The auth module needs more tests."},
        {"role": "user", "content": "Please write a summary of the codebase architecture."},
        {"role": "assistant", "content": "Based on my analysis, here's the architecture summary..."},
    ]


async def main() -> None:
    parser = setup_argparser("Experiment 14: Context Compaction")
    args = parser.parse_args()

    client = UnifiedLLMClient(provider=args.provider, model=args.model, scenario="compaction_demo")

    header("Experiment 14: Context Compaction")

    messages = build_sample_conversation()
    config = CompactConfig(
        autocompact_threshold=800,
        microcompact_after_turns=2,
        preserve_recent_messages=4,
        max_tool_result_chars=100,
    )

    section("1. Initial Conversation")
    total_tokens = count_messages_tokens(messages)
    step(1, f"Conversation: {len(messages)} messages, ~{total_tokens} tokens")
    warning = calculate_warning_state(total_tokens, config.autocompact_threshold)
    color = {"normal": "green", "warning": "yellow", "critical": "red", "over_limit": "red"}[warning]
    info(f"Warning state: {colored(warning, color)} (threshold: {config.autocompact_threshold})")

    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        content = str(msg.get("content", ""))[:60].replace("\n", " ")
        tokens = count_tokens(content)
        print(f"    [{i:2d}] {colored(role, 'cyan'):>20s}: {content}... ({tokens}t)")

    # --- Microcompact ---
    section("2. Microcompact (Truncate Old Tool Results)")
    step(2, "Applying microcompact to old tool_result messages...")
    micro_messages = microcompact(messages, config, current_turn=5)
    micro_tokens = count_messages_tokens(micro_messages)
    info(f"Before: {total_tokens} tokens -> After: {micro_tokens} tokens "
         f"(saved ~{total_tokens - micro_tokens} tokens)")

    for i, msg in enumerate(micro_messages):
        if msg.get("_original_size"):
            original = msg["_original_size"]
            current = len(str(msg.get("content", "")))
            print(f"    [{i:2d}] tool_result: {original} -> {current} chars "
                  f"({colored('microcompacted', 'yellow')})")

    # --- Autocompact ---
    section("3. Autocompact (Summarize Middle Messages)")
    step(3, f"Token count ({micro_tokens}) vs threshold ({config.autocompact_threshold})...")

    if micro_tokens > config.autocompact_threshold:
        info("Over threshold! Triggering autocompact...")

        session_facts = extract_session_memory(micro_messages[1:-config.preserve_recent_messages])
        if session_facts:
            step(4, f"Extracted {len(session_facts)} session memories before compacting:")
            for fact in session_facts:
                print(f"      - {colored(fact[:80], 'cyan')}")

        compacted, summary = await autocompact(micro_messages, config, client)
        compact_tokens = count_messages_tokens(compacted)
        info(f"After autocompact: {len(compacted)} messages, ~{compact_tokens} tokens")
        info(f"Reduction: {total_tokens} -> {compact_tokens} tokens "
             f"({colored(f'-{total_tokens - compact_tokens}', 'green')})")

        step(5, "Compacted conversation:")
        for i, msg in enumerate(compacted):
            role = msg.get("role", "?")
            content = str(msg.get("content", ""))[:70].replace("\n", " ")
            print(f"    [{i:2d}] {colored(role, 'cyan'):>20s}: {content}")
    else:
        info("Under threshold, no autocompact needed")
        compacted = micro_messages

    # --- Force compact ---
    section("4. Force Compact (User-Triggered /compact)")
    step(6, "Simulating /compact command...")
    force_config = CompactConfig(
        autocompact_threshold=0,
        preserve_recent_messages=2,
        max_tool_result_chars=50,
    )
    force_compacted, summary = await autocompact(compacted, force_config, client)
    force_tokens = count_messages_tokens(force_compacted)
    info(f"Force compact: {len(force_compacted)} messages, ~{force_tokens} tokens")

    # --- Summary ---
    section("5. Compaction Strategy Summary")
    print(f"    {'Strategy':<20} {'When':<30} {'What it does'}")
    print(f"    {'-'*20} {'-'*30} {'-'*40}")
    print(f"    {'Microcompact':<20} {'Each iteration':<30} {'Truncate old tool_result content'}")
    print(f"    {'Autocompact':<20} {'Tokens > threshold':<30} {'Summarize middle messages via LLM'}")
    print(f"    {'Force compact':<20} {'User /compact cmd':<30} {'Aggressive summarization'}")
    print()
    info(f"Token journey: {total_tokens} -> {micro_tokens} (micro) -> {count_messages_tokens(compacted)} (auto) -> {force_tokens} (force)")


if __name__ == "__main__":
    asyncio.run(main())
