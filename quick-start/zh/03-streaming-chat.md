# 实现流式对话

流式 API 将输出拆成多条事件（文本增量、`content_block_delta`、工具 JSON 片段）。本节用 **异步迭代** 模拟 SSE，并演示如何把 **tool_use** 的 JSON **拼完整**。

## 前置条件

```bash
pip install anthropic
```

可选：仅运行 mock 部分无需 API key。

## 核心模式

1. **文本**：把 `text_delta` 事件拼成字符串。
2. **工具**：模型可能分多包发送 `partial_json`；按 `index` 合并，最后 `json.loads`。

## 示例：Mock 异步流 + 真 API 简例

```python
"""Streaming: assemble text and tool_use JSON from fragments."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

async def mock_sse_events() -> AsyncIterator[dict[str, Any]]:
    """Simulate Anthropic-style streaming chunks."""
    yield {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
    for ch in "你好":
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

### 使用 Anthropic 流式（需 API key）

```python
import os
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

# asyncio.run(stream_anthropic())  # uncomment when ANTHROPIC_API_KEY is set
```

SDK 已封装文本流；若需 **底层事件**（含 tool JSON 增量），使用 `stream` 上原始事件 API（随 SDK 版本查阅 `message_stream_events` 或等价接口）。

## 小结

- 用 **`content_block_delta`** 累积文本与 `partial_json`。
- **tool 多个块** 用 `index` 对齐 `content_block_start` 里的元数据。
- 生产环境还需处理 **中断、重试、退避**（见 `docs/zh/12-api-streaming.md`）。
