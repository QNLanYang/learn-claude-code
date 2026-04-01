"""
Predefined mock LLM responses for offline experiment execution.

Each scenario maps to a sequence of responses indexed by call_count.
"""

from __future__ import annotations

from typing import Any

from .types import LLMResponse, StreamEvent, ToolUseBlock

SCENARIOS: dict[str, list[LLMResponse]] = {
    "default": [
        LLMResponse(text="Hello! I'm a mock assistant. How can I help you?"),
    ],

    "agent_loop_calculator": [
        LLMResponse(
            text="I'll calculate that for you.",
            tool_uses=[ToolUseBlock(id="tu_1", name="calculator", input={"expression": "2 + 3 * 4"})],
            stop_reason="tool_use",
        ),
        LLMResponse(
            text="The result of 2 + 3 * 4 is 14.",
            stop_reason="end_turn",
        ),
    ],

    "agent_loop_multi_tool": [
        LLMResponse(
            text="Let me read the file and calculate.",
            tool_uses=[
                ToolUseBlock(id="tu_1", name="read_file", input={"path": "data.txt"}),
                ToolUseBlock(id="tu_2", name="calculator", input={"expression": "100 / 5"}),
            ],
            stop_reason="tool_use",
        ),
        LLMResponse(
            text="The file contains 'Hello World' and 100/5 = 20.",
            stop_reason="end_turn",
        ),
    ],

    "tool_system_demo": [
        LLMResponse(
            text="I'll search for that and read the file.",
            tool_uses=[
                ToolUseBlock(id="tu_1", name="grep_search", input={"pattern": "TODO", "path": "."}),
                ToolUseBlock(id="tu_2", name="read_file", input={"path": "README.md"}),
            ],
            stop_reason="tool_use",
        ),
        LLMResponse(
            text="I'll now write the result to a file.",
            tool_uses=[
                ToolUseBlock(id="tu_3", name="write_file", input={"path": "output.txt", "content": "Done"}),
            ],
            stop_reason="tool_use",
        ),
        LLMResponse(text="All tasks completed.", stop_reason="end_turn"),
    ],

    "permission_demo": [
        LLMResponse(
            tool_uses=[ToolUseBlock(id="tu_1", name="read_file", input={"path": "/etc/hosts"})],
            stop_reason="tool_use",
        ),
        LLMResponse(
            tool_uses=[ToolUseBlock(id="tu_2", name="bash", input={"command": "rm -rf /tmp/test"})],
            stop_reason="tool_use",
        ),
        LLMResponse(
            tool_uses=[ToolUseBlock(id="tu_3", name="write_file", input={"path": "notes.txt", "content": "ok"})],
            stop_reason="tool_use",
        ),
        LLMResponse(text="Permission demo complete.", stop_reason="end_turn"),
    ],

    "prompt_assembly": [
        LLMResponse(text="I can see the system prompt has static and dynamic sections."),
    ],

    "memory_recall": [
        LLMResponse(
            text="Let me save this to memory.",
            tool_uses=[ToolUseBlock(id="tu_1", name="memory_write", input={
                "topic": "preferences",
                "content": "User prefers dark mode and Python.",
            })],
            stop_reason="tool_use",
        ),
        LLMResponse(text="Saved! I'll remember your preferences."),
    ],

    "memory_extract": [
        LLMResponse(text="Key facts: 1) User prefers Python. 2) Project uses asyncio. 3) Testing with pytest."),
    ],

    "streaming_demo": [
        LLMResponse(
            text="Let me calculate that for you step by step.",
            tool_uses=[ToolUseBlock(id="tu_1", name="calculator", input={"expression": "42 * 17"})],
            stop_reason="tool_use",
        ),
        LLMResponse(text="The answer is 714.", stop_reason="end_turn"),
    ],

    "compaction_demo": [
        LLMResponse(text="Summary: The conversation discussed Python async patterns, "
                         "tool systems, and agent architecture. Key decisions: use asyncio "
                         "for concurrency, Pydantic for validation."),
    ],

    "multi_agent_leader": [
        LLMResponse(
            text="I'll delegate subtasks to worker agents.",
            tool_uses=[ToolUseBlock(id="tu_1", name="spawn_agent", input={
                "task": "Search for Python best practices",
                "agent_id": "worker_1",
            })],
            stop_reason="tool_use",
        ),
        LLMResponse(
            text="Worker 1 found the information. Now delegating to worker 2.",
            tool_uses=[ToolUseBlock(id="tu_2", name="spawn_agent", input={
                "task": "Summarize the findings",
                "agent_id": "worker_2",
            })],
            stop_reason="tool_use",
        ),
        LLMResponse(text="Both workers completed. Final report compiled."),
    ],

    "multi_agent_worker": [
        LLMResponse(text="Task completed: Found 5 Python best practices including type hints, "
                         "virtual environments, and testing."),
    ],

    "mcp_demo": [
        LLMResponse(
            tool_uses=[ToolUseBlock(id="tu_1", name="mcp__weather__get_forecast", input={"city": "Tokyo"})],
            stop_reason="tool_use",
        ),
        LLMResponse(text="The weather in Tokyo is sunny, 22°C."),
    ],

    "startup_flow": [
        LLMResponse(text="Application initialized successfully."),
    ],

    "plugin_skill": [
        LLMResponse(text="Loaded 3 plugins and 5 skills from the skills directory."),
    ],

    "config_demo": [
        LLMResponse(text="Configuration merged from 4 layers: system, user, project, local."),
    ],

    "command_system": [
        LLMResponse(text="Executed /compact command. Context reduced from 50k to 8k tokens."),
    ],
}

