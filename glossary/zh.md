# Claude Code 与 Agent 系统术语表（中文）

下列术语按主题分组；**出现位置**指向本仓库文档章节或典型源码区域，便于对照阅读。

## Agent Core（Agent 核心）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| Agent 循环 | Agent Loop | 模型调用 → 解析响应 → 工具调度 → 写回消息 → 再调用的闭环，直到结束条件。 | `docs/zh/03-core-loop.md`；`src/query.ts` |
| 工具调用块 | tool_use | 模型输出的结构化工具调用（名称 + 参数 JSON）。 | `docs/zh/04-tool-system.md`；`src/query.ts` |
| 工具结果 | tool_result | 执行工具后写回对话的观测结果，供下一轮模型推理。 | `docs/zh/04-tool-system.md`；`src/Tool.ts` |
| 异步生成器 | async generator | 用 `async def` + `yield` 流式产出事件，消费者按需拉取。 | `docs/zh/03-core-loop.md`；`src/query.ts` |
| 状态机 | state machine | 用离散状态与转移描述循环（继续 / 终止 / 恢复），避免散乱布尔标志。 | `docs/zh/03-core-loop.md`；`experiments/exp_03_core_agent_loop/` |
| 终止条件 | terminal condition | 如任务完成、达最大轮次、用户中止、致命错误等退出循环的条件。 | `docs/zh/03-core-loop.md` |
| 回合 / 轮次 | turn | 一次「模型 → 工具 → 模型」迭代计为一轮。 | `docs/zh/03-core-loop.md` |
| 流式事件 | stream event | 增量文本、工具块、usage 等在流式 API 中的分片事件。 | `docs/zh/12-api-streaming.md` |

## Tool System（工具系统）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| 工具模式 | Tool mode | 定义工具在对话中的角色（如是否可并行、是否需用户确认）。 | `docs/zh/04-tool-system.md` |
| 输入校验 | validate input | 按 JSON Schema / 校验器在执行前检查参数，失败则短路。 | `docs/zh/04-tool-system.md`；`src/Tool.ts` |
| 工具注册表 | tool registry | 名称到工具实现与 schema 的映射，供模型与调度器查询。 | `docs/zh/04-tool-system.md` |
| 并行分区 | partition concurrent | 将无依赖的工具调用分批并行执行，有依赖的串行。 | `docs/zh/04-tool-system.md` |
| 工具结果裁剪 | result truncation | 超长输出按策略截断或外存，以控制上下文体积。 | `docs/zh/04-tool-system.md`；`src/utils/toolResultStorage.ts` |

## Context / Prompt（上下文与提示）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| 系统提示 | system prompt | 固定行为约束与能力说明，通常与用户消息分离注入。 | `docs/zh/06-context-prompt.md`；`src/utils/systemPrompt.ts` |
| 用户上下文 | user context | 工作区、打开文件、git 状态等注入到提示中的环境信息。 | `docs/zh/06-context-prompt.md` |
| CLAUDE.md | CLAUDE.md | 项目级长期说明文件，可被加载进系统或用户上下文。 | `docs/zh/06-context-prompt.md` |
| 缓存边界 | cache boundary | 在消息序列上标记可缓存片段的边界，配合供应商缓存降本。 | `docs/zh/06-context-prompt.md`；`docs/zh/12-api-streaming.md` |
| 提示组装 | prompt assembly | 将规则、记忆、工具定义、历史消息拼成最终 API 负载。 | `docs/zh/06-context-prompt.md` |

## Memory（记忆）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| 长期记忆 | long-term memory | 跨会话持久化的知识（如文件、向量库、摘要）。 | `docs/zh/07-memory-system.md` |
| 会话记忆 | session memory | 当前会话内累积的短期状态与笔记。 | `docs/zh/07-memory-system.md` |
| 记忆召回 | memory recall | 按查询从存储中检索相关片段注入上下文。 | `docs/zh/07-memory-system.md` |
| TF-IDF | TF-IDF | 词频–逆文档频率，用于轻量级关键词相关度排序。 | `docs/zh/07-memory-system.md`；`experiments/exp_07_memory_system/` |

