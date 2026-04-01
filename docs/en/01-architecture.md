# Architecture & Module Map

## Layered Architecture

Claude Code uses a clear layered architecture, forming a complete data pipeline from user input to LLM interaction:

```mermaid
graph TB
    subgraph entryLayer [Entry Layer]
        CLI["entrypoints/cli.tsx"]
        MainTSX["main.tsx"]
        Boot["bootstrap/state.ts"]
    end

    subgraph coreLayer [Core Layer]
        Query["query.ts (Agent Loop)"]
        QE["QueryEngine.ts (SDK Wrapper)"]
        ToolDef["Tool.ts (Tool Types)"]
        ToolReg["tools.ts (Tool Registry)"]
        CmdReg["commands.ts (Command Registry)"]
    end

    subgraph serviceLayer [Service Layer]
        API["services/api/ (Anthropic API)"]
        MCP["services/mcp/ (MCP Client)"]
        Compact["services/compact/ (Context Compaction)"]
        Analytics["services/analytics/ (Telemetry)"]
        OAuth["services/oauth/ (Auth)"]
        ToolSvc["services/tools/ (Tool Dispatch)"]
    end

    subgraph uiLayer [UI Layer]
        InkCore["ink/ (Rendering Engine)"]
        Screens["screens/REPL.tsx"]
        Components["components/ (UI Components)"]
        Hooks["hooks/ (React Hooks)"]
    end

    subgraph infraLayer [Infrastructure Layer]
        Perms["utils/permissions/"]
        Settings["utils/settings/"]
        Model["utils/model/"]
        Swarm["utils/swarm/"]
        Shell["utils/bash/"]
    end

    subgraph extLayer [Extension Layer]
        Plugins["plugins/"]
        Skills["skills/"]
        Bridge["bridge/"]
        Tasks["tasks/"]
    end

    CLI --> MainTSX
    MainTSX --> Boot
    MainTSX --> Screens
    MainTSX --> QE
    Screens --> Query
    QE --> Query
    Query --> API
    Query --> ToolSvc
    ToolSvc --> ToolDef
    ToolSvc --> ToolReg
    ToolReg --> extLayer
    API --> Model
    Query --> Compact
    Screens --> Components
    Screens --> Hooks
    Components --> InkCore
    ToolSvc --> Perms
    MainTSX --> Settings
```

## `src/` Top-Level Directory Classification

### Entry Layer

| Directory/File | Files | Responsibility |
|----------------|-------|---------------|
| `entrypoints/` | 8 | Process entry: `cli.tsx` (CLI bootstrap), `init.ts` (one-time init), `mcp.ts` (MCP server mode), SDK types |
| `main.tsx` | 1 | Commander CLI setup, GrowthBook init, tool registration, REPL launch |
| `bootstrap/` | 1 | `state.ts`: global bootstrap state (telemetry, channels, settings cache) |

### Core Layer

| File | Responsibility |
|------|---------------|
| `query.ts` | **Core agent loop**: `query()` / `queryLoop()` state machine driving LLM calls -> tool execution -> result injection |
| `QueryEngine.ts` | SDK / headless mode wrapper managing per-session message lists, abort, file cache |
| `Tool.ts` | Tool interface definitions: `Tool<Input, Output>`, `ToolUseContext`, `ToolPermissionContext`, `buildTool()` |
| `tools.ts` | Tool registry: `getAllBaseTools()` returns all built-in tools, `getTools()` filters by permissions |
| `commands.ts` | Command registry: merges bundled/plugin/skill/built-in commands, sorted by priority |

### Service Layer (`services/`, 130 files)

| Subdirectory | Responsibility |
|--------------|---------------|
| `api/` | Anthropic API client construction, streaming calls, retries, file API |
| `mcp/` | MCP client connection management, tool discovery, config merging |
| `compact/` | Context compaction (full/micro/auto) |
| `analytics/` | GrowthBook feature flags, analytics events |
| `oauth/` | OAuth 2.0 authentication flow |
| `tools/` | Tool orchestration (`toolOrchestration.ts`), execution (`toolExecution.ts`), streaming executor |
| `lsp/` | Language Server Protocol integration |
| `policyLimits/` | Organization policy limits |
| `remoteManagedSettings/` | Remote managed settings (enterprise) |
| `SessionMemory/` | Session memory extraction |
| `teamMemorySync/` | Team memory synchronization |

### UI Layer

| Directory | Files | Responsibility |
|-----------|-------|---------------|
| `ink/` | 96 | Custom Ink rendering engine: React reconciler + Yoga layout + terminal cell buffer |
| `screens/` | 3 | Full-screen UIs: `REPL.tsx` (main interaction), `Doctor.tsx` (diagnostics), `ResumeConversation.tsx` |
| `components/` | 389 | Ink UI components: message display, permission dialogs, input, design system, task panels, etc. |
| `hooks/` | 104 | React hooks: tool permissions, notifications, settings changes, etc. |
| `keybindings/` | 14 | Keybinding definitions and handling (chord support) |
| `vim/` | 5 | Vim mode implementation (motions, operators, text objects) |

### Infrastructure Layer (`utils/`, 564 files)

| Subdirectory | Responsibility |
|--------------|---------------|
| `permissions/` | Core permission decision logic, rule parsing, setup |
| `settings/` | Layered config loading and merging (user/project/local/flag/policy) |
| `model/` | Model selection, provider branching, capability checks |
| `swarm/` | Multi-agent coordination: in-process teammates, tmux/iTerm backends |
| `bash/` | Bash command parsing and security classification |
| `plugins/` | Plugin loader |
| `hooks/` | Lifecycle hooks |
| `telemetry/` | Telemetry reporting |

### Extension Layer

| Directory | Files | Responsibility |
|-----------|-------|---------------|
| `plugins/` | 2 | Plugin system (built-in plugin registration) |
| `skills/` | 20 | Skill system (bundled skills, disk skill loading) |
| `bridge/` | 31 | IDE bridge (VS Code, JetBrains) |
| `tasks/` | 12 | Task framework: local/remote agent tasks, teammate tasks |

## Core Data Flow

A complete user interaction flows through:

```mermaid
sequenceDiagram
    participant User
    participant REPL as REPL.tsx
    participant PUI as processUserInput
    participant QL as query() Loop
    participant API as Anthropic API
    participant TE as Tool Execution Engine
    participant Tool as Concrete Tool

    User->>REPL: Input text / slash command
    REPL->>PUI: handlePromptSubmit
    PUI->>PUI: Parse slash commands, attachments
    PUI->>QL: messages + systemPrompt + context
    
    loop Agent Loop (each iteration)
        QL->>QL: Context preparation (token budget / compact)
        QL->>API: callModel (streaming)
        API-->>QL: AssistantMessage (with tool_use blocks)
        QL-->>REPL: Stream events -> UI rendering
        
        alt Contains tool_use
            QL->>TE: runTools / StreamingToolExecutor
            TE->>TE: Permission check (canUseTool)
            TE->>Tool: tool.call(input, context)
            Tool-->>TE: ToolResult
            TE-->>QL: tool_result messages
            Note over QL: needsFollowUp = true, continue loop
        else No tool_use
            Note over QL: Loop terminates, return result
        end
    end
    
    QL-->>REPL: Final messages
    REPL-->>User: Render response
```

## Next

Go to [02-startup-flow.md](02-startup-flow.md) to understand the complete startup process from command line to interactive loop.
