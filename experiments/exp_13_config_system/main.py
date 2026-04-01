"""
Experiment 13 — Configuration System

Replicates the layered configuration from src/utils/settings.ts.

Key concepts demonstrated:
  1. Multi-layer config with priority (system > CLI > env > user > project > local)
  2. Deep merge strategy
  3. Pydantic schema validation
  4. Environment variable override
  5. Config tool for runtime inspection

Run:
    python -m exp_13_config_system.main --mock
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# Configuration schema (Pydantic)
# ---------------------------------------------------------------------------

class ModelConfig(BaseModel):
    name: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7


class PermissionsConfig(BaseModel):
    mode: str = "default"
    allow_bash: bool = True
    allowed_directories: list[str] = Field(default_factory=lambda: ["."])


class UIConfig(BaseModel):
    theme: str = "dark"
    vim_mode: bool = False
    show_token_count: bool = True


class AppConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    verbose: bool = False
    telemetry: bool = True


# ---------------------------------------------------------------------------
# Deep merge utility
# ---------------------------------------------------------------------------

def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge override into base (immutable — returns new dict).
    Override values win; nested dicts are merged recursively.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


# ---------------------------------------------------------------------------
# Configuration sources
# ---------------------------------------------------------------------------

class ConfigSource:
    def __init__(self, name: str, priority: int, data: dict[str, Any]):
        self.name = name
        self.priority = priority
        self.data = data


def load_json_config(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def load_env_config() -> dict[str, Any]:
    """Load configuration from environment variables."""
    config: dict[str, Any] = {}

    env_map = {
        "CLAUDE_MODEL": ("model", "name"),
        "CLAUDE_MAX_TOKENS": ("model", "max_tokens"),
        "CLAUDE_THEME": ("ui", "theme"),
        "CLAUDE_VIM_MODE": ("ui", "vim_mode"),
        "CLAUDE_VERBOSE": ("verbose",),
        "CLAUDE_TELEMETRY": ("telemetry",),
    }

    for env_var, path in env_map.items():
        value = os.environ.get(env_var)
        if value is None:
            continue

        if value.lower() in ("true", "false"):
            value = value.lower() == "true"  # type: ignore[assignment]
        elif value.isdigit():
            value = int(value)  # type: ignore[assignment]

        current = config
        for part in path[:-1]:
            current = current.setdefault(part, {})
        current[path[-1]] = value

    return config


# ---------------------------------------------------------------------------
# Configuration manager
# ---------------------------------------------------------------------------

class ConfigManager:
    """Loads, merges, and validates configuration from multiple sources."""

    def __init__(self):
        self._sources: list[ConfigSource] = []
        self._merged: dict[str, Any] = {}
        self._config: AppConfig | None = None

    def add_source(self, source: ConfigSource) -> None:
        self._sources.append(source)
        self._sources.sort(key=lambda s: s.priority, reverse=True)

    def resolve(self) -> AppConfig:
        """Merge all sources by priority and validate."""
        self._merged = {}
        for source in reversed(self._sources):
            self._merged = deep_merge(self._merged, source.data)

        self._config = AppConfig.model_validate(self._merged)
        return self._config

    def get(self, dotted_path: str) -> Any:
        """Get a config value by dotted path (e.g., 'model.name')."""
        if not self._config:
            self.resolve()
        parts = dotted_path.split(".")
        obj: Any = self._config
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
        return obj

    def explain(self, dotted_path: str) -> list[dict[str, Any]]:
        """Show which sources contribute to a config value."""
        parts = dotted_path.split(".")
        contributions = []
        for source in self._sources:
            val = source.data
            for part in parts:
                if isinstance(val, dict) and part in val:
                    val = val[part]
                else:
                    val = None
                    break
            if val is not None:
                contributions.append({
                    "source": source.name,
                    "priority": source.priority,
                    "value": val,
                })
        return contributions


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 13: Configuration System")
    parser.parse_args()

    header("Experiment 13: Configuration System")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample config files
        system_config = {"model": {"max_tokens": 8192}, "telemetry": True, "permissions": {"mode": "default"}}
        user_config = {"model": {"name": "claude-sonnet-4-20250514", "temperature": 0.5}, "ui": {"theme": "dark", "vim_mode": True}}
        project_config = {"model": {"name": "claude-sonnet-4-20250514"}, "permissions": {"allowed_directories": ["src/", "tests/"]}}
        local_config = {"verbose": True, "ui": {"show_token_count": False}}

        for name, data in [("system", system_config), ("user", user_config), ("project", project_config), ("local", local_config)]:
            path = Path(tmpdir) / f"{name}.json"
            path.write_text(json.dumps(data, indent=2))

        section("1. Configuration Sources")
        manager = ConfigManager()

        sources = [
            ConfigSource("system (MDM/enterprise)", 100, load_json_config(f"{tmpdir}/system.json")),
            ConfigSource("user (~/.claude/settings.json)", 60, load_json_config(f"{tmpdir}/user.json")),
            ConfigSource("project (.claude/settings.json)", 40, load_json_config(f"{tmpdir}/project.json")),
            ConfigSource("local (.claude/settings.local.json)", 20, load_json_config(f"{tmpdir}/local.json")),
            ConfigSource("environment variables", 80, load_env_config()),
        ]

        for source in sources:
            manager.add_source(source)
            step_text = f"priority={source.priority:3d}"
            non_empty = bool(source.data)
            status = colored("has data", "green") if non_empty else colored("empty", "gray")
            info(f"  [{step_text}] {source.name:40s} {status}")

        section("2. Deep Merge Demonstration")
        step(1, "Merging all sources by priority...")
        config = manager.resolve()

        print(f"\n    Final configuration:")
        config_dict = config.model_dump()
        for top_key, top_val in config_dict.items():
            if isinstance(top_val, dict):
                print(f"    {colored(top_key, 'cyan')}:")
                for k, v in top_val.items():
                    print(f"      {k}: {colored(str(v), 'green')}")
            else:
                print(f"    {colored(top_key, 'cyan')}: {colored(str(top_val), 'green')}")

        section("3. Config Value Provenance")
        paths_to_explain = ["model.name", "model.max_tokens", "ui.vim_mode", "verbose", "permissions.mode"]

        for path in paths_to_explain:
            step(2, f"Explaining '{path}':")
            final_value = manager.get(path)
            contributions = manager.explain(path)
            print(f"    Final value: {colored(str(final_value), 'green')}")
            for c in contributions:
                winner = " <-- WINNER" if c["value"] == final_value else ""
                color = "yellow" if winner else "gray"
                print(f"      [{c['priority']:3d}] {c['source']:30s} = {colored(str(c['value']), color)}{winner}")

        section("4. Deep Merge Details")
        step(3, "Demonstrating merge behavior:")

        base = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2]}
        override = {"b": {"y": 99, "z": 30}, "c": [3, 4], "d": "new"}
        merged = deep_merge(base, override)

        print(f"    base:     {json.dumps(base)}")
        print(f"    override: {json.dumps(override)}")
        print(f"    merged:   {colored(json.dumps(merged), 'green')}")
        info("  Nested dicts merged recursively; arrays and scalars replaced entirely")

        section("5. Validation")
        step(4, "Testing invalid config...")
        try:
            bad_config = {"model": {"max_tokens": "not_a_number"}}
            AppConfig.model_validate(deep_merge(config_dict, bad_config))
            warn("Should have raised validation error!")
        except Exception as e:
            info(f"  Caught validation error: {str(e)[:100]}")

    section("Summary")
    info("Layered config: system(100) > env(80) > user(60) > project(40) > local(20)")
    info("Deep merge: nested dicts merged recursively, scalars/arrays replaced")
    info("Pydantic: schema validation with type coercion and defaults")
    info("Provenance: explain() shows which source set each value")


if __name__ == "__main__":
    asyncio.run(main())
