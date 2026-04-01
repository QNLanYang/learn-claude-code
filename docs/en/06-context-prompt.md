# Context Assembly & System Prompt Engineering

Each request sent to the LLM consists of three context parts. This assembly system determines what the LLM "knows" and "how it acts."

## Three-Part Context Structure

| Part | Source | Content |
|------|--------|---------|
| **System Prompt** | `getSystemPrompt()` | Role definition, tool instructions, behavior rules |
| **User Context** | `getUserContext()` | CLAUDE.md project rules, current date |
| **System Context** | `getSystemContext()` | Git status snapshot, auxiliary info |

These three parts are loaded in parallel by `fetchSystemPromptParts()` in `src/utils/queryContext.ts`.

## System Prompt Assembly

### Structure: Static Prefix + Dynamic Sections

```
+---------------------------------------------+
| Static Prefix (cacheable)                    |
|   - Role definition                          |
|   - Tool instructions                        |
|   - Behavior rules                           |
|   - Per-tool usage guides                    |
+------ SYSTEM_PROMPT_DYNAMIC_BOUNDARY --------+
| Dynamic Sections (may vary per request)      |
|   - Memory instructions                      |
|   - Environment info                         |
|   - Language preference                      |
|   - MCP server instructions                  |
|   - Output style settings                    |
+---------------------------------------------+
```

### Cache Boundary Design

`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` optimizes Anthropic API's **prompt caching**: static content before the boundary stays constant across turns (cacheable), while dynamic content after it can change freely without invalidating the cache.

### Dynamic Section System

```typescript
// src/constants/systemPromptSections.ts
systemPromptSection('memory_instructions', () => loadMemoryPrompt())
// Computed once per session, cached until /clear or compact

DANGEROUS_uncachedSystemPromptSection('env', () => getEnvInfo())
// Recomputed every time (name warns about performance impact)
```

## User Context

`getUserContext()` in `src/context.ts` returns a `{ [key: string]: string }` dictionary containing:
1. **CLAUDE.md chain**: project rules loaded from multiple locations (working dir, project root, parent dirs, `~/.claude/`)
2. **Current date**: injected for LLM time awareness

## System Context

`getSystemContext()` returns auxiliary keyed strings, notably git status snapshots when enabled.

## Context Injection into API Requests

```typescript
deps.callModel(messagesForAPI, {
    systemPrompt: prependUserContext(systemPrompt, userContext),
    ...appendSystemContext(systemContext),
});
```

## Key Source Files

| File | Responsibility |
|------|---------------|
| `src/constants/prompts.ts` | `getSystemPrompt()`: main system prompt assembly |
| `src/constants/systemPromptSections.ts` | Dynamic section system |
| `src/context.ts` | `getUserContext()` / `getSystemContext()` |
| `src/utils/queryContext.ts` | `fetchSystemPromptParts()`: parallel loading |

## Next

Go to [07-memory-system.md](07-memory-system.md) to learn how the memory system maintains knowledge across sessions.

## Hands-on Experiment

This chapter has a corresponding Python experiment:

> **[Lab 06 — Prompt Assembly](experiments/06-prompt-assembly-lab.md)**
>
> Covers: three-part assembly, cache boundary, CLAUDE.md chain
>
> ```bash
> cd experiments && python -m exp_06_prompt_assembly.main --mock
> ```
