"""
Experiment 11 — Plugin & Skill System

Replicates the plugin/skill loading from src/services/plugins/ and
src/services/skills/.

Key concepts demonstrated:
  1. SKILL.md file discovery and parsing
  2. Plugin manifest with lifecycle hooks
  3. Command priority chain (built-in > plugin > skill > MCP)
  4. Skill execution as prompt injection
  5. Plugin capability contributions (commands, tools, MCP)

Run:
    python -m exp_11_plugin_skill.main --mock
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# Skill data model
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    name: str
    description: str
    content: str
    source: str  # "bundled", "disk", "plugin", "mcp"
    path: str | None = None

    @property
    def priority(self) -> int:
        priorities = {"bundled": 0, "disk": 1, "plugin": 2, "mcp": 3}
        return priorities.get(self.source, 99)


def parse_skill_md(path: str) -> Skill | None:
    """Parse a SKILL.md file with YAML-like frontmatter."""
    try:
        content = Path(path).read_text()
    except (OSError, IOError):
        return None

    name = ""
    description = ""
    body = content

    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if frontmatter_match:
        fm_text = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        for line in fm_text.splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"\'')

    if not name:
        name = Path(path).parent.name

    return Skill(name=name, description=description, content=body, source="disk", path=path)


# ---------------------------------------------------------------------------
# Plugin data model
# ---------------------------------------------------------------------------

@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    capabilities: list[str] = field(default_factory=list)


@dataclass
class Plugin:
    manifest: PluginManifest
    skills: list[Skill] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    hooks: dict[str, Any] = field(default_factory=dict)
    is_loaded: bool = False

    def load(self) -> None:
        """Simulate plugin loading and lifecycle init."""
        self.is_loaded = True
        if "on_load" in self.hooks:
            self.hooks["on_load"]()

    def unload(self) -> None:
        if "on_unload" in self.hooks:
            self.hooks["on_unload"]()
        self.is_loaded = False


# ---------------------------------------------------------------------------
# Command system integration
# ---------------------------------------------------------------------------

@dataclass
class Command:
    name: str
    description: str
    cmd_type: str  # "local" or "prompt"
    source: str  # "built-in", "plugin", "skill"
    handler: Any = None
    prompt_template: str = ""

    @property
    def priority(self) -> int:
        priorities = {"built-in": 0, "plugin": 1, "skill": 2}
        return priorities.get(self.source, 99)


def merge_commands(
    built_ins: list[Command],
    plugin_cmds: list[Command],
    skill_cmds: list[Command],
) -> list[Command]:
    """Merge commands with priority: built-in > plugin > skill."""
    by_name: dict[str, Command] = {}
    for cmd_list in [built_ins, plugin_cmds, skill_cmds]:
        for cmd in sorted(cmd_list, key=lambda c: c.priority):
            by_name.setdefault(cmd.name, cmd)
    return sorted(by_name.values(), key=lambda c: c.name)


# ---------------------------------------------------------------------------
# Skill-to-command conversion
# ---------------------------------------------------------------------------

def skill_to_command(skill: Skill) -> Command:
    return Command(
        name=skill.name,
        description=skill.description or f"Run {skill.name} skill",
        cmd_type="prompt",
        source="skill",
        prompt_template=skill.content,
    )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 11: Plugin & Skill System")
    parser.parse_args()

    header("Experiment 11: Plugin & Skill System")

    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"

        # Create sample SKILL.md files
        for skill_info in [
            ("code-review", "code-review", "Review code for quality and best practices",
             "Review the following code for:\n- Code quality\n- Security issues\n- Performance\n- Best practices\n\nProvide specific, actionable feedback."),
            ("test-writer", "test-writer", "Generate test cases for code",
             "Generate comprehensive test cases for the provided code:\n- Unit tests\n- Edge cases\n- Error scenarios\n\nUse pytest conventions."),
            ("doc-generator", "doc-generator", "Generate documentation from code",
             "Generate clear documentation for the provided code:\n- Function signatures\n- Parameters\n- Return values\n- Usage examples"),
        ]:
            name, dirname, desc, body = skill_info
            skill_dir = skills_dir / dirname
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}\n"
            )

        section("1. Skill Discovery & Parsing")
        step(1, f"Scanning {skills_dir} for SKILL.md files...")

        discovered_skills: list[Skill] = []
        for skill_md in skills_dir.rglob("SKILL.md"):
            skill = parse_skill_md(str(skill_md))
            if skill:
                discovered_skills.append(skill)
                info(f"  Found: {skill.name} ({skill.source}) — {skill.description}")

        step(2, f"Discovered {len(discovered_skills)} skills")

        # Add bundled skills
        bundled = [
            Skill("memory", "Manage agent memory", "/memory [save|recall] <topic>", "bundled"),
            Skill("compact", "Compact conversation context", "/compact", "bundled"),
        ]
        all_skills = bundled + discovered_skills
        info(f"Total skills (bundled + disk): {len(all_skills)}")

        section("2. Plugin System")
        plugin = Plugin(
            manifest=PluginManifest(
                name="security-scanner",
                version="1.0.0",
                description="Security scanning plugin",
                capabilities=["commands", "skills"],
            ),
            skills=[
                Skill("security-scan", "Scan for security vulnerabilities",
                      "Analyze the codebase for:\n- SQL injection\n- XSS\n- CSRF\n- Hardcoded secrets",
                      "plugin"),
            ],
            commands=[
                {"name": "scan", "description": "Run security scan", "type": "local"},
            ],
            hooks={
                "on_load": lambda: info("  Plugin 'security-scanner' loaded"),
                "on_unload": lambda: info("  Plugin 'security-scanner' unloaded"),
            },
        )

        step(3, "Loading plugin...")
        plugin.load()
        info(f"  Manifest: {plugin.manifest.name} v{plugin.manifest.version}")
        info(f"  Capabilities: {plugin.manifest.capabilities}")
        info(f"  Skills contributed: {len(plugin.skills)}")
        info(f"  Commands contributed: {len(plugin.commands)}")

        section("3. Command Priority Chain")
        built_in_cmds = [
            Command("compact", "Compact context", "local", "built-in"),
            Command("memory", "Manage memory", "local", "built-in"),
            Command("config", "Show configuration", "local", "built-in"),
        ]

        plugin_cmds = [
            Command("scan", "Security scan", "local", "plugin"),
            Command("compact", "Plugin compact (should lose)", "local", "plugin"),
        ]

        skill_cmds = [skill_to_command(s) for s in all_skills]

        merged = merge_commands(built_in_cmds, plugin_cmds, skill_cmds)
        step(4, f"Merged command pool: {len(merged)} commands")

        print(f"\n    {'Command':<20} {'Type':<10} {'Source':<12} {'Description'}")
        print(f"    {'-'*20} {'-'*10} {'-'*12} {'-'*30}")
        for cmd in merged:
            source_color = {"built-in": "green", "plugin": "magenta", "skill": "cyan"}[cmd.source]
            print(f"    {cmd.name:<20} {cmd.cmd_type:<10} {colored(cmd.source, source_color):<24} {cmd.description}")

        info("\nNote: built-in 'compact' wins over plugin 'compact' (priority chain)")

        section("4. Skill Execution (Prompt Injection)")
        step(5, "Executing 'code-review' skill...")
        review_skill = next((s for s in all_skills if s.name == "code-review"), None)
        if review_skill:
            injected_prompt = (
                f"[Skill: {review_skill.name}]\n\n"
                f"{review_skill.content}\n\n"
                f"[User Code]\n"
                f"def add(a, b):\n    return a + b\n"
            )
            info("Prompt injected into message:")
            for line in injected_prompt.split("\n")[:8]:
                print(f"    {colored(line, 'gray')}")

        # Cleanup
        plugin.unload()

    section("Summary")
    info("Skills: SKILL.md files with frontmatter, converted to prompt-type commands")
    info("Plugins: manifests with lifecycle hooks, contribute commands + skills + MCP")
    info("Priority: built-in > plugin > skill > MCP (first-seen wins on collision)")


if __name__ == "__main__":
    asyncio.run(main())
