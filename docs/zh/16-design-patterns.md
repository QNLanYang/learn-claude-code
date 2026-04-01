# 关键设计模式与工程实践总结

本章总结 Claude Code 源码中反复出现的设计模式和工程实践，帮助理解代码库的设计哲学。

## 1. 异步生成器管道（Async Generator Pipeline）

这是 Claude Code 最核心的架构模式——几乎所有数据流都通过 async generator 串联。

### 模式描述

```typescript
// 生产者
async function* query(params): AsyncGenerator<StreamEvent | Message, Terminal> {
    // yield 流式事件和消息
    for await (const event of callModel(...)) {
        yield event;
    }
    yield* runTools(...);
}

// 消费者
for await (const event of query(params)) {
    onQueryEvent(event);  // 渲染到 UI
}
```

### 应用场景

| 位置 | 生成器 | yield 内容 |
|------|--------|-----------|
| `query.ts` | `query()` / `queryLoop()` | StreamEvent, Message, ToolUseSummary |
| `services/api/claude.ts` | `queryModelWithStreaming()` | AssistantMessage, StreamEvent |
| `tools/AgentTool/runAgent.ts` | `runAgent()` | 子 Agent 的事件和消息 |
| `services/tools/toolExecution.ts` | `runToolUse()` | 工具执行结果 |
| `services/tools/toolOrchestration.ts` | `runTools()` | 批量工具结果 |

### 为什么使用 async generator

- **增量交付**：流式输出可以逐步渲染到 UI
- **背压控制**：消费者控制处理节奏
- **组合性**：`yield*` 可以无缝嵌套生成器
- **取消传播**：`.return()` 在整个生成器链中传播

## 2. 显式状态机（Explicit State Machine）

`queryLoop` 的循环不是简单的 while-true，而是一个有明确状态和转移的状态机。

### 模式描述

```typescript
type State = {
    messages: Message[]
    turnCount: number
    transition: Continue | undefined  // 上一轮的继续原因
    // ...其他状态字段
}

// 每个 continue 站点整体替换状态
state = {
    ...state,
    messages: newMessages,
    turnCount: state.turnCount + 1,
    transition: { reason: 'tool_use' },
};
continue;
```

### 关键特征

- **State 是一个对象**，不是散落的变量
- **transition 字段**记录状态转移的原因，便于调试和测试断言
- **Terminal 类型**定义所有终止原因，编译器强制穷举
- 每轮迭代开始时**解构**，保持代码整洁

### 好处

- 状态变更集中可见
- 测试可以断言转移原因而非消息内容
- 避免了隐式的状态泄漏

## 3. 依赖注入（Dependency Injection）

外部依赖通过接口注入，使核心逻辑可测试。

### 模式描述

```typescript
// src/query/deps.ts
type QueryDeps = {
    callModel: typeof queryModelWithStreaming
    microcompact: typeof microcompactMessages
    autocompact: typeof compactConversation
    uuid: () => string
}

// 生产环境
const productionDeps = (): QueryDeps => ({
    callModel: queryModelWithStreaming,
    microcompact: microcompactMessages,
    autocompact: compactConversation,
    uuid: crypto.randomUUID,
});

// 测试环境
const testDeps: QueryDeps = {
    callModel: mockCallModel,
    microcompact: (msgs) => msgs,  // no-op
    autocompact: (msgs) => msgs,   // no-op
    uuid: () => 'test-uuid',
};
```

### 应用范围

此模式仅在 `query` 循环的核心依赖上使用，保持简洁。不是全局 DI 容器。

## 4. 工厂 + 默认值（Factory + Defaults）

工具通过工厂函数构建，提供安全的默认值。

### 模式描述

```typescript
// src/Tool.ts
const TOOL_DEFAULTS = {
    checkPermissions: () => ({ result: 'allow' }),
    isConcurrencySafe: false,
    isReadOnly: () => false,
    validateInput: () => ({ result: true }),
    // ...
};

export function buildTool<I, O>(def: ToolDef<I, O>): Tool<I, O> {
    return { ...TOOL_DEFAULTS, ...def };
}
```

### 好处

- 新工具只需定义必要字段
- 默认行为安全（如默认不可并发、默认非只读）
- 类型推断仍然完整

## 5. 分层配置合并（Layered Config Merge）

多来源配置按优先级合并，支持从用户级到企业级的覆盖。

### 模式描述

