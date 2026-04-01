"""Core data types shared across experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    text: str = ""
    tool_uses: list[ToolUseBlock] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    stop_reason: str = "end_turn"

    @property
    def has_tool_use(self) -> bool:
        return len(self.tool_uses) > 0


@dataclass
class StreamEvent:
    type: str  # content_delta, tool_use_start, tool_use_delta, tool_use_end, message_stop
    text: str = ""
    tool_use: ToolUseBlock | None = None
    partial_json: str = ""
    index: int = 0
