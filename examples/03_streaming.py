#!/usr/bin/env python3
"""Mock async SSE-like events; assemble text and tool_use JSON fragments."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator


async def fake_events() -> AsyncIterator[dict[str, Any]]:
    yield {"type": "cb_start", "index": 0, "block": {"kind": "text"}}
    for ch in "OK":
        yield {"type": "delta", "index": 0, "delta": {"kind": "text", "text": ch}}
    yield {"type": "cb_stop", "index": 0}
    yield {
        "type": "cb_start",
        "index": 1,
        "block": {"kind": "tool_use", "name": "calculator", "id": "t1"},
    }
    for frag in ['{"expr', 'ession":"7', '-2"}']:
        yield {"type": "delta", "index": 1, "delta": {"kind": "json", "partial": frag}}
    yield {"type": "cb_stop", "index": 1}


async def consume(events: AsyncIterator[dict[str, Any]]) -> dict[str, Any]:
    text: list[str] = []
    json_parts: dict[int, list[str]] = {}
    meta: dict[int, dict[str, str]] = {}

    async for ev in events:
        if ev["type"] == "cb_start":
            idx = ev["index"]
            b = ev["block"]
            if b["kind"] == "tool_use":
                meta[idx] = {"name": b["name"], "id": b["id"]}
                json_parts[idx] = []
        elif ev["type"] == "delta":
            idx = ev["index"]
            d = ev["delta"]
            if d["kind"] == "text":
                text.append(d["text"])
            elif d["kind"] == "json":
                json_parts.setdefault(idx, []).append(d["partial"])
        elif ev["type"] == "cb_stop":
            pass

    tools = []
    for idx, parts in json_parts.items():
        raw = "".join(parts)
        tools.append(
            {"id": meta[idx]["id"], "name": meta[idx]["name"], "input": json.loads(raw)}
        )
    return {"text": "".join(text), "tools": tools}


async def main() -> None:
    out = await consume(fake_events())
    print("assembled text:", repr(out["text"]))
    print("assembled tools:", out["tools"])


if __name__ == "__main__":
    asyncio.run(main())