## MCP

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| MCP | Model Context Protocol | 标准化外部工具与资源接入的协议与消息格式。 | `docs/zh/09-mcp-integration.md` |
| JSON-RPC | JSON-RPC | MCP 常用的 JSON 远程过程调用封装（method / params / id）。 | `docs/zh/09-mcp-integration.md` |
| 传输层 | transport | stdio、HTTP、WebSocket 等承载 MCP 消息的通道。 | `docs/zh/09-mcp-integration.md` |
| 工具发现 | tool discovery | 连接后列举远端可用 tools/resources/prompts。 | `docs/zh/09-mcp-integration.md`；`experiments/exp_09_mcp_client/` |

## Multi-Agent（多 Agent）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| Swarm | Swarm | 多协作者 Agent 的编排与 UI/后端抽象（如队友模式）。 | `docs/zh/10-multi-agent.md`；`src/utils/swarm/` |
| 邮箱 | mailbox | 进程或 Agent 间通过文件/通道异步传递消息的机制。 | `docs/zh/10-multi-agent.md`；`src/utils/teammateMailbox.ts` |
| 嵌套 Agent | nested agent | 父 Agent 通过工具启动子 Agent，子会话有独立工具与白名单。 | `docs/zh/10-multi-agent.md` |
| Leader-Worker | leader-worker | 领导者分解任务，工作者并行执行并汇总。 | `docs/zh/10-multi-agent.md` |
| 侧链 transcript | sidechain transcript | 子 Agent 对话与主会话隔离的记录，可按需合并摘要。 | `docs/zh/10-multi-agent.md` |

## API / Streaming（接口与流式）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| SSE | Server-Sent Events | 服务端单向推送事件流，常用于 HTTP 上的流式响应。 | `docs/zh/12-api-streaming.md` |
| 流式响应 | streaming | 边生成边消费模型输出，降低首字延迟。 | `docs/zh/12-api-streaming.md` |
| content_block_delta | content_block_delta | 流式 API 中表示内容块增量的字段/事件类型。 | `docs/zh/12-api-streaming.md`；供应商 SDK |
| 重试 | retry | 对可恢复错误按策略再次请求。 | `docs/zh/12-api-streaming.md` |
| 退避 | backoff | 重试间隔指数或线性增大，减轻服务端压力。 | `docs/zh/12-api-streaming.md` |

## Config（配置）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| Compaction | compaction | 将过长上下文压缩为更短表示（摘要/丢弃/合并）。 | `docs/zh/14-compact-context-mgmt.md` |
| Microcompact | microcompact | 小粒度、低成本的局部压缩策略。 | `docs/zh/14-compact-context-mgmt.md` |
| Autocompact | autocompact | 在接近预算时自动触发压缩。 | `docs/zh/14-compact-context-mgmt.md` |
| Token 预算 | token budget | 为提示、输出、工具结果预留的最大 token 上限。 | `docs/zh/14-compact-context-mgmt.md`；`src/utils/tokenBudget.ts` |
| 托管配置 | managed / MDM | 组织策略下发的只读或受限配置。 | `docs/zh/13-config-settings.md`；`src/utils/settings/mdm/` |

## Permission / Security（权限与安全）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| 权限模式 | permission mode | 如默认允许、需确认、只读等，对工具与文件操作分级。 | `docs/zh/05-permission-security.md` |
| 规则 | rule | 声明式或配置型策略，匹配路径/命令后决定允许与否。 | `docs/zh/05-permission-security.md` |
| 沙箱 | sandbox | 限制子进程文件系统、网络等执行环境。 | `docs/zh/05-permission-security.md` |
| 绕过 | bypass | 在显式用户授权或特权模式下跳过某些检查（需谨慎审计）。 | `docs/zh/05-permission-security.md` |

## UI（界面）

| 术语 | 英文 | 定义 | 出现位置 |
|------|------|------|----------|
| Ink | Ink | 基于 React 的终端 UI 库，用于 TUI 组件树。 | `docs/zh/08-terminal-ui.md`；`src/screens/REPL.tsx` |
| React | React | 声明式 UI 框架；在终端中与 Ink 结合。 | `docs/zh/08-terminal-ui.md` |
| Vim 模式 | Vim mode | 在输入框或 REPL 中模拟 Vim 编辑键位。 | `docs/zh/08-terminal-ui.md`；`src/vim/` |
| 快捷键绑定 | keybinding | 键盘快捷键到命令或动作的映射。 | `docs/zh/08-terminal-ui.md`；`docs/zh/15-command-system.md` |
| REPL | REPL | 读–求值–输出循环式交互主界面。 | `docs/zh/08-terminal-ui.md`；`src/screens/REPL.tsx` |

---

*文档路径相对于仓库根目录 `claude-code-snapshot/`。*
