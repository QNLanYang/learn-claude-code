# 多 Agent 协作 / Multi-Agent Coordination

```mermaid
flowchart TB
  subgraph nest["Nested delegation"]
    Parent["Parent Agent"]
    AgentTool["AgentTool"]
    Child["Child Agent"]
    Parent --> AgentTool
    AgentTool --> Child
  end
  subgraph restrict["Child constraints"]
    RT["restricted tools"]
    SC["sidechain transcript"]
    Child --> RT
    Child --> SC
  end
  subgraph swarm["Leader and workers"]
    Leader["Leader"]
    MB["File Mailbox"]
    W1["Worker 1"]
    W2["Worker 2"]
    Leader --> MB
    MB --> W1
    MB --> W2
    PS["permission sync"]
    W1 --> PS
    W2 --> PS
    PS --> Leader
  end
```

**说明（zh）**：嵌套场景下父 Agent 通过 `AgentTool` 启动子 Agent，子体使用受限工具集，侧链 transcript 与主会话隔离。Swarm 式协作中 Leader 通过文件邮箱向 Worker 分派任务，权限状态在参与者间同步。

**Notes (en)**: Nesting: the parent invokes `AgentTool` to spawn a child with a restricted tool allow-list and an isolated sidechain transcript. Swarm-style: a leader uses a file mailbox to assign work to workers, with permission state kept in sync across participants.
