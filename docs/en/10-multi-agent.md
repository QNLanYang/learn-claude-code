# Multi-Agent Coordination (Swarm / Tasks)

Claude Code supports multiple collaboration modes: nested sub-agents, swarm teams, and background tasks.

## Layer 1: AgentTool -- Nested Sub-Agents

`AgentTool` spawns a constrained sub-agent in-process, reusing the `query()` loop with a restricted tool pool (excluding `ALL_AGENT_DISALLOWED_TOOLS`). Sub-agent conversations are recorded as sidechain transcripts.

```typescript
// src/tools/AgentTool/runAgent.ts
async function* runAgent(prompt, context, options) {
    // Build constrained tool pool -> build sub-agent system prompt
    // -> call query() -> record sidechain transcript -> yield events
}
```

## Layer 2: Swarm Teams

### In-Process Teammates

Run in the same process using `AsyncLocalStorage` (`runWithTeammateContext`) for context isolation.

### External Process Teammates

Spawned via tmux or iTerm backends (`src/utils/swarm/backends/`), running independent Claude Code instances with shared CLI flags from `spawnUtils.ts`.

### File Mailbox Communication

```typescript
// src/utils/teammateMailbox.ts
// Path: .claude/teams/<session>/inboxes/<agent-id>.json
sendMessage(targetId, msg)  // write to target's inbox
readMessages(myId)          // read own inbox
```

Messages include work assignments, progress reports, permission requests/responses, and completion notifications. File locks ensure concurrency safety.

### Permission Synchronization

Teammates send permission requests via mailbox to the leader, who handles user approval and propagates results back.

## Layer 3: Task Framework

Unifies "things running in parallel with the main session":

| Type | Description |
|------|-------------|
| `LocalAgentTask` | Background sub-agent |
| `InProcessTeammateTask` | In-process teammate |
| `LocalMainSessionTask` | Background main session (Ctrl+B) |
| `RemoteAgentTask` | Remote agent task |
| `DreamTask` | Auto-dream task |
| `LocalShellTask` | Local shell task |

Task tools: `TaskCreateTool`, `TaskGetTool`, `TaskListTool`, `TaskUpdateTool`, `TaskStopTool`, `TaskOutputTool`.

## Key Source Files

| File | Responsibility |
|------|---------------|
| `src/tools/AgentTool/runAgent.ts` | Sub-agent execution loop |
| `src/utils/swarm/inProcessRunner.ts` | In-process teammate runner |
| `src/utils/swarm/backends/` | Execution backends (tmux/iTerm/in-process) |
| `src/utils/teammateMailbox.ts` | File mailbox communication |
| `src/tasks/` | Task framework |

## Next

Go to [11-plugin-skill.md](11-plugin-skill.md) to learn about the plugin and skill extension system.

## Hands-on Experiment

This chapter has a corresponding Python experiment:

> **[Lab 10 — Multi-Agent](experiments/10-multi-agent-lab.md)**
>
> Covers: nested agents, file mailbox, leader-worker pattern
>
> ```bash
> cd experiments && python -m exp_10_multi_agent.main --mock
> ```
