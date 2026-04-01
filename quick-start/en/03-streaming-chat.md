# Implement Streaming Chat

Streaming APIs emit many small events (text deltas, `content_block_delta`, partial tool JSON). This guide uses an **async iterator** to mimic SSE and shows how to **reassemble** a full `tool_use` payload.

## Prerequisites

```bash
pip install anthropic
```

The mock section runs without an API key.

## Core pattern

1. **Text**: concatenate `text_delta` chunks.
2. **Tools**: merge `partial_json` strings keyed by block `index`, then `json.loads`.

## Example: mock async stream + real API sketch

```python
"""Streaming: assemble text and tool_use JSON from fragments."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

async def mock_sse_events() -> AsyncIterator[dict[str, Any]]:
    """Simulate Anthropic-style streaming chunks."""
    yield {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
    for ch in "Hi ":
        yield {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": ch}}
    yield {"type": "content_block_stop", "index": 0}
    yield {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "tu_1", "name": "calculator"}}
    parts = ['{"exp', 'ression": "', '2+2"}']
    for p in parts:
        yield {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": p},
        }
    yield {"type": "content_block_stop", "index": 1}
    yield {"type": "message_delta", "delta": {"stop_reason": "tool_use"}}

async def consume_stream(events: AsyncIterator[dict[str, Any]]) -> dict[str, Any]:
    text_buf: list[str] = []
    json_buf: dict[int, list[str]] = {}
    tool_meta: dict[int, dict[str, str]] = {}

    async for ev in events:
        t = ev.get("type")
        if t == "content_block_start":
            idx = ev["index"]
            block = ev["content_block"]
            if block["type"] == "tool_use":
                tool_meta[idx] = {"id": block["id"], "name": block["name"]}
                json_buf[idx] = []
        elif t == "content_block_delta":
            idx = ev["index"]
            d = ev["delta"]
            if d["type"] == "text_delta":
                text_buf.append(d["text"])
            elif d["type"] == "input_json_delta":
                json_buf.setdefault(idx, []).append(d["partial_json"])
        elif t == "content_block_stop":
            pass

    tools = []
    for idx, chunks in json_buf.items():
        raw = "".join(chunks)
        tools.append({
            "id": tool_meta[idx]["id"],
            "name": tool_meta[idx]["name"],
            "input": json.loads(raw) if raw else {},
        })
    return {"text": "".join(text_buf), "tools": tools}

async def main() -> None:
    result = await consume_stream(mock_sse_events())
    print("text:", result["text"])
    print("tools:", result["tools"])

if __name__ == "__main__":
    asyncio.run(main())
```

### Anthropic streaming (API key required)

```python
import anthropic

async def stream_anthropic() -> None:
    client = anthropic.AsyncAnthropic()
    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{"role": "user", "content": "Say hi in one short sentence."}],
    ) as stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)
    print()

# asyncio.run(stream_anthropic())
```

The high-level `text_stream` helper is enough for chat. For **raw events** (including tool JSON deltas), use the lower-level event API for your SDK version.

## Summary

- Accumulate **`content_block_delta`** for text and `partial_json`.
- Align tool fragments with the **`index`** from `content_block_start`.
- Pair streaming with **retry/backoff** policies in production (`docs/en/12-api-streaming.md`).