```typescript
const SETTING_SOURCES = [
    'userSettings',     // 最低优先级
    'projectSettings',
    'localSettings',
    'flagSettings',
    'policySettings',   // 最高优先级（企业强制）
];

function mergeSettings(sources: SettingsBySource): FinalSettings {
    // 后面的来源覆盖前面的
    // 但权限规则是合并而非覆盖
}
```

### 设计考量

- 用户设置可以被项目设置覆盖（团队统一）
- 项目设置可以被企业策略覆盖（合规要求）
- 本地设置（git-ignored）允许个人偏好不影响团队
- 安全相关设置（如权限规则）使用合并语义

## 6. React 在终端（React in Terminal）

使用 React 的声明式范式管理复杂的终端 UI 状态。

### 模式描述

```
React Component Tree
    └─ react-reconciler（自定义协调器）
        └─ Yoga Layout（Flexbox 计算）
            └─ Cell Buffer（字符网格）
                └─ TTY Diff（差量输出到终端）
```

### 与 Web React 的区别

| 方面 | Web React | 终端 React (Ink) |
|------|-----------|------------------|
| 渲染目标 | DOM | 字符网格 |
| 布局引擎 | CSS | Yoga (Flexbox) |
| 更新机制 | DOM diff | Cell buffer diff |
| 事件系统 | DOM events | stdin 字节解析 |
| 样式 | CSS | ANSI 转义序列 |

### 好处

- 声明式 UI 管理复杂的对话界面
- Hook 生态系统（useState, useEffect, ...）
- 组件复用和组合
- 熟悉的编程模型

## 7. 并发控制：工具批次分区

工具执行通过分区策略平衡并发和安全。

### 模式描述

```typescript
// src/services/tools/toolOrchestration.ts
function partitionToolCalls(toolUses: ToolUseBlock[]): Batch[] {
    // 1. 扫描工具列表，按 isConcurrencySafe 分类
    // 2. 连续的并发安全工具合并为一个并发批次
    // 3. 非并发安全工具各自成为一个串行批次
    // 4. 保持原始顺序
    
    // 例如：[Read, Read, Grep, Write, Read]
    // → [Batch(Read,Read,Grep, concurrent), Batch(Write, serial), Batch(Read, concurrent)]
}
```

### 并发限制

```typescript
// CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY 环境变量控制
// 并发批次中的工具使用 Promise.all 并行执行
// 但受最大并发数限制
```

### 流式执行器

```typescript
// StreamingToolExecutor 在流式传输过程中就开始执行工具
// 并发安全的工具一完成参数解析就立即启动
// 非并发安全的工具排队等待
```

## 8. 文件级邮箱（File-Based Mailbox）

Swarm 团队使用文件系统实现进程间通信。

### 模式描述

```typescript
// src/utils/teammateMailbox.ts
// 每个 agent 有一个 inbox 文件
// .claude/teams/<session>/inboxes/<agent-id>.json

function sendMessage(targetId, msg) {
    // 追加到目标 inbox 文件
    // 文件锁保证原子性
}

function readMessages(myId) {
    // 读取自己的 inbox 文件
    // 读取后清空（或标记已读）
}
```

### 为什么用文件而非 IPC

- **跨进程**：tmux/iTerm 后端的 teammate 是独立进程
- **持久化**：crash 后消息不丢失
- **简单**：无需维护 socket 连接
- **可观察**：可以直接查看文件内容调试

## 9. 编译期死代码消除

使用 `bun:bundle` 的 `feature()` 在编译时完全移除未启用的代码路径。

### 模式描述

```typescript
import { feature } from 'bun:bundle';

// 编译期评估：如果 VOICE_MODE 未启用，整个 require 被消除
const voiceCommand = feature('VOICE_MODE')
    ? require('./commands/voice/index.js').default
    : null;

// 条件 import 也被消除
if (feature('DAEMON') && args[0] === '--daemon-worker') {
    const { run } = await import('./daemon/workerRegistry.js');
    // ...
}
```

### 常见 Feature Flags

| Flag | 功能 |
|------|------|
| `PROACTIVE` | 主动模式 |
| `KAIROS` | 助手模式 |
| `BRIDGE_MODE` | IDE 桥接 |
| `DAEMON` | 守护进程 |
| `VOICE_MODE` | 语音输入 |
| `AGENT_TRIGGERS` | Agent 触发器 |
| `MONITOR_TOOL` | 监控工具 |
| `REACTIVE_COMPACT` | 反应式压缩 |
| `HISTORY_SNIP` | 历史剪裁 |
| `MCP_SKILLS` | MCP 技能 |

