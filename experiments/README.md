# Claude Code Learning Experiments

Hands-on Python experiments that replicate the core design patterns found in Claude Code's TypeScript source.

## Setup

```bash
cd experiments
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running Experiments

Every experiment supports three providers via `--provider`:

```bash
# Offline / no API key required
python -m exp_03_core_agent_loop.main --mock

# Using Anthropic API
export ANTHROPIC_API_KEY=sk-ant-...
python -m exp_03_core_agent_loop.main --provider anthropic

# Using OpenAI-compatible API
export OPENAI_API_KEY=sk-...
python -m exp_03_core_agent_loop.main --provider openai
```

## Learning Tracks

### Focused Track (9 core experiments)

The essential path for understanding Claude Code's architecture:

```
exp_03 Agent Loop ──> exp_04 Tool System ──> exp_05 Permissions
       │                                           │
       v                                           v
exp_12 Streaming ──> exp_14 Compaction ──> exp_06 Prompt Assembly
                                                   │
                                                   v
                     exp_10 Multi-Agent <── exp_07 Memory System
                            │
                            v
                     exp_09 MCP Client
```

### Comprehensive Track (all 15 experiments)

Adds 6 supplementary experiments to the focused track:

| Experiment | Chapter | Track |
|-----------|---------|-------|
| `exp_02_startup_flow` | 02 - Startup Flow | Comprehensive |
| `exp_03_core_agent_loop` | 03 - Core Loop | **Focused** |
| `exp_04_tool_system` | 04 - Tool System | **Focused** |
| `exp_05_permission_engine` | 05 - Permissions | **Focused** |
| `exp_06_prompt_assembly` | 06 - Context/Prompt | **Focused** |
| `exp_07_memory_system` | 07 - Memory | **Focused** |
| `exp_08_terminal_ui` | 08 - Terminal UI | Comprehensive |
| `exp_09_mcp_client` | 09 - MCP | **Focused** |
| `exp_10_multi_agent` | 10 - Multi-Agent | **Focused** |
| `exp_11_plugin_skill` | 11 - Plugin/Skill | Comprehensive |
| `exp_12_streaming_api` | 12 - API/Streaming | **Focused** |
| `exp_13_config_system` | 13 - Config | Comprehensive |
| `exp_14_context_compaction` | 14 - Compaction | **Focused** |
| `exp_15_command_system` | 15 - Commands | Comprehensive |
| `exp_16_design_patterns` | 16 - Patterns | Comprehensive |

## Documentation

- Chinese: [docs/zh/experiments/](../docs/zh/experiments/)
- English: [docs/en/experiments/](../docs/en/experiments/)
