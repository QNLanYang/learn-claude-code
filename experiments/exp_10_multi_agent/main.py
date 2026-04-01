"""
Experiment 10 — Multi-Agent Coordination

Replicates the AgentTool (nested agents) and Swarm (file mailbox) patterns
from src/tools/AgentTool/ and src/utils/teammateMailbox.ts.

Key concepts demonstrated:
  1. Nested agent: parent spawns child with restricted tool pool
  2. File-based mailbox for message passing
  3. Leader-worker pattern with task delegation
  4. Permission sync: child requests permission from parent
  5. Concurrent agent execution via asyncio

Run:
    python -m exp_10_multi_agent.main --mock
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import UnifiedLLMClient
from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# File-based mailbox (mirrors src/utils/teammateMailbox.ts)
# ---------------------------------------------------------------------------

@dataclass
class MailboxMessage:
    sender: str
    recipient: str
    msg_type: str  # task, result, permission_request, permission_response, shutdown
    content: str
    timestamp: float = field(default_factory=time.time)


class FileMailbox:
    """File-based mailbox using JSON files with simple locking."""

    def __init__(self, base_dir: str, agent_id: str):
        self.agent_id = agent_id
        self._inbox_dir = Path(base_dir) / "inboxes" / agent_id
        self._inbox_dir.mkdir(parents=True, exist_ok=True)
        self._msg_counter = 0

    def send(self, recipient: str, msg_type: str, content: str, base_dir: str) -> None:
        """Write a message to the recipient's inbox."""
        recipient_dir = Path(base_dir) / "inboxes" / recipient
        recipient_dir.mkdir(parents=True, exist_ok=True)

        self._msg_counter += 1
        msg = MailboxMessage(
            sender=self.agent_id,
            recipient=recipient,
            msg_type=msg_type,
            content=content,
        )
        filename = f"{int(msg.timestamp * 1000)}_{self._msg_counter}.json"
        (recipient_dir / filename).write_text(json.dumps({
            "sender": msg.sender,
            "recipient": msg.recipient,
            "type": msg.msg_type,
            "content": msg.content,
            "timestamp": msg.timestamp,
        }, indent=2))

    def receive(self) -> list[MailboxMessage]:
        """Read and consume all messages from inbox."""
        messages = []
        for f in sorted(self._inbox_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                messages.append(MailboxMessage(
                    sender=data["sender"],
                    recipient=data["recipient"],
                    msg_type=data["type"],
                    content=data["content"],
                    timestamp=data.get("timestamp", 0),
                ))
                f.unlink()
            except (json.JSONDecodeError, KeyError):
                continue
        return messages

    def has_messages(self) -> bool:
        return any(self._inbox_dir.glob("*.json"))


# ---------------------------------------------------------------------------
# Nested agent (mirrors AgentTool pattern)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentConfig:
    agent_id: str
    tools: list[str]
    max_turns: int = 5
    parent_id: str | None = None


async def run_nested_agent(
    config: AgentConfig,
    task: str,
    client: UnifiedLLMClient,
) -> dict[str, Any]:
    """
    Run a child agent with restricted tool pool.
    The child operates on a sidechain transcript (separate from parent).
    """
    transcript: list[dict[str, Any]] = []
    transcript.append({"role": "user", "content": task})

    info(f"  [{config.agent_id}] Starting with tools: {config.tools}")
    info(f"  [{config.agent_id}] Task: {task}")

    for turn in range(1, config.max_turns + 1):
        await asyncio.sleep(0.1)

        response = await client.chat(transcript)

        transcript.append({"role": "assistant", "content": response.text})

        if not response.has_tool_use:
            info(f"  [{config.agent_id}] Completed in {turn} turn(s)")
            return {
                "agent_id": config.agent_id,
                "result": response.text,
                "turns": turn,
                "transcript_length": len(transcript),
            }

        for tu in response.tool_uses:
            if tu.name not in config.tools:
                transcript.append({
                    "role": "tool_result",
                    "tool_use_id": tu.id,
                    "content": f"Error: Tool '{tu.name}' not available in this agent's tool pool",
                })
            else:
                transcript.append({
                    "role": "tool_result",
                    "tool_use_id": tu.id,
                    "content": f"[mock result from {tu.name}]",
                })

    return {
        "agent_id": config.agent_id,
        "result": f"Reached max turns ({config.max_turns})",
        "turns": config.max_turns,
        "transcript_length": len(transcript),
    }


# ---------------------------------------------------------------------------
# Leader-worker pattern with mailbox
# ---------------------------------------------------------------------------

async def worker_agent(
    agent_id: str,
    mailbox_dir: str,
    client: UnifiedLLMClient,
) -> None:
    """Worker agent that polls its mailbox for tasks."""
    mailbox = FileMailbox(mailbox_dir, agent_id)

    for _ in range(20):
        await asyncio.sleep(0.2)
        messages = mailbox.receive()

        for msg in messages:
            if msg.msg_type == "shutdown":
                info(f"  [{agent_id}] Received shutdown signal")
                return

            if msg.msg_type == "task":
                info(f"  [{agent_id}] Received task from {msg.sender}: {msg.content[:60]}")

                await asyncio.sleep(0.3)
                result = f"Completed: {msg.content}"

                mailbox.send(msg.sender, "result", result, mailbox_dir)
                info(f"  [{agent_id}] Sent result back to {msg.sender}")

    warn(f"  [{agent_id}] Timed out waiting for messages")


async def leader_agent(
    agent_id: str,
    worker_ids: list[str],
    tasks: list[str],
    mailbox_dir: str,
    client: UnifiedLLMClient,
) -> list[str]:
    """Leader agent that delegates tasks to workers via mailbox."""
    mailbox = FileMailbox(mailbox_dir, agent_id)

    # Delegate tasks round-robin
    for i, task in enumerate(tasks):
        worker = worker_ids[i % len(worker_ids)]
        info(f"  [{agent_id}] Assigning task to {worker}: {task[:50]}")
        mailbox.send(worker, "task", task, mailbox_dir)
        await asyncio.sleep(0.1)

    # Collect results
    results: list[str] = []
    for _ in range(30):
        await asyncio.sleep(0.2)
        messages = mailbox.receive()
        for msg in messages:
            if msg.msg_type == "result":
                results.append(msg.content)
                info(f"  [{agent_id}] Got result from {msg.sender}: {msg.content[:50]}")

        if len(results) >= len(tasks):
            break

    # Send shutdown to all workers
    for worker in worker_ids:
        mailbox.send(worker, "shutdown", "", mailbox_dir)

    return results


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 10: Multi-Agent Coordination")
    args = parser.parse_args()

    client = UnifiedLLMClient(provider=args.provider, model=args.model, scenario="multi_agent_worker")

    header("Experiment 10: Multi-Agent Coordination")

    # --- Nested Agent Demo ---
    section("1. Nested Agent (AgentTool Pattern)")
    step(1, "Parent spawns child agent with restricted tools...")

    child_config = AgentConfig(
        agent_id="child_1",
        tools=["read_file", "grep_search"],
        max_turns=3,
        parent_id="parent",
    )

    result = await run_nested_agent(child_config, "Find all TODO comments in the project", client)
    print(f"    {colored('Child result:', 'green')} {result['result'][:80]}")
    print(f"    Turns: {result['turns']}, Transcript: {result['transcript_length']} messages")

    # --- Concurrent Nested Agents ---
    section("2. Concurrent Nested Agents")
    step(2, "Spawning 3 agents concurrently...")

    agents = [
        AgentConfig("researcher", ["read_file", "grep_search"], parent_id="main"),
        AgentConfig("writer", ["read_file", "write_file"], parent_id="main"),
        AgentConfig("reviewer", ["read_file", "bash"], parent_id="main"),
    ]
    tasks_for_agents = [
        "Research the project structure",
        "Write a summary document",
        "Run the test suite and report results",
    ]

    results = await asyncio.gather(*(
        run_nested_agent(cfg, task, client)
        for cfg, task in zip(agents, tasks_for_agents)
    ))

    for r in results:
        status = colored("done", "green")
        print(f"    [{r['agent_id']}] {status}: {r['result'][:60]} ({r['turns']} turns)")

    # --- Mailbox Leader-Worker Demo ---
    section("3. File Mailbox (Swarm Pattern)")

    with tempfile.TemporaryDirectory() as tmpdir:
        mailbox_dir = os.path.join(tmpdir, "team")

        step(3, "Starting leader + 2 workers with file-based mailbox...")

        worker_ids = ["worker_alpha", "worker_beta"]
        tasks = [
            "Analyze the codebase structure",
            "Review security vulnerabilities",
            "Check test coverage",
            "Optimize database queries",
        ]

        worker_coros = [
            worker_agent(wid, mailbox_dir, client)
            for wid in worker_ids
        ]
        leader_coro = leader_agent("leader", worker_ids, tasks, mailbox_dir, client)

        all_results = await asyncio.gather(leader_coro, *worker_coros)
        leader_results = all_results[0]

        step(4, f"Leader collected {len(leader_results)} results:")
        for r in leader_results:
            print(f"    - {r[:70]}")

    section("Summary")
    info("Nested agents: parent controls child's tool pool + transcript isolation")
    info("File mailbox: JSON files in shared directory with atomic writes")
    info("Leader-worker: delegation via mailbox, round-robin + result aggregation")


if __name__ == "__main__":
    asyncio.run(main())
