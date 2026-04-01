# Key Design Patterns & Engineering Practices

This chapter summarizes the recurring design patterns and engineering practices found throughout the Claude Code source, helping you understand its design philosophy.

## 1. Async Generator Pipeline

The most fundamental architectural pattern -- nearly all data flows use async generators.

```typescript
// Producer
async function* query(params): AsyncGenerator<StreamEvent | Message, Terminal> {
    for await (const event of callModel(...)) {
        yield event;
    }
    yield* runTools(...);
}

// Consumer
for await (const event of query(params)) {
    onQueryEvent(event);
}
```

Used in: `query()`, `queryModelWithStreaming()`, `runAgent()`, `runToolUse()`, `runTools()`.

**Why**: Incremental delivery (stream to UI immediately), backpressure control (consumer controls pace), composability (`yield*` nests generators seamlessly), cancellation propagation (`.return()` propagates through the chain).

## 2. Explicit State Machine

`queryLoop` is not a simple while-true but a state machine with explicit state and transitions.

```typescript
type State = {
    messages: Message[]
    turnCount: number
    transition: Continue | undefined  // why previous iteration continued
    // ...
}

// Each continue site replaces entire state
state = { ...state, messages: newMessages, transition: { reason: 'tool_use' } };
continue;
```

**Benefits**: State changes are centrally visible, tests can assert transition reasons, no implicit state leakage.

## 3. Dependency Injection

Core external dependencies are injected via `QueryDeps` for testability:

```typescript
type QueryDeps = {
    callModel: typeof queryModelWithStreaming
    microcompact: typeof microcompactMessages
    autocompact: typeof compactConversation
    uuid: () => string
}
```

Scoped intentionally -- only for `query` loop core dependencies, not a global DI container.

## 4. Factory + Defaults

Tools are built via `buildTool()` with safe defaults:

```typescript
const TOOL_DEFAULTS = {
    checkPermissions: () => ({ result: 'allow' }),
    isConcurrencySafe: false,
    isReadOnly: () => false,
};

export function buildTool(def) { return { ...TOOL_DEFAULTS, ...def }; }
```

New tools only define necessary fields; defaults are safe (not concurrent, not read-only).

## 5. Layered Config Merge

Multi-source configs merge by priority, supporting user to enterprise override:

```
userSettings < projectSettings < localSettings < flagSettings < policySettings
```

Security-related settings (permission rules) use merge semantics rather than override.

## 6. React in Terminal

Declarative UI paradigm for managing complex terminal UI state:

```
React Component Tree -> react-reconciler -> Yoga Layout (Flexbox)
  -> Cell Buffer (character grid) -> TTY Diff (delta output to terminal)
```

Benefits: declarative UI, hook ecosystem, component reuse, familiar programming model.

## 7. Tool Batch Partitioning

Tool execution balances concurrency and safety via partitioning:

- **Concurrent-safe batch**: `isConcurrencySafe: true` tools (FileRead, Glob, Grep) run in parallel
- **Serial batch**: `isConcurrencySafe: false` tools (FileWrite, Bash) run sequentially

`StreamingToolExecutor` overlaps tool execution with LLM streaming.

## 8. File-Based Mailbox

Swarm teammates use filesystem JSON inboxes for inter-process communication:

```
.claude/teams/<session>/inboxes/<agent-id>.json
```

**Why files over IPC**: Cross-process (tmux/iTerm teammates are separate processes), persistent (survive crashes), simple (no socket connections), observable (can inspect files for debugging).

## 9. Compile-Time Dead Code Elimination

`bun:bundle`'s `feature()` completely removes disabled code paths at compile time:

```typescript
const SleepTool = feature('PROACTIVE')
    ? require('./tools/SleepTool/SleepTool.js').SleepTool
    : null;
```

Notable flags: `PROACTIVE`, `KAIROS`, `BRIDGE_MODE`, `DAEMON`, `VOICE_MODE`, `AGENT_TRIGGERS`, `REACTIVE_COMPACT`, `MCP_SKILLS`.

## 10. Parallel Prefetch

Startup leverages ES module side effects to run expensive I/O in parallel with module loading:

```typescript
profileCheckpoint('main_tsx_entry');
startMdmRawRead();        // Start MDM subprocess
startKeychainPrefetch();   // Start Keychain reads
// Subsequent ~135ms of imports run in parallel with above I/O
```

Memory prefetch uses `using` syntax for guaranteed cleanup on all exit paths.

## 11. Prompt Cache Boundary

`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` in the system prompt optimizes Anthropic API's prompt caching: static content before the boundary is cacheable across turns, while dynamic content after it changes freely.

## 12. Session-Scoped Section Cache

Dynamic system prompt sections are computed once and cached per session:

```typescript
systemPromptSection('memory_instructions', () => loadMemoryPrompt())
// Computed once, cached until /clear or compact

DANGEROUS_uncachedSystemPromptSection('env', () => getEnvInfo())
// Always recomputed (name warns about performance)
```

## Design Philosophy Summary

| Principle | Manifestation |
|-----------|--------------|
| **Incremental delivery** | Full-chain async generators, UI responds immediately |
| **Safe defaults** | Tools default to non-concurrent, permissions default to ask |
| **Testability** | QueryDeps DI, VCR recording/playback |
| **Performance first** | Parallel prefetch, compile-time elimination, prompt cache |
| **Clear layering** | Entry -> Core -> Service -> UI -> Infrastructure |
| **Extension friendly** | Plugins, skills, MCP, custom agent types |
| **Progressive complexity** | Simple cases are simple (single tool), complex cases composable (swarm) |

## Recommended Code Reading Paths

To deeply understand a specific pattern:

1. **Async Generator Pipeline**: Start from `queryLoop` in `query.ts`, follow `yield*` to `callModel` and `runTools`
2. **State Machine**: Read the `State` type in `query.ts`, then search all `continue` sites
3. **Tool System**: Start from `Tool.ts` interface, then `checkPermissionsAndCallTool` in `toolExecution.ts`
4. **React in Terminal**: Start from the `Ink` class in `ink/ink.tsx`
5. **Config Merge**: Start from `SETTING_SOURCES` in `settings/constants.ts`, then `settings.ts`

---

Congratulations on completing the full Claude Code source tutorial! You should now have a systematic understanding of the architecture, core loop, tool system, security model, and engineering practices.

## Hands-on Experiment

This chapter has a corresponding Python experiment:

> **[Lab 16 — Design Patterns](experiments/16-design-patterns-lab.md)**
>
> Covers: 6 patterns cookbook (async generators, immutable state, DI, factory, config merge, batch partitioning)
>
> ```bash
> cd experiments && python -m exp_16_design_patterns.main --mock
> ```