## 10. 并行预取（Parallel Prefetch）

启动时利用 ES 模块副作用并行启动耗时操作。

### 模式描述

```typescript
// main.tsx 的前几行
profileCheckpoint('main_tsx_entry');  // 标记入口时间

startMdmRawRead();        // 启动 MDM 子进程（plutil/reg query）
startKeychainPrefetch();   // 启动 macOS Keychain 读取（两个并发）

// 后续 ~135ms 的 import 与上述 I/O 并行执行
import { Command } from '@commander-js/extra-typings';
import chalk from 'chalk';
// ...
```

### 记忆预取

```typescript
// src/query.ts
using pendingMemoryPrefetch = startRelevantMemoryPrefetch(messages, context);
// 使用 `using` 确保在所有退出路径上正确清理
// 预取结果在需要时 poll（从不阻塞主循环）
```

## 11. Prompt Cache 边界优化

System Prompt 中的缓存边界标记优化了 Anthropic API 的 prompt caching。

### 模式描述

```typescript
// src/constants/prompts.ts
const systemPrompt = [
    ...staticPrefix,         // 不变的部分（可缓存）
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,  // 缓存边界标记
    ...dynamicSections,      // 可能变化的部分（不缓存）
];
```

### 好处

- 静态前缀在多轮对话中只计算一次
- 减少 API 成本（cached tokens 更便宜）
- 减少延迟（缓存命中时更快）

## 12. 会话级分节缓存

System Prompt 的动态分节使用会话级缓存，避免重复计算。

### 模式描述

```typescript
// src/constants/systemPromptSections.ts
export function systemPromptSection(key, compute) {
    // 首次调用：执行 compute()，缓存结果
    // 后续调用：返回缓存
    // /clear 或 compact 时：clearSystemPromptSections() 清除缓存
}

// 不安全分节（每次重新计算）
export function DANGEROUS_uncachedSystemPromptSection(key, compute) {
    // 总是重新计算，不缓存
    // 命名带 DANGEROUS 前缀提醒开发者注意性能影响
}
```

## 设计哲学总结

| 原则 | 体现 |
|------|------|
| **增量交付** | 全链路 async generator，UI 立即响应 |
| **安全默认** | 工具默认不可并发、权限默认需审批 |
| **可测试性** | QueryDeps 依赖注入、VCR 录放 |
| **性能优先** | 并行预取、编译期消除、prompt cache |
| **层次分明** | 入口 → 核心 → 服务 → UI → 基础设施 |
| **扩展友好** | 插件、技能、MCP、自定义 Agent 类型 |
| **渐进复杂** | 简单场景简单（单工具），复杂场景可组合（swarm） |

## 推荐的代码阅读路径

如果你想深入理解某个设计模式的实现：

1. **Async Generator Pipeline**: 从 `query.ts` 的 `queryLoop` 开始，跟踪 `yield*` 到 `callModel` 和 `runTools`
2. **State Machine**: 阅读 `query.ts` 中 `State` 类型的定义，然后搜索所有 `continue` 站点
3. **Tool System**: 从 `Tool.ts` 的接口定义开始，然后看 `toolExecution.ts` 的 `checkPermissionsAndCallTool`
4. **React in Terminal**: 从 `ink/ink.tsx` 的 `Ink` 类开始，理解 reconciler → layout → render 管道
5. **Config Merge**: 从 `settings/constants.ts` 的 `SETTING_SOURCES` 开始，然后看 `settings.ts` 的合并逻辑

---

恭喜你完成了 Claude Code 源码教学文档的全部阅读！你现在应该对 Claude Code 的架构、核心循环、工具系统、安全模型和工程实践有了系统性的理解。

如需深入某个特定模块，可以直接阅读对应章节指出的关键源文件。

## 动手实验

本章有对应的 Python 实验，通过编码复现上述概念：

> **[实验 16 — 设计模式](experiments/16-设计模式实验.md)**
>
> 涵盖内容：6 种模式实战（异步生成器、不可变状态、DI、工厂、配置合并、批量分区）
>
> ```bash
> cd experiments && python -m exp_16_design_patterns.main --mock
> ```
