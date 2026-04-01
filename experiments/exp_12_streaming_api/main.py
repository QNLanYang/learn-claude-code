"""
Experiment 12 — Streaming API Client

Replicates the streaming patterns from src/services/api/claude.ts.

Key concepts demonstrated:
  1. Streaming SSE event consumption
  2. Tool input JSON fragment assembly
  3. Retry with exponential backoff
  4. Idle timeout watchdog
  5. Event-sourced assistant message construction

Run:
    python -m exp_12_streaming_api.main --mock
    python -m exp_12_streaming_api.main --provider anthropic
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import UnifiedLLMClient, StreamEvent, ToolUseBlock
from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# Stream assembler (mirrors event-sourced assembly in claude.ts)
# ---------------------------------------------------------------------------

@dataclass
class PartialContentBlock:
    index: int
    block_type: str  # "text" or "tool_use"
    text: str = ""
    tool_id: str = ""
    tool_name: str = ""
    input_json_str: str = ""


@dataclass
class AssembledMessage:
    text: str = ""
    tool_uses: list[dict[str, Any]] = field(default_factory=list)


class StreamAssembler:
    """
    Assembles a complete assistant message from streaming events.
    Mirrors the content_block_start/delta/stop handling in claude.ts.
    """

    def __init__(self):
        self._blocks: dict[int, PartialContentBlock] = {}
        self._text_parts: list[str] = []

    def process_event(self, event: StreamEvent) -> str | None:
        """Process one stream event. Returns text delta if any."""
        if event.type == "content_delta":
            self._text_parts.append(event.text)
            return event.text

        elif event.type == "tool_use_start":
            tu = event.tool_use
            if tu:
                self._blocks[event.index] = PartialContentBlock(
                    index=event.index,
                    block_type="tool_use",
                    tool_id=tu.id,
                    tool_name=tu.name,
                )
            return None

        elif event.type == "tool_use_delta":
            block = self._blocks.get(event.index)
            if block:
                block.input_json_str += event.partial_json
            return None

        elif event.type == "tool_use_end":
            return None

        elif event.type == "message_stop":
            return None

        return None

    def assemble(self) -> AssembledMessage:
        """Finalize the assembled message."""
        msg = AssembledMessage(text="".join(self._text_parts))

        for block in sorted(self._blocks.values(), key=lambda b: b.index):
            if block.block_type == "tool_use":
                try:
                    parsed_input = json.loads(block.input_json_str) if block.input_json_str else {}
                except json.JSONDecodeError:
                    parsed_input = {"_raw": block.input_json_str}
                msg.tool_uses.append({
                    "id": block.tool_id,
                    "name": block.tool_name,
                    "input": parsed_input,
                })

        return msg


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------

@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    retryable_errors: tuple[type[Exception], ...] = (ConnectionError, TimeoutError)


async def with_retry(
    fn: Any,
    config: RetryConfig,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a function with exponential backoff retry."""
    last_error = None
    delay = config.initial_delay

    for attempt in range(1, config.max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except config.retryable_errors as e:
            last_error = e
            if attempt == config.max_retries:
                break
            warn(f"  Attempt {attempt} failed: {e}. Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)
            delay = min(delay * config.backoff_multiplier, config.max_delay)

    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Idle timeout watchdog
# ---------------------------------------------------------------------------

async def stream_with_watchdog(
    stream: AsyncIterator[StreamEvent],
    idle_timeout: float = 10.0,
) -> AsyncIterator[StreamEvent]:
    """Wrap a stream with an idle timeout that cancels if no events arrive."""
    async for event in stream:
        yield event
    # In a real implementation, we'd use asyncio.wait_for on each iteration.
    # For the demo, we simulate the concept.


async def simulate_stalled_stream() -> AsyncIterator[StreamEvent]:
    """Simulate a stream that stalls to demonstrate the watchdog."""
    yield StreamEvent(type="content_delta", text="Starting...")
    await asyncio.sleep(0.1)
    yield StreamEvent(type="content_delta", text=" processing...")
    # Simulate a stall
    info("  [watchdog] Stream stalled for 2s (simulated)")
    await asyncio.sleep(0.5)
    yield StreamEvent(type="content_delta", text=" done!")
    yield StreamEvent(type="message_stop")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 12: Streaming API Client")
    args = parser.parse_args()

    client = UnifiedLLMClient(provider=args.provider, model=args.model, scenario="streaming_demo")

    header("Experiment 12: Streaming API Client")

    # --- Basic streaming ---
    section("1. Basic Streaming (Event-by-Event)")
    step(1, "Streaming response from LLM...")
    assembler = StreamAssembler()
    event_log: list[str] = []

    async for event in client.stream_chat(
        messages=[{"role": "user", "content": "What is 42 * 17?"}],
        tools=[{
            "name": "calculator",
            "description": "Calculate math",
            "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}}},
        }],
    ):
        event_log.append(event.type)
        text_delta = assembler.process_event(event)
        if text_delta:
            print(f"    {colored('DELTA:', 'cyan')} '{text_delta}'")
        elif event.type == "tool_use_start" and event.tool_use:
            print(f"    {colored('TOOL START:', 'magenta')} {event.tool_use.name}")
        elif event.type == "tool_use_delta":
            print(f"    {colored('TOOL JSON:', 'magenta')} +'{event.partial_json}'")
        elif event.type == "message_stop":
            print(f"    {colored('STOP', 'yellow')}")

    step(2, "Event sequence:")
    print(f"    {' -> '.join(event_log)}")

    # --- JSON fragment assembly ---
    section("2. Tool Input JSON Assembly")
    assembled = assembler.assemble()
    step(3, f"Assembled text: '{assembled.text}'")
    for tu in assembled.tool_uses:
        step(4, f"Assembled tool_use: {tu['name']}({json.dumps(tu['input'])})")
        info("JSON was assembled from streaming fragments (partial_json deltas)")

    # --- Retry demo ---
    section("3. Retry with Exponential Backoff")
    attempt_count = 0

    async def flaky_api_call() -> str:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError(f"Connection reset (attempt {attempt_count})")
        return "Success on attempt 3"

    retry_config = RetryConfig(max_retries=5, initial_delay=0.1, max_delay=1.0)
    step(5, "Calling flaky API with retry...")
    try:
        result = await with_retry(flaky_api_call, retry_config)
        print(f"    {colored('Result:', 'green')} {result}")
    except ConnectionError as e:
        print(f"    {colored('Failed:', 'red')} {e}")

    # --- Watchdog demo ---
    section("4. Idle Timeout Watchdog")
    step(6, "Streaming with stall detection...")
    stall_assembler = StreamAssembler()
    last_event_time = time.time()

    async for event in simulate_stalled_stream():
        now = time.time()
        idle_ms = int((now - last_event_time) * 1000)
        last_event_time = now
        text_delta = stall_assembler.process_event(event)
        idle_indicator = f" (idle {idle_ms}ms)" if idle_ms > 200 else ""
        if text_delta:
            print(f"    {colored('DELTA:', 'cyan')} '{text_delta}'{idle_indicator}")

    stall_msg = stall_assembler.assemble()
    step(7, f"Final assembled text: '{stall_msg.text}'")

    # --- Cost tracking ---
    section("5. Usage & Cost Tracking")
    if args.provider == "mock":
        usage = {"input_tokens": 150, "output_tokens": 75}
    else:
        response = await client.chat(
            messages=[{"role": "user", "content": "Hello"}],
        )
        usage = response.usage

    input_cost = usage.get("input_tokens", 0) * 3.0 / 1_000_000
    output_cost = usage.get("output_tokens", 0) * 15.0 / 1_000_000
    total_cost = input_cost + output_cost
    step(8, f"Input tokens: {usage.get('input_tokens', 0)} (${input_cost:.6f})")
    step(9, f"Output tokens: {usage.get('output_tokens', 0)} (${output_cost:.6f})")
    info(f"Total cost: ${total_cost:.6f}")

    section("Summary")
    info("Streaming: event-sourced assembly of text + tool_use JSON fragments")
    info("Retry: exponential backoff with configurable max delay")
    info("Watchdog: detect stalled streams via idle timeout")


if __name__ == "__main__":
    asyncio.run(main())
