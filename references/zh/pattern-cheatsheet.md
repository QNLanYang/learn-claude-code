# 设计模式速查（中文）

Python 等价物为示意写法；**示例源文件**为 Claude Code（TypeScript）或本仓库 `experiments/` 中体现该思想的文件。

| 模式 | 一句话 | Python 等价示意 | 示例源文件 |
|------|--------|-----------------|------------|
| Async Iterator / Generator | 异步流式产出事件，由消费者驱动下一步。 | `async def loop(): yield event` | `src/query.ts`；`experiments/exp_03_core_agent_loop/main.py` |
| Immutable Snapshot | 每轮用新对象替换状态，禁止原地修改。 | `@dataclass(frozen=True)` + `replace()` | `experiments/exp_03_core_agent_loop/main.py` |
| Strategy | 可插拔算法（如不同 LLM 提供商）。 | 抽象基类 + 多实现 | `experiments/shared/llm_client.py` |
| Registry | 名称到工具/处理器的映射表。 | `dict[str, Callable]` | `src/utils/toolSearch.ts`；`experiments/exp_04_tool_system/main.py` |
| Chain of Responsibility | 请求沿责任链传递直到被处理（如权限检查）。 | 链表或列表依次 `handle(req)` | `src/utils/permissions/`；`experiments/exp_05_permission_engine/main.py` |
| Facade | 对复杂子系统提供单一入口。 | 包装类封装多步调用 | `experiments/shared/llm_client.py`；`src/utils/model/model.ts` |
| Adapter | 将外部协议转为内部统一接口。 | 包装第三方 SDK | `tools/MCPTool/MCPTool.ts`；`experiments/exp_09_mcp_client/main.py` |
| Observer / Pub-Sub | 流式事件订阅，UI 或日志监听。 | `asyncio.Queue` + 消费者 | `src/utils/stream.ts`；`experiments/exp_12_streaming_api/main.py` |
| State | 显式状态与转移，驱动循环终止/继续。 | `Enum` + `match` / `if` | `experiments/exp_03_core_agent_loop/main.py` |
| Command | 将操作封装为可排队、可重试的对象。 | `dataclass` + `run(ctx)` | `src/commands/`；`experiments/exp_15_command_system/main.py` |
| Template Method | 固定骨架，子步骤可覆盖。 | 基类定义 `run()` 调用若干 `_step_*` | `src/services/compact/compact.ts` |
| Leader–Worker / Queue | 协调者分派任务，工作者从队列取任务。 | `asyncio.Queue` | `src/utils/swarm/`；`experiments/exp_10_multi_agent/main.py` |
