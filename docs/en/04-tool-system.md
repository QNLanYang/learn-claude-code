# Tool System: Definition, Registration, Dispatch, Execution

Tools are the agent's "hands" for interacting with the outside world. Claude Code's tool system covers the complete lifecycle from definition to permissions to execution.

## Tool Interface

All tools share a unified `Tool<Input, Output>` interface, defined in `src/Tool.ts`:

```typescript
type Tool<Input, Output, P = unknown> = {
    name: string
    inputSchema: z.ZodType<Input>          // Zod schema (runtime validation)
    inputJSONSchema?: ToolInputJSONSchema  // JSON Schema (for MCP tools)
    
    call(input, context, canUseTool, parentMessage, onProgress?): Promise<ToolResult<Output>>
    checkPermissions(input, context, workingDir): Promise<PermissionResult>
    validateInput?(input): ValidationResult
    mapToolResultToToolResultBlockParam(result, context): ToolResultBlockParam
    
    renderToolUseMessage?(input, output): React.ReactNode
    isConcurrencySafe?: boolean
    isReadOnly?: () => boolean
    isMcp?: boolean
    isEnabled?: (context) => boolean
    maxResultSizeChars?: number
}
```

## `buildTool()` Factory

Each tool is built via `buildTool()`, which merges `TOOL_DEFAULTS` for safe defaults:

```typescript
const TOOL_DEFAULTS = {
    checkPermissions: () => ({ result: 'allow' }),
    isConcurrencySafe: false,
    isReadOnly: () => false,
};

export function buildTool<I, O>(def: ToolDef<I, O>): Tool<I, O> {
    return { ...TOOL_DEFAULTS, ...def };
}
```

## Tool Registration

### `getAllBaseTools()`

Returns all built-in tools. Feature-gated tools use `bun:bundle`'s `feature()` for compile-time elimination:

```typescript
const SleepTool = feature('PROACTIVE') || feature('KAIROS')
    ? require('./tools/SleepTool/SleepTool.js').SleepTool
    : null;
```

### `getTools()` Filtering

Applies deny rules, checks `isEnabled()`, removes REPL-only tools in non-interactive mode, and applies "simple" mode restrictions.

### `assembleToolPool()` -- Merging MCP Tools

Built-in tools take priority on name conflicts. MCP tools are named `mcp__serverName__toolName`.

## Built-in Tool Catalog

| Category | Tools |
|----------|-------|
| File Operations | `FileReadTool`, `FileWriteTool`, `FileEditTool`, `NotebookEditTool`, `GlobTool`, `GrepTool` |
| Shell | `BashTool`, `PowerShellTool` |
| Network | `WebFetchTool`, `WebSearchTool` |
| Agent & Tasks | `AgentTool`, `TaskCreateTool`, `TaskGetTool`, `TaskListTool`, `TaskUpdateTool`, `TaskStopTool`, `TaskOutputTool`, `SendMessageTool`, `TeamCreateTool`, `TeamDeleteTool` |
| Other | `SkillTool`, `MCPTool`, `LSPTool`, `TodoWriteTool`, `EnterPlanModeTool`, `ExitPlanModeTool`, `ConfigTool`, `ToolSearchTool` |

## Tool Dispatch Pipeline

### `toolOrchestration.ts` -- Orchestration

`partitionToolCalls` divides tool calls into:
- **Concurrent-safe batches** (`isConcurrencySafe: true`): e.g., FileRead, Glob, Grep -- run in parallel
- **Serial batches** (`isConcurrencySafe: false`): e.g., FileWrite, BashTool -- run sequentially

### `toolExecution.ts` -- Execution

Single tool execution flow: Find tool -> Zod parse -> `validateInput` -> pre-hooks -> `canUseTool` permission check -> `tool.call()` -> map result -> process result (persist large outputs) -> post-hooks.

### `StreamingToolExecutor` -- Streaming Execution

When enabled, tools start executing as soon as their parameters are fully streamed, overlapping with the LLM response. Concurrent-safe tools launch immediately; others queue.

## Tool Result Handling

When results exceed `maxResultSizeChars`, `processToolResultBlock` persists them to disk under the session's `tool-results/` directory, replacing inline content with a preview + file path.

## Key Source Files

| File | Responsibility |
|------|---------------|
| `src/Tool.ts` | Tool interface, ToolUseContext, buildTool() |
| `src/tools.ts` | Tool registry: getAllBaseTools(), getTools(), assembleToolPool() |
| `src/services/tools/toolOrchestration.ts` | Tool orchestration: partitionToolCalls, runTools |
| `src/services/tools/toolExecution.ts` | Tool execution: runToolUse, checkPermissionsAndCallTool |
| `src/services/tools/StreamingToolExecutor.ts` | Streaming concurrent executor |
| `src/utils/toolResultStorage.ts` | Large result persistence and budget |

## Next

Go to [05-permission-security.md](05-permission-security.md) to learn about the permission system.

## Hands-on Experiment

This chapter has a corresponding Python experiment:

> **[Lab 04 — Tool System](experiments/04-tool-system-lab.md)**
>
> Covers: Tool protocol, Pydantic validation, registry, batch execution
>
> ```bash
> cd experiments && python -m exp_04_tool_system.main --mock
> ```