STREAM_SCENARIOS: dict[str, list[list[StreamEvent]]] = {
    "default": [[
        StreamEvent(type="content_delta", text="Hello"),
        StreamEvent(type="content_delta", text="! How can"),
        StreamEvent(type="content_delta", text=" I help you?"),
        StreamEvent(type="message_stop"),
    ]],

    "streaming_demo": [
        [
            StreamEvent(type="content_delta", text="Let me "),
            StreamEvent(type="content_delta", text="calculate that."),
            StreamEvent(
                type="tool_use_start",
                tool_use=ToolUseBlock(id="tu_1", name="calculator", input={}),
                index=1,
            ),
            StreamEvent(type="tool_use_delta", partial_json='{"expr', index=1),
            StreamEvent(type="tool_use_delta", partial_json='ession":', index=1),
            StreamEvent(type="tool_use_delta", partial_json=' "42 * 17"}', index=1),
            StreamEvent(type="tool_use_end", index=1),
            StreamEvent(type="message_stop"),
        ],
        [
            StreamEvent(type="content_delta", text="The answer"),
            StreamEvent(type="content_delta", text=" is 714."),
            StreamEvent(type="message_stop"),
        ],
    ],

    "agent_loop_calculator": [
        [
            StreamEvent(type="content_delta", text="I'll calculate."),
            StreamEvent(
                type="tool_use_start",
                tool_use=ToolUseBlock(id="tu_1", name="calculator", input={}),
                index=1,
            ),
            StreamEvent(type="tool_use_delta", partial_json='{"expression": "2 + 3 * 4"}', index=1),
            StreamEvent(type="tool_use_end", index=1),
            StreamEvent(type="message_stop"),
        ],
        [
            StreamEvent(type="content_delta", text="The result is 14."),
            StreamEvent(type="message_stop"),
        ],
    ],
}


def get_mock_response(scenario: str, call_count: int) -> LLMResponse:
    responses = SCENARIOS.get(scenario, SCENARIOS["default"])
    idx = min(call_count - 1, len(responses) - 1)
    return responses[idx]


def get_mock_stream_events(scenario: str, call_count: int) -> list[StreamEvent]:
    streams = STREAM_SCENARIOS.get(scenario, STREAM_SCENARIOS["default"])
    idx = min(call_count - 1, len(streams) - 1)
    return streams[idx]
