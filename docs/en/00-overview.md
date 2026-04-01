# Claude Code Source Tutorial -- Project Overview & Quick Navigation

## Background

Claude Code is Anthropic's CLI tool that lets users interact with Claude from the terminal to perform software engineering tasks: editing files, running commands, searching codebases, and coordinating workflows.

This repository is a source snapshot that became publicly accessible on March 31, 2026, through a source map exposure in the npm distribution. It is maintained for educational and security research purposes only.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Runtime | [Bun](https://bun.sh) |
| Language | TypeScript (strict) |
| Terminal UI | React + [Ink](https://github.com/vadimdemedes/ink) (custom fork) |
| CLI Parsing | [Commander.js](https://github.com/tj/commander.js) (extra-typings) |
| Schema Validation | [Zod v4](https://zod.dev) |
| Code Search | [ripgrep](https://github.com/BurntSushi/ripgrep) |
| Protocols | [MCP SDK](https://modelcontextprotocol.io), LSP |
| API | [Anthropic SDK](https://docs.anthropic.com) |
| Telemetry | OpenTelemetry + gRPC |
| Feature Flags | GrowthBook + `bun:bundle` compile-time elimination |
| Auth | OAuth 2.0, JWT, macOS Keychain |

## Scale

- **~1,900 source files**, 512,000+ lines of code
- Single `src/` package structure, no `package.json` (this snapshot contains source only)
- 301 directories

## Quick Navigation

| I want to learn about... | Chapter | Key Files |
|--------------------------|---------|-----------|
| Overall architecture | [01-architecture](01-architecture.md) | `src/` directory structure |
| How it starts up | [02-startup-flow](02-startup-flow.md) | `entrypoints/cli.tsx`, `main.tsx` |
| How the agent loop works | [03-core-loop](03-core-loop.md) | `query.ts`, `QueryEngine.ts` |
| How tools are defined and run | [04-tool-system](04-tool-system.md) | `Tool.ts`, `tools.ts`, `services/tools/` |
| How permissions work | [05-permission-security](05-permission-security.md) | `utils/permissions/`, `types/permissions.ts` |
| How system prompt is assembled | [06-context-prompt](06-context-prompt.md) | `constants/prompts.ts`, `context.ts` |
| How memory works | [07-memory-system](07-memory-system.md) | `memdir/`, `services/SessionMemory/` |
| How the terminal UI renders | [08-terminal-ui](08-terminal-ui.md) | `ink/`, `screens/REPL.tsx`, `components/` |
| MCP integration | [09-mcp-integration](09-mcp-integration.md) | `services/mcp/`, `tools/MCPTool/` |
| Multi-agent coordination | [10-multi-agent](10-multi-agent.md) | `tools/AgentTool/`, `utils/swarm/` |
| Plugin and skill system | [11-plugin-skill](11-plugin-skill.md) | `plugins/`, `skills/`, `tools/SkillTool/` |
| API calls and streaming | [12-api-streaming](12-api-streaming.md) | `services/api/claude.ts`, `services/api/client.ts` |
| Configuration system | [13-config-settings](13-config-settings.md) | `utils/settings/` |
| Context compaction | [14-compact-context-mgmt](14-compact-context-mgmt.md) | `services/compact/` |
| Slash command system | [15-command-system](15-command-system.md) | `commands.ts`, `commands/` |
| Design patterns summary | [16-design-patterns](16-design-patterns.md) | Cross-file |

## Recommended Reading Paths

### Fast Track (~2 hours)

For readers who want to quickly grasp the core mechanisms:

```
00-overview -> 01-architecture -> 03-core-loop -> 04-tool-system -> 06-context-prompt
```

This covers the agent's "brain" -- how the loop runs, how tools execute, and how prompts are assembled.

### Full Track (~1-2 days)

For systematic, in-depth study, read all 17 documents in order:

```
00 -> 01 -> 02 -> 03 -> 04 -> 05 -> 06 -> 07 -> 08 -> 09 -> 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16
```

### By Interest

- **Agent core**: 03 -> 04 -> 05 -> 06
- **Extensibility**: 09 -> 10 -> 11 -> 15
- **Engineering practices**: 02 -> 12 -> 13 -> 14 -> 16
- **UI implementation**: 08

## Source Directory Overview

```
src/
├── main.tsx                 # Main entry (Commander CLI + Ink rendering)
├── query.ts                 # Core agent loop
├── QueryEngine.ts           # SDK/headless query engine wrapper
├── Tool.ts                  # Tool type definitions and context
├── tools.ts                 # Tool registry
├── commands.ts              # Command registry
├── context.ts               # Context collection (CLAUDE.md, git, etc.)
├── cost-tracker.ts          # Token cost tracking
│
├── entrypoints/             # Entry points (cli.tsx, init.ts, mcp.ts)
├── bootstrap/               # Global bootstrap state
├── screens/                 # Full-screen UIs (REPL, Doctor)
├── query/                   # Query pipeline helpers (deps, config, stopHooks)
│
├── tools/                   # ~40 tool implementations
├── commands/                # ~50 slash commands
├── components/              # ~140 Ink UI components
├── hooks/                   # React hooks
├── ink/                     # Ink rendering engine (custom fork)
├── services/                # External service integrations (API, MCP, OAuth, etc.)
├── utils/                   # Utilities (permissions, settings, model, etc.)
│
├── plugins/                 # Plugin system
├── skills/                  # Skill system
├── bridge/                  # IDE bridge
├── memdir/                  # Persistent memory directory
├── tasks/                   # Task management (sub-agents, teammates)
├── state/                   # State management
├── keybindings/             # Keybinding configuration
├── vim/                     # Vim mode
├── voice/                   # Voice input
├── remote/                  # Remote sessions
└── ...
```

## Hands-on Experiments

In addition to reading, we provide **15 Python experiments** that let you replicate Claude Code's core design patterns through code.

Experiments support three modes: `--mock` (offline), `--provider anthropic`, `--provider openai`.

### Experiment Directory

| Experiment | Chapter | Track |
|-----------|---------|-------|
| [exp_03 Core Agent Loop](experiments/03-core-agent-loop-lab.md) | 03 - Core Loop | **Core** |
| [exp_04 Tool System](experiments/04-tool-system-lab.md) | 04 - Tool System | **Core** |
| [exp_05 Permission Engine](experiments/05-permission-engine-lab.md) | 05 - Permissions | **Core** |
| [exp_06 Prompt Assembly](experiments/06-prompt-assembly-lab.md) | 06 - Context/Prompt | **Core** |
| [exp_07 Memory System](experiments/07-memory-system-lab.md) | 07 - Memory | **Core** |
| [exp_09 MCP Client](experiments/09-mcp-client-lab.md) | 09 - MCP | **Core** |
| [exp_10 Multi-Agent](experiments/10-multi-agent-lab.md) | 10 - Multi-Agent | **Core** |
| [exp_12 Streaming API](experiments/12-streaming-api-lab.md) | 12 - API/Streaming | **Core** |
| [exp_14 Context Compaction](experiments/14-context-compaction-lab.md) | 14 - Compaction | **Core** |
| [exp_02 Startup Flow](experiments/02-startup-flow-lab.md) | 02 - Startup Flow | Comprehensive |
| [exp_08 Terminal UI](experiments/08-terminal-ui-lab.md) | 08 - Terminal UI | Comprehensive |
| [exp_11 Plugin/Skill](experiments/11-plugin-skill-lab.md) | 11 - Plugin/Skill | Comprehensive |
| [exp_13 Config System](experiments/13-config-system-lab.md) | 13 - Config | Comprehensive |
| [exp_15 Command System](experiments/15-command-system-lab.md) | 15 - Commands | Comprehensive |
| [exp_16 Design Patterns](experiments/16-design-patterns-lab.md) | 16 - Patterns | Comprehensive |

See the [Experiment Guide](experiments/00-experiment-guide.md) for full setup instructions.

## Next

Go to [01-architecture.md](01-architecture.md) to understand the overall architecture.
