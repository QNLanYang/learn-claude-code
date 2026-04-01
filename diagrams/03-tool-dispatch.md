# 工具调度流水线 / Tool Dispatch Pipeline

```mermaid
flowchart TD
  start([tool_use blocks])
  v[validateInput]
  p[checkPermissions]
  part[partition concurrent or serial]
  batch[execute batch]
  mapr[map results]
  size[size check]
  append[append to messages]
  endnode([continue loop or terminate])
  start --> v
  v --> p
  p --> part
  part --> batch
  batch --> mapr
  mapr --> size
  size --> append
  append --> endnode
```

**说明（zh）**：模型产出的 `tool_use` 块先经输入校验与权限判断，再按依赖与策略分为并发或串行批次执行；结果映射回消息角色后做体积检查，最后追加到对话历史供下一轮模型使用。

**Notes (en)**: `tool_use` blocks are validated and permission-checked, partitioned into concurrent or serial batches, executed, mapped to message shapes, size-checked, and appended for the next model turn.
