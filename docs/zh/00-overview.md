# Claude Code 源码教学文档 — 项目总览与快速导航

## 项目背景

Claude Code 是 Anthropic 开发的 CLI 工具，允许用户从终端与 Claude 交互，执行软件工程任务：编辑文件、运行命令、搜索代码库、协调工作流。

本仓库是 2026 年 3 月 31 日通过 npm 发布包中的 source map 文件公开暴露的源码快照，仅用于教育和安全研究目的。

## 技术栈

| 类别 | 技术 |
|------|------|
| 运行时 | [Bun](https://bun.sh) |
| 语言 | TypeScript (strict) |
| 终端 UI | React + [Ink](https://github.com/vadimdemedes/ink) (自定义 fork) |
| CLI 解析 | [Commander.js](https://github.com/tj/commander.js) (extra-typings) |
| Schema 验证 | [Zod v4](https://zod.dev) |
| 代码搜索 | [ripgrep](https://github.com/BurntSushi/ripgrep) |
| 协议 | [MCP SDK](https://modelcontextprotocol.io), LSP |
| API | [Anthropic SDK](https://docs.anthropic.com) |
| 遥测 | OpenTelemetry + gRPC |
| 特性开关 | GrowthBook + `bun:bundle` 编译期消除 |
| 认证 | OAuth 2.0, JWT, macOS Keychain |

## 代码规模

- **~1,900 个源文件**，512,000+ 行代码
- 纯 `src/` 单包结构，无 `package.json`（此快照仅包含源码）
- 301 个目录

## 快速导航

| 我想了解... | 章节 | 核心文件 |
|-------------|------|----------|
| 整体架构长什么样 | [01-architecture](01-architecture.md) | `src/` 目录结构 |
| 程序怎么启动的 | [02-startup-flow](02-startup-flow.md) | `entrypoints/cli.tsx`, `main.tsx` |
| Agent 循环怎么运行的 | [03-core-loop](03-core-loop.md) | `query.ts`, `QueryEngine.ts` |
| 工具怎么定义和执行的 | [04-tool-system](04-tool-system.md) | `Tool.ts`, `tools.ts`, `services/tools/` |
| 权限系统怎么工作 | [05-permission-security](05-permission-security.md) | `utils/permissions/`, `types/permissions.ts` |
| System Prompt 怎么组装 | [06-context-prompt](06-context-prompt.md) | `constants/prompts.ts`, `context.ts` |
| 记忆系统怎么设计 | [07-memory-system](07-memory-system.md) | `memdir/`, `services/SessionMemory/` |
| 终端 UI 怎么渲染 | [08-terminal-ui](08-terminal-ui.md) | `ink/`, `screens/REPL.tsx`, `components/` |
| MCP 协议怎么集成 | [09-mcp-integration](09-mcp-integration.md) | `services/mcp/`, `tools/MCPTool/` |
| 多 Agent 怎么协作 | [10-multi-agent](10-multi-agent.md) | `tools/AgentTool/`, `utils/swarm/` |
| 插件和技能系统 | [11-plugin-skill](11-plugin-skill.md) | `plugins/`, `skills/`, `tools/SkillTool/` |
| API 调用和流式处理 | [12-api-streaming](12-api-streaming.md) | `services/api/claude.ts`, `services/api/client.ts` |
| 配置体系 | [13-config-settings](13-config-settings.md) | `utils/settings/` |
| 上下文压缩 | [14-compact-context-mgmt](14-compact-context-mgmt.md) | `services/compact/` |
| 斜杠命令系统 | [15-command-system](15-command-system.md) | `commands.ts`, `commands/` |
| 设计模式总结 | [16-design-patterns](16-design-patterns.md) | 跨文件 |

## 推荐阅读路径

### 快速路线（约 2 小时）

适合想快速理解核心机制的读者：

```
00-overview → 01-architecture → 03-core-loop → 04-tool-system → 06-context-prompt
```

这条路线覆盖了 Agent 最核心的"大脑"——循环如何运转、工具如何执行、提示词如何组装。

### 完整路线（约 1-2 天）

适合想系统性深入学习的读者，按序阅读全部 17 篇文档：

```
00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16
```

### 按兴趣分支

- **想理解 Agent 核心**：03 → 04 → 05 → 06
- **想理解扩展机制**：09 → 10 → 11 → 15
- **想理解工程实践**：02 → 12 → 13 → 14 → 16
- **想理解 UI 实现**：08

## 源码目录速览

```
src/
├── main.tsx                 # 主入口（Commander CLI + Ink 渲染）
├── query.ts                 # 核心 Agent 循环
├── QueryEngine.ts           # SDK/无头模式的查询引擎封装
├── Tool.ts                  # 工具类型定义与上下文
├── tools.ts                 # 工具注册表
├── commands.ts              # 命令注册表
├── context.ts               # 上下文收集（CLAUDE.md、git 等）
├── cost-tracker.ts          # Token 成本追踪
│
├── entrypoints/             # 入口点（cli.tsx、init.ts、mcp.ts）
├── bootstrap/               # 全局启动状态
├── screens/                 # 全屏 UI（REPL、Doctor）
├── query/                   # 查询管道辅助（deps、config、stopHooks）
│
├── tools/                   # ~40 个工具实现
├── commands/                # ~50 个斜杠命令
├── components/              # ~140 个 Ink UI 组件
├── hooks/                   # React Hooks
├── ink/                     # Ink 渲染引擎（自定义 fork）
├── services/                # 外部服务集成（API、MCP、OAuth 等）
├── utils/                   # 工具函数（权限、设置、模型等）
│
├── plugins/                 # 插件系统
├── skills/                  # 技能系统
├── bridge/                  # IDE 桥接
├── memdir/                  # 持久化记忆目录
├── tasks/                   # 任务管理（子 Agent、Teammate）
├── state/                   # 状态管理
├── keybindings/             # 快捷键配置
├── vim/                     # Vim 模式
├── voice/                   # 语音输入
├── remote/                  # 远程会话
└── ...
```

## 动手实验

除了文档阅读，我们还提供了 **15 个 Python 实验**，让你通过编码复现 Claude Code 的核心设计模式。

实验支持三种运行模式：`--mock`（离线）、`--provider anthropic`、`--provider openai`。

### 实验目录

| 实验 | 对应章节 | 学习路径 |
|------|---------|---------|
| [exp_03 核心 Agent 循环](experiments/03-核心Agent循环实验.md) | 03 - Core Loop | **核心** |
| [exp_04 工具系统](experiments/04-工具系统实验.md) | 04 - Tool System | **核心** |
| [exp_05 权限引擎](experiments/05-权限引擎实验.md) | 05 - Permissions | **核心** |
| [exp_06 提示词组装](experiments/06-提示词组装实验.md) | 06 - Context/Prompt | **核心** |
| [exp_07 记忆系统](experiments/07-记忆系统实验.md) | 07 - Memory | **核心** |
| [exp_09 MCP 客户端](experiments/09-MCP客户端实验.md) | 09 - MCP | **核心** |
| [exp_10 多 Agent 协作](experiments/10-多Agent协作实验.md) | 10 - Multi-Agent | **核心** |
| [exp_12 流式 API](experiments/12-流式API实验.md) | 12 - API/Streaming | **核心** |
| [exp_14 上下文压缩](experiments/14-上下文压缩实验.md) | 14 - Compaction | **核心** |
| [exp_02 启动流程](experiments/02-启动流程实验.md) | 02 - Startup Flow | 扩展 |
| [exp_08 终端 UI](experiments/08-终端UI实验.md) | 08 - Terminal UI | 扩展 |
| [exp_11 插件技能](experiments/11-插件技能系统实验.md) | 11 - Plugin/Skill | 扩展 |
| [exp_13 配置系统](experiments/13-配置系统实验.md) | 13 - Config | 扩展 |
| [exp_15 命令系统](experiments/15-命令系统实验.md) | 15 - Commands | 扩展 |
| [exp_16 设计模式](experiments/16-设计模式实验.md) | 16 - Patterns | 扩展 |

详细指南请参阅 [实验指南](experiments/00-实验指南.md)。

## 下一步

前往 [01-architecture.md](01-architecture.md) 了解整体架构设计。
