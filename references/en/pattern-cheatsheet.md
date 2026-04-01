# Design Pattern Cheatsheet (English)

Python equivalents are illustrative. **Example source** points to Claude Code (TypeScript) or this repo’s `experiments/` where the idea shows up clearly.

| Pattern | One-liner | Python sketch | Example source |
|---------|-----------|---------------|----------------|
| Async iterator / generator | Stream events asynchronously; consumer pulls the next step. | `async def loop(): yield event` | `src/query.ts`; `experiments/exp_03_core_agent_loop/main.py` |
| Immutable snapshot | Replace state with a new object each turn; no in-place mutation. | `@dataclass(frozen=True)` + `replace()` | `experiments/exp_03_core_agent_loop/main.py` |
| Strategy | Pluggable algorithms (e.g., LLM providers). | ABC + multiple implementations | `experiments/shared/llm_client.py` |
| Registry | Map names to tools or handlers. | `dict[str, Callable]` | `src/utils/toolSearch.ts`; `experiments/exp_04_tool_system/main.py` |
| Chain of responsibility | Pass a request along handlers until one accepts (e.g., permissions). | List of `handle(req)` | `src/utils/permissions/`; `experiments/exp_05_permission_engine/main.py` |
| Facade | One entrypoint over a complex subsystem. | Wrapper class | `experiments/shared/llm_client.py`; `src/utils/model/model.ts` |
| Adapter | Translate an external protocol to an internal interface. | Thin wrapper over a SDK | `tools/MCPTool/MCPTool.ts`; `experiments/exp_09_mcp_client/main.py` |
| Observer / pub-sub | Subscribers react to streamed events. | `asyncio.Queue` + consumers | `src/utils/stream.ts`; `experiments/exp_12_streaming_api/main.py` |
| State | Explicit states and transitions for loop control. | `Enum` + branching | `experiments/exp_03_core_agent_loop/main.py` |
| Command | Encapsulate an action for queueing or retry. | `dataclass` + `run(ctx)` | `src/commands/`; `experiments/exp_15_command_system/main.py` |
| Template method | Fixed skeleton; subclasses override steps. | Base `run()` calling `_step_*` | `src/services/compact/compact.ts` |
| Leader–worker / queue | Coordinator enqueues; workers dequeue. | `asyncio.Queue` | `src/utils/swarm/`; `experiments/exp_10_multi_agent/main.py` |
