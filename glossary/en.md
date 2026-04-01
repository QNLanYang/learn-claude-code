# Glossary: Claude Code and Agent Systems (English)

Terms are grouped by theme. **Where It Appears** points to documentation chapters or typical source areas in this repository.

## Agent Core

| Term | Definition | Where It Appears |
|------|------------|------------------|
| Agent Loop | Closed cycle: call model → parse response → dispatch tools → append results → repeat until a terminal condition. | `docs/en/03-core-loop.md`; `src/query.ts` |
| tool_use | Structured tool invocation from the model (name + JSON arguments). | `docs/en/04-tool-system.md`; `src/query.ts` |
| tool_result | Observation written back into the conversation after a tool runs. | `docs/en/04-tool-system.md`; `src/Tool.ts` |
| async generator | `async` function that `yield`s events; consumers pull incrementally. | `docs/en/03-core-loop.md`; `src/query.ts` |
| state machine | Discrete states and transitions for the loop (continue / terminate / recover). | `docs/en/03-core-loop.md`; `experiments/exp_03_core_agent_loop/` |
| terminal condition | Exit reasons such as task done, max turns, user abort, fatal error. | `docs/en/03-core-loop.md` |
| turn | One iteration of model → tools → model. | `docs/en/03-core-loop.md` |
| stream event | Chunked events in streaming APIs (text deltas, tool blocks, usage). | `docs/en/12-api-streaming.md` |

## Tool System

| Term | Definition | Where It Appears |
|------|------------|------------------|
| Tool mode | How a tool participates in the dialog (e.g., parallelizable, needs approval). | `docs/en/04-tool-system.md` |
| validate input | Check arguments against JSON Schema or validators before execution. | `docs/en/04-tool-system.md`; `src/Tool.ts` |
| tool registry | Map from tool name to implementation and schema. | `docs/en/04-tool-system.md` |
| partition concurrent | Run independent tool calls in parallel; serialize dependent ones. | `docs/en/04-tool-system.md` |
| result truncation | Shorten or externalize oversized tool output to bound context size. | `docs/en/04-tool-system.md`; `src/utils/toolResultStorage.ts` |

## Context / Prompt

| Term | Definition | Where It Appears |
|------|------------|------------------|
| system prompt | Fixed behavioral instructions, usually separate from user messages. | `docs/en/06-context-prompt.md`; `src/utils/systemPrompt.ts` |
| user context | Workspace, open files, git state, etc., injected into the prompt. | `docs/en/06-context-prompt.md` |
| CLAUDE.md | Project-level instruction file loaded into context. | `docs/en/06-context-prompt.md` |
| cache boundary | Marks segments of the message list eligible for provider-side caching. | `docs/en/06-context-prompt.md`; `docs/en/12-api-streaming.md` |
| prompt assembly | Building the final API payload from rules, memory, tools, and history. | `docs/en/06-context-prompt.md` |

## Memory

| Term | Definition | Where It Appears |
|------|------------|------------------|
| long-term memory | Knowledge persisted across sessions (files, vector stores, summaries). | `docs/en/07-memory-system.md` |
| session memory | Short-lived state and notes within the current session. | `docs/en/07-memory-system.md` |
| memory recall | Retrieve relevant snippets for a query and inject into context. | `docs/en/07-memory-system.md` |
| TF-IDF | Term frequency–inverse document frequency; lightweight relevance ranking. | `docs/en/07-memory-system.md`; `experiments/exp_07_memory_system/` |

## MCP

| Term | Definition | Where It Appears |
|------|------------|------------------|
| MCP | Model Context Protocol: standard way to expose tools and resources. | `docs/en/09-mcp-integration.md` |
| JSON-RPC | JSON remote procedure call envelope (method / params / id) used by MCP. | `docs/en/09-mcp-integration.md` |
| transport | Channel carrying MCP messages (stdio, HTTP, WebSocket, etc.). | `docs/en/09-mcp-integration.md` |
| tool discovery | After connect, list remote tools/resources/prompts. | `docs/en/09-mcp-integration.md`; `experiments/exp_09_mcp_client/` |

## Multi-Agent

| Term | Definition | Where It Appears |
|------|------------|------------------|
| Swarm | Multi-teammate agent orchestration and related UI/backend. | `docs/en/10-multi-agent.md`; `src/utils/swarm/` |
| mailbox | Async message passing between processes or agents (e.g., files). | `docs/en/10-multi-agent.md`; `src/utils/teammateMailbox.ts` |
| nested agent | Parent launches a child via a tool; child has restricted tools and transcript. | `docs/en/10-multi-agent.md` |
| leader-worker | Leader decomposes work; workers execute in parallel and aggregate. | `docs/en/10-multi-agent.md` |
| sidechain transcript | Child conversation isolated from the main thread; may merge as summary. | `docs/en/10-multi-agent.md` |

## API / Streaming

| Term | Definition | Where It Appears |
|------|------------|------------------|
| SSE | Server-Sent Events: one-way event stream over HTTP. | `docs/en/12-api-streaming.md` |
| streaming | Consume model output incrementally to reduce time-to-first-token. | `docs/en/12-api-streaming.md` |
| content_block_delta | Streaming field/event type representing a delta on a content block. | `docs/en/12-api-streaming.md`; vendor SDKs |
| retry | Re-issue a request after a recoverable failure. | `docs/en/12-api-streaming.md` |
| backoff | Increase delay between retries to reduce load on the service. | `docs/en/12-api-streaming.md` |

## Config

| Term | Definition | Where It Appears |
|------|------------|------------------|
| compaction | Shorten context via summarization, dropping, or merging. | `docs/en/14-compact-context-mgmt.md` |
| microcompact | Small-granularity, cheaper compaction strategy. | `docs/en/14-compact-context-mgmt.md` |
| autocompact | Automatically compact when approaching budget limits. | `docs/en/14-compact-context-mgmt.md` |
| token budget | Upper bound on tokens for prompt, completion, and tool results. | `docs/en/14-compact-context-mgmt.md`; `src/utils/tokenBudget.ts` |
| managed / MDM | Organization-managed settings overlays. | `docs/en/13-config-settings.md`; `src/utils/settings/mdm/` |

## Permission / Security

| Term | Definition | Where It Appears |
|------|------------|------------------|
| permission mode | Tiered policy for tools and filesystem (e.g., ask, allow-list). | `docs/en/05-permission-security.md` |
| rule | Declarative match (path, command) → allow/deny decision. | `docs/en/05-permission-security.md` |
| sandbox | Restricted execution environment for subprocesses (fs, network). | `docs/en/05-permission-security.md` |
| bypass | Skip checks under explicit user grant or elevated mode (audit carefully). | `docs/en/05-permission-security.md` |

## UI

| Term | Definition | Where It Appears |
|------|------------|------------------|
| Ink | React-based library for terminal user interfaces. | `docs/en/08-terminal-ui.md`; `src/screens/REPL.tsx` |
| React | Declarative UI framework used with Ink in the terminal. | `docs/en/08-terminal-ui.md` |
| Vim mode | Vim-style keybindings in the prompt or REPL. | `docs/en/08-terminal-ui.md`; `src/vim/` |
| keybinding | Map keyboard shortcuts to commands or actions. | `docs/en/08-terminal-ui.md`; `docs/en/15-command-system.md` |
| REPL | Interactive read-eval-print loop main surface. | `docs/en/08-terminal-ui.md`; `src/screens/REPL.tsx` |

---

*Paths are relative to the repository root `claude-code-snapshot/`.*
