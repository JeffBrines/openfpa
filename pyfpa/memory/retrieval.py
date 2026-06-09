from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


_TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]+")
_IGNORED_FILES = {"index.yaml", "context-pack.md"}


class MemoryEntry(BaseModel):
    path: str
    category: str
    title: str
    text: str
    tokens: list[str] = Field(default_factory=list)


class MemoryHit(BaseModel):
    path: str
    category: str
    title: str
    excerpt: str
    score: float


class MemoryIndex(BaseModel):
    schema_version: int = 1
    entries: list[MemoryEntry] = Field(default_factory=list)


def _tokens(text: str) -> list[str]:
    return sorted(set(_TOKEN.findall(text.casefold())))


def _category(path: Path, workspace: Path) -> str:
    relative = path.relative_to(workspace)
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem


def _title(path: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def build_memory_index(workspace: str | Path) -> MemoryIndex:
    """Build a deterministic lexical index from canonical `.fpa` files."""
    workspace = Path(workspace)
    entries: list[MemoryEntry] = []
    if not workspace.exists():
        return MemoryIndex()
    for path in sorted(workspace.rglob("*")):
        if (
            not path.is_file()
            or path.name in _IGNORED_FILES
            or path.suffix.lower() not in {".md", ".yaml", ".yml"}
        ):
            continue
        text = path.read_text()
        relative = str(path.relative_to(workspace))
        entries.append(MemoryEntry(
            path=relative,
            category=_category(path, workspace),
            title=_title(path, text),
            text=text,
            tokens=_tokens(f"{relative} {text}"),
        ))
    return MemoryIndex(entries=entries)


def save_memory_index(index: MemoryIndex, path: str | Path) -> None:
    """Save the rebuildable index without changing canonical memory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(index.model_dump(), sort_keys=False))


def load_memory_index(path: str | Path) -> MemoryIndex:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"memory index not found: {path}")
    return MemoryIndex.model_validate(yaml.safe_load(path.read_text()))


def search_memory(
    index: MemoryIndex,
    query: str,
    *,
    categories: list[str] | None = None,
    limit: int = 8,
) -> list[MemoryHit]:
    """Rank memory entries by transparent lexical overlap."""
    if limit < 1:
        raise ValueError("memory search limit must be at least 1")
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return []
    allowed = set(categories or [])
    hits: list[MemoryHit] = []
    for entry in index.entries:
        if allowed and entry.category not in allowed:
            continue
        entry_tokens = set(entry.tokens)
        overlap = query_tokens & entry_tokens
        if not overlap:
            continue
        title_tokens = set(_tokens(entry.title))
        path_tokens = set(_tokens(entry.path))
        score = (
            len(overlap) / len(query_tokens)
            + 0.5 * len(query_tokens & title_tokens)
            + 0.25 * len(query_tokens & path_tokens)
        )
        excerpt = " ".join(entry.text.split())
        if len(excerpt) > 320:
            excerpt = excerpt[:317].rstrip() + "..."
        hits.append(MemoryHit(
            path=entry.path,
            category=entry.category,
            title=entry.title,
            excerpt=excerpt,
            score=score,
        ))
    return sorted(hits, key=lambda hit: (-hit.score, hit.path))[:limit]


def build_context_pack(
    index: MemoryIndex,
    task: str,
    *,
    categories: list[str] | None = None,
    limit: int = 8,
) -> str:
    """Render a bounded, source-linked memory pack for an agent task."""
    hits = search_memory(index, task, categories=categories, limit=limit)
    lines = [
        "# Task Memory Pack",
        "",
        f"**Task:** {task}",
        "",
        "> Rebuildable retrieval output. Canonical memory remains in the linked files.",
        "",
    ]
    if not hits:
        lines.append("No relevant memory found.")
        return "\n".join(lines) + "\n"
    for hit in hits:
        lines.extend([
            f"## {hit.title}",
            "",
            f"- **Source:** `{hit.path}`",
            f"- **Category:** `{hit.category}`",
            f"- **Relevance:** {hit.score:.3f}",
            f"- **Excerpt:** {hit.excerpt}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"
