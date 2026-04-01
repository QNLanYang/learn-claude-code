"""
Experiment 07 — Memory System

Replicates the three-layer memory architecture from src/utils/memory/.

Key concepts demonstrated:
  1. Long-term memory: MEMORY.md index + topic files
  2. Session memory: extract key facts from conversation
  3. Recall: keyword match + TF-IDF scoring
  4. Memory injection into system prompt
  5. Deduplication of already-surfaced memories

Run:
    python -m exp_07_memory_system.main --mock
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import UnifiedLLMClient
from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# Memory data structures
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    topic: str
    content: str
    source: str = "user"  # user, session, agent


@dataclass
class MemoryIndex:
    entries: list[dict[str, str]] = field(default_factory=list)

    def add(self, topic: str, filename: str, summary: str) -> None:
        self.entries.append({"topic": topic, "file": filename, "summary": summary})

    def to_markdown(self) -> str:
        lines = ["# Memory Index\n"]
        for e in self.entries:
            lines.append(f"- **{e['topic']}** → `{e['file']}` — {e['summary']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Layer 1: Long-term memory (file-based)
# ---------------------------------------------------------------------------

class LongTermMemory:
    """File-based memory store using MEMORY.md index and topic files."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index = MemoryIndex()
        self._load_index()

    def _index_path(self) -> Path:
        return self.base_dir / "MEMORY.md"

    def _load_index(self) -> None:
        path = self._index_path()
        if path.exists():
            content = path.read_text()
            for line in content.splitlines():
                match = re.match(r"- \*\*(.+?)\*\* → `(.+?)` — (.+)", line)
                if match:
                    self.index.add(match.group(1), match.group(2), match.group(3))

    def write(self, topic: str, content: str) -> str:
        filename = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_") + ".md"
        filepath = self.base_dir / filename
        filepath.write_text(f"# {topic}\n\n{content}\n")

        existing = [e for e in self.index.entries if e["topic"] == topic]
        if not existing:
            summary = content[:100].replace("\n", " ")
            self.index.add(topic, filename, summary)
            self._index_path().write_text(self.index.to_markdown())

        return filename

    def read(self, topic: str) -> str | None:
        for entry in self.index.entries:
            if entry["topic"].lower() == topic.lower():
                path = self.base_dir / entry["file"]
                if path.exists():
                    return path.read_text()
        return None

    def list_topics(self) -> list[str]:
        return [e["topic"] for e in self.index.entries]

    def all_contents(self) -> dict[str, str]:
        result = {}
        for entry in self.index.entries:
            path = self.base_dir / entry["file"]
            if path.exists():
                result[entry["topic"]] = path.read_text()
        return result


# ---------------------------------------------------------------------------
# Layer 2: Session memory (extract facts from conversation)
# ---------------------------------------------------------------------------

class SessionMemory:
    """Extracts and stores key facts from the current conversation."""

    def __init__(self):
        self.facts: list[str] = []
        self._surfaced: set[str] = set()

    def extract_from_messages(
        self,
        messages: list[dict[str, Any]],
        client: UnifiedLLMClient | None = None,
    ) -> list[str]:
        """
        Extract key facts from conversation messages.
        In production, this uses a forked LLM call. Here we use simple heuristics.
        """
        new_facts = []
        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            for sentence in re.split(r"[.!?\n]", content):
                sentence = sentence.strip()
                if len(sentence) < 10:
                    continue
                if any(kw in sentence.lower() for kw in ["prefer", "always", "never", "use", "important"]):
                    if sentence not in self.facts:
                        self.facts.append(sentence)
                        new_facts.append(sentence)
        return new_facts

    def get_unsurfaced(self) -> list[str]:
        return [f for f in self.facts if f not in self._surfaced]

    def mark_surfaced(self, facts: list[str]) -> None:
        self._surfaced.update(facts)


