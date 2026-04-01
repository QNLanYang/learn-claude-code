"""
Experiment 02 — Startup Flow

Simulates the cli.tsx -> main.tsx -> init chain from Claude Code.

Key concepts demonstrated:
  1. Thin CLI entry point with early fast paths
  2. Parallel prefetch using ThreadPoolExecutor
  3. Lazy imports for startup speed
  4. Initialization pipeline with ordered steps
  5. Mode dispatch (REPL, headless, special modes)

Run:
    python -m exp_02_startup_flow.main --mock
    python -m exp_02_startup_flow.main --version
    python -m exp_02_startup_flow.main --mode headless -p "Hello"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, warn, colored


# ---------------------------------------------------------------------------
# Fast paths (mirrors cli.tsx early exits)
# ---------------------------------------------------------------------------

def check_fast_paths(argv: list[str]) -> bool:
    """Handle flags that should exit immediately without full init."""
    if "--version" in argv:
        print("claude-code-experiment v1.0.0")
        return True
    if "--help-all" in argv:
        print("All commands: --version, --mode, --prompt, --mock")
        return True
    return False


# ---------------------------------------------------------------------------
# Parallel prefetch (mirrors main.tsx prefetch pattern)
# ---------------------------------------------------------------------------

def prefetch_mdm_settings() -> dict[str, Any]:
    """Simulate fetching managed device settings."""
    time.sleep(0.3)
    return {"max_tokens": 4096, "allowed_models": ["claude-sonnet-4-20250514"]}


def prefetch_auth_token() -> dict[str, Any]:
    """Simulate fetching auth token from keychain."""
    time.sleep(0.2)
    return {"token": "sk-ant-***", "expires_at": "2025-12-31"}


def prefetch_feature_flags() -> dict[str, Any]:
    """Simulate fetching feature flags from GrowthBook."""
    time.sleep(0.15)
    return {"mcp_enabled": True, "swarm_enabled": False, "vim_mode": True}


def prefetch_config() -> dict[str, Any]:
    """Simulate loading config from disk."""
    time.sleep(0.1)
    return {"theme": "dark", "model": "claude-sonnet-4-20250514"}


def run_parallel_prefetch() -> dict[str, Any]:
    """
    Run all prefetch tasks in parallel using ThreadPoolExecutor.
    Mirrors the Promise.all pattern in main.tsx.
    """
    results: dict[str, Any] = {}
    tasks = {
        "mdm_settings": prefetch_mdm_settings,
        "auth_token": prefetch_auth_token,
        "feature_flags": prefetch_feature_flags,
        "config": prefetch_config,
    }

    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            elapsed = (time.time() - start) * 1000
            try:
                results[name] = future.result()
                info(f"  [{elapsed:6.0f}ms] Prefetched: {name}")
            except Exception as e:
                warn(f"  [{elapsed:6.0f}ms] Failed: {name} ({e})")
                results[name] = None

    total = (time.time() - start) * 1000
    info(f"  All prefetch completed in {total:.0f}ms (sequential would be ~750ms)")
    return results


# ---------------------------------------------------------------------------
# Initialization pipeline (mirrors init.ts)
# ---------------------------------------------------------------------------

def init_step(name: str, duration_ms: int = 50) -> None:
    """Simulate an initialization step."""
    time.sleep(duration_ms / 1000)
    step_num = getattr(init_step, "_counter", 0) + 1
    init_step._counter = step_num  # type: ignore[attr-defined]
    info(f"  Init [{step_num}]: {name}")


def run_init(prefetch_data: dict[str, Any]) -> dict[str, Any]:
    """
    Run the initialization pipeline.
    Mirrors init() in src/init.ts.
    """
    init_step("Validate environment")
    init_step("Setup error handlers")
    init_step("Load settings (merged with prefetched config)")
    init_step("Initialize auth (using prefetched token)")
    init_step("Register tools")
    init_step("Setup MCP connections")
    init_step("Initialize telemetry")

    return {
        "initialized": True,
        "tools_registered": 15,
        "mcp_servers": 2,
        **prefetch_data,
    }


# ---------------------------------------------------------------------------
# Mode dispatch (mirrors replLauncher.tsx / main.tsx)
# ---------------------------------------------------------------------------

async def launch_repl(state: dict[str, Any]) -> None:
    """Simulate launching interactive REPL mode."""
    info("Launching interactive REPL...")
    info(f"  Tools: {state.get('tools_registered', 0)} registered")
    info(f"  MCP servers: {state.get('mcp_servers', 0)} connected")
    info("  [REPL would start here — accepting user input]")


async def launch_headless(state: dict[str, Any], prompt: str) -> None:
    """Simulate headless mode (single query, no interactive loop)."""
    info(f"Headless mode — processing prompt: '{prompt}'")
    info("  [Would call query() and return result]")


async def launch_mcp_server(state: dict[str, Any]) -> None:
    """Simulate launching as MCP server."""
    info("Launching as MCP server (stdio transport)...")
    info("  [Would listen for JSON-RPC on stdin/stdout]")


# ---------------------------------------------------------------------------
# Main entry point (mirrors cli.tsx -> main.tsx)
# ---------------------------------------------------------------------------

async def main() -> None:
    raw_argv = sys.argv[1:]

    # --- Layer 1: Fast paths (cli.tsx) ---
    if check_fast_paths(raw_argv):
        return

    # --- Layer 2: Full CLI parsing (main.tsx / Commander) ---
    parser = argparse.ArgumentParser(description="Experiment 02: Startup Flow")
    parser.add_argument("--mode", choices=["repl", "headless", "mcp"], default="repl")
    parser.add_argument("-p", "--prompt", default=None)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--provider", default="mock")
    parser.add_argument("--model", default=None)
    args = parser.parse_args(raw_argv)

    header("Experiment 02: Startup Flow")

    # --- Layer 3: Parallel prefetch ---
    section("1. Parallel Prefetch")
    step(1, "Starting parallel prefetch tasks...")
    prefetch_data = run_parallel_prefetch()

    # --- Layer 4: Initialization ---
    section("2. Initialization Pipeline")
    step(2, "Running init sequence...")
    state = run_init(prefetch_data)
    info(f"Initialization complete. State keys: {list(state.keys())}")

    # --- Layer 5: Mode dispatch ---
    section("3. Mode Dispatch")
    step(3, f"Dispatching to mode: {args.mode}")

    if args.mode == "headless" and args.prompt:
        await launch_headless(state, args.prompt)
    elif args.mode == "mcp":
        await launch_mcp_server(state)
    else:
        await launch_repl(state)

    section("Startup Chain Summary")
    info("cli.tsx:   Fast paths (--version, --help) -> exit early")
    info("main.tsx:  Commander parse -> parallel prefetch -> init()")
    info("init.ts:   Environment -> auth -> tools -> MCP -> telemetry")
    info("launcher:  Mode dispatch -> REPL / headless / MCP server")


if __name__ == "__main__":
    asyncio.run(main())
