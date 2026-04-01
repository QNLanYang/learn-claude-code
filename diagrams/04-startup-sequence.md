# 启动时序 / Startup Sequence

```mermaid
sequenceDiagram
  participant CLI as cli.tsx
  participant Fast as fast_path_check
  participant Main as main.tsx
  participant PF as parallel_prefetch
  participant MDM as MDM
  participant Auth as auth
  participant Flags as flags
  participant Config as config
  participant Init as init
  participant Reg as register_tools
  participant Launch as REPL_or_headless

  CLI->>Fast: entry
  Fast-->>CLI: ok or short_circuit
  CLI->>Main: bootstrap
  Main->>PF: start parallel prefetch
  par MDM load
    PF->>MDM: prefetch
  and auth
    PF->>Auth: prefetch
  and flags
    PF->>Flags: prefetch
  and config
    PF->>Config: prefetch
  end
  PF-->>Main: ready
  Main->>Init: init
  Init->>Reg: register tools
  Reg-->>Init: registry ready
  Init->>Launch: launch REPL or headless
  Launch-->>Main: running
```

**说明（zh）**：`cli.tsx` 经快速路径判断后进入 `main.tsx`；并行预取 MDM、认证、特性开关与配置以降低首屏延迟；`init()` 完成环境初始化并注册工具；最后启动交互 REPL 或无头模式。

**Notes (en)**: After `cli.tsx` fast-path checks, `main.tsx` runs parallel prefetch for MDM, auth, flags, and config; `init()` wires the environment and tool registry; then the app launches the REPL or headless runner.
