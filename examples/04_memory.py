#!/usr/bin/env python3
"""Tiny file-backed memory store with TF-IDF style recall (no external libs)."""
from __future__ import annotations

import math
import re
import tempfile
from pathlib import Path


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def write_topics(base: Path) -> None:
    (base / "python.txt").write_text("Python is a language for agents and tools.", encoding="utf-8")
    (base / "mcp.txt").write_text(
        "MCP connects models to tools using JSON-RPC transports.", encoding="utf-8"
    )
    (base / "ui.txt").write_text("Ink renders React components in the terminal.", encoding="utf-8")


def build_index(base: Path) -> tuple[dict[str, dict[str, float]], dict[str, int]]:
    """Return per-doc term weights and document frequency."""
    docs = list(base.glob("*.txt"))
    df: dict[str, int] = {}
    tf: dict[str, dict[str, int]] = {}
    for p in docs:
        toks = tokenize(p.read_text(encoding="utf-8"))
        freq: dict[str, int] = {}
        for t in toks:
            freq[t] = freq.get(t, 0) + 1
        tf[p.name] = freq
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    n = len(docs)
    weights: dict[str, dict[str, float]] = {}
    for name, freq in tf.items():
        weights[name] = {}
        max_f = max(freq.values()) if freq else 1
        for term, c in freq.items():
            idf = math.log((1 + n) / (1 + df[term])) + 1.0
            weights[name][term] = (c / max_f) * idf
    return weights, df


def recall(weights: dict[str, dict[str, float]], query: str, top_k: int = 2) -> list[tuple[str, float]]:
    q_terms = tokenize(query)
    scores: dict[str, float] = {name: 0.0 for name in weights}
    for t in q_terms:
        for name, wmap in weights.items():
            scores[name] += wmap.get(t, 0.0)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        write_topics(base)
        weights, _ = build_index(base)
        q = "How do models talk to tools?"
        hits = recall(weights, q)
        print("query:", q)
        for name, score in hits:
            if score <= 0:
                continue
            body = (base / name).read_text(encoding="utf-8")
            print(f"  {name} score={score:.3f} :: {body[:60]}...")


if __name__ == "__main__":
    main()
