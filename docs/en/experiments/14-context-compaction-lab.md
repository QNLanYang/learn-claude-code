# Context Compaction Lab [Core]

**Experiment:** `experiments/exp_14_context_compaction/main.py`

## Objective

Contrast **microcompact** (truncate old tool results), **autocompact** (LLM summary of the middle), **force compact** (user `/compact`), and **session memory extraction**—aligned with `src/services/context/compact.ts` and per-turn trimming ideas in the query path.

## Source mapping (Claude Code)

| Piece | TypeScript |
|-------|------------|
| Compaction strategies | `src/services/context/compact.ts` |
| Ongoing context trimming (related) | `src/query.ts` |

## Architecture

```mermaid
flowchart TD
  M[messages] --> U{tokens > threshold?}
  M --> MC[microcompact old tool_result]
  MC --> U
  U -->|yes| AC[autocompact: summarize middle]
  AC --> SM[extract_session_memory]
  U -->|no| OK[keep]
  FC[/compact] --> AC2[force aggressive autocompact]
```

## Key code walkthrough

**Microcompact** preserves structure, shrinks stale tool payloads:

```58:85:experiments/exp_14_context_compaction/main.py
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
```

**Autocompact** calls the LLM for a middle summary:

```92:133:experiments/exp_14_context_compaction/main.py
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
    # ... build middle_text, await client.chat for summary, splice messages ...
```

**Force compact** in the demo sets `autocompact_threshold=0` to always summarize (see `main()` section “Force Compact”).

## How to run

```bash
cd experiments
python -m exp_14_context_compaction.main --mock
python -m exp_14_context_compaction.main --provider anthropic
python -m exp_14_context_compaction.main --provider openai
```

## Exercises

1. Track **`compact_boundary`** in `CompactState` and log what the model can still “see.”
2. Replace heuristic **`extract_session_memory`** with a small structured LLM call.
3. Integrate **microcompact** into **`exp_03` `agent_loop`** after each tool round.

## Next experiment

**[Command System Lab](./15-command-system-lab.md)** (Comprehensive) wires `/compact` and other slash commands into the REPL.