# ---------------------------------------------------------------------------
# Layer 3: Memory recall (TF-IDF scoring)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _compute_tfidf(query_tokens: list[str], documents: dict[str, str]) -> list[tuple[str, float]]:
    """Simple TF-IDF scoring of documents against query."""
    if not documents:
        return []

    doc_tokens = {name: _tokenize(text) for name, text in documents.items()}
    n_docs = len(doc_tokens)

    df: Counter[str] = Counter()
    for tokens in doc_tokens.values():
        for t in set(tokens):
            df[t] += 1

    scores: list[tuple[str, float]] = []
    for name, tokens in doc_tokens.items():
        if not tokens:
            scores.append((name, 0.0))
            continue
        tf = Counter(tokens)
        score = 0.0
        for qt in query_tokens:
            if qt in tf:
                tf_val = tf[qt] / len(tokens)
                idf_val = math.log((n_docs + 1) / (df.get(qt, 0) + 1)) + 1
                score += tf_val * idf_val
        scores.append((name, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def find_relevant_memories(
    query: str,
    memory: LongTermMemory,
    top_k: int = 3,
    min_score: float = 0.01,
) -> list[tuple[str, str, float]]:
    """Find memories most relevant to a query using TF-IDF."""
    query_tokens = _tokenize(query)
    all_contents = memory.all_contents()
    scored = _compute_tfidf(query_tokens, all_contents)

    results = []
    for topic, score in scored[:top_k]:
        if score >= min_score:
            content = all_contents[topic]
            results.append((topic, content, score))
    return results


# ---------------------------------------------------------------------------
# Memory injection into system prompt
# ---------------------------------------------------------------------------

def inject_memories(
    system_prompt: str,
    relevant_memories: list[tuple[str, str, float]],
    session_facts: list[str],
) -> str:
    """Inject retrieved memories and session facts into the system prompt."""
    parts = [system_prompt]

    if relevant_memories:
        parts.append("\n\n## Relevant Memories\n")
        for topic, content, score in relevant_memories:
            preview = content.split("\n")
            preview = [l for l in preview if l.strip() and not l.startswith("#")][:5]
            parts.append(f"### {topic} (relevance: {score:.3f})")
            parts.append("\n".join(preview))
            parts.append("")

    if session_facts:
        parts.append("\n## Session Notes\n")
        for fact in session_facts:
            parts.append(f"- {fact}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 07: Memory System")
    args = parser.parse_args()

    header("Experiment 07: Memory System")

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = os.path.join(tmpdir, ".claude", "memory")

        section("1. Long-Term Memory (File-Based)")
        ltm = LongTermMemory(memory_dir)

        step(1, "Writing memories to disk...")
        ltm.write("Python Preferences", "User prefers Python 3.11+ with type hints.\n"
                   "Always use dataclasses over plain dicts.\n"
                   "Prefer asyncio for concurrent code.")
        ltm.write("Project Architecture", "The project uses a layered architecture:\n"
                   "- Entry layer: CLI parsing\n"
                   "- Core layer: Agent loop\n"
                   "- Service layer: API, tools, MCP\n"
                   "- UI layer: Terminal rendering")
        ltm.write("Testing Guidelines", "Use pytest for all tests.\n"
                   "Minimum 80% coverage.\n"
                   "Always write tests before implementation (TDD).")
        ltm.write("Git Workflow", "Use conventional commits: feat, fix, refactor, docs.\n"
                   "Always rebase before merging.\n"
                   "Never force push to main.")

        info(f"Stored {len(ltm.list_topics())} memory topics:")
        for topic in ltm.list_topics():
            print(f"    - {topic}")

        step(2, "Reading MEMORY.md index:")
        index_content = ltm._index_path().read_text()
        for line in index_content.splitlines():
            print(f"    {colored(line, 'gray')}")

        section("2. Memory Recall (TF-IDF)")
        queries = [
            "How should I write async Python code?",
            "What testing framework does the project use?",
            "How is the codebase structured?",
        ]

        for query in queries:
            step(3, f"Query: '{query}'")
            results = find_relevant_memories(query, ltm)
            if results:
                for topic, _, score in results:
                    bar = colored("█" * int(score * 50), "green")
                    print(f"      {topic:25s} score={score:.4f} {bar}")
            else:
                print(f"      (no relevant memories)")

        section("3. Session Memory (Fact Extraction)")
        session = SessionMemory()
        conversation = [
            {"role": "user", "content": "I always prefer using dataclasses for configuration."},
            {"role": "assistant", "content": "Great choice! Dataclasses are clean and Pythonic."},
            {"role": "user", "content": "Never use global mutable state. It causes bugs."},
            {"role": "user", "content": "The important thing is to validate all inputs."},
            {"role": "assistant", "content": "Absolutely, input validation is crucial for security."},
        ]

        facts = session.extract_from_messages(conversation)
        step(4, f"Extracted {len(facts)} session facts:")
        for fact in facts:
            print(f"    - {colored(fact, 'cyan')}")

        section("4. Memory Injection into Prompt")
        relevant = find_relevant_memories("How to write Python code with testing?", ltm, top_k=2)
        unsurfaced = session.get_unsurfaced()

        base_prompt = "You are a helpful coding assistant."
        enhanced = inject_memories(base_prompt, relevant, unsurfaced)

        step(5, f"Enhanced prompt: {len(enhanced)} chars (was {len(base_prompt)})")
        for line in enhanced.split("\n"):
            if line.strip():
                print(f"    {colored(line[:100], 'gray')}")

        session.mark_surfaced(unsurfaced)
        step(6, f"After surfacing: {len(session.get_unsurfaced())} unsurfaced facts remain")

        section("5. Deduplication")
        info("Second recall for same query skips already-surfaced memories")
        remaining = session.get_unsurfaced()
        info(f"Unsurfaced facts: {len(remaining)} (all surfaced in previous injection)")


if __name__ == "__main__":
    asyncio.run(main())
