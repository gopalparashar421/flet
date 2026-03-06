"""Index Flet markdown documentation into the FTS5 database."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

# ---------- MkDocs / Jinja syntax stripping ----------

_RE_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)
_RE_JINJA_BLOCK = re.compile(r"\{%.*?%\}", re.DOTALL)
_RE_JINJA_EXPR = re.compile(r"\{\{.*?\}\}", re.DOTALL)
_RE_SNIPPET_INCLUDE = re.compile(r"--8<--\s*\"[^\"]*\"")
_RE_ADMONITION = re.compile(r"^!!!?\s+\w+.*$", re.MULTILINE)
_RE_ANNOTATION = re.compile(r"\[\(c\)\.\]|\[\(c\)\]")


def _strip_mkdocs_syntax(text: str) -> str:
    """Remove MkDocs-Material / Jinja2 boilerplate from markdown."""
    text = _RE_FRONTMATTER.sub("", text)
    text = _RE_JINJA_BLOCK.sub("", text)
    text = _RE_JINJA_EXPR.sub("", text)
    text = _RE_SNIPPET_INCLUDE.sub("", text)
    text = _RE_ADMONITION.sub("", text)
    text = _RE_ANNOTATION.sub("", text)
    return text.strip()


# ---------- Category derivation ----------

_KNOWN_CATEGORIES = {
    "controls",
    "types",
    "services",
    "cookbook",
    "cli",
    "getting-started",
    "tutorials",
    "publish",
    "reference",
    "charts",
    "extend",
    "fastapi",
}


def _derive_category(rel_path: str) -> str:
    """Derive a doc category from the first path component."""
    parts = Path(rel_path).parts
    if parts:
        first = parts[0].lower()
        if first in _KNOWN_CATEGORIES:
            return first
    return "other"


# ---------- Section splitting ----------


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown text by ## headings. Returns [(heading, body), ...]."""
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_heading or current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading or current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return sections


def _extract_title(text: str, filename: str) -> str:
    """Extract title from first # heading or use filename."""
    for line in text.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return filename.replace(".md", "").replace("-", " ").replace("_", " ").title()


# ---------- Main indexer ----------


def index_docs(conn: sqlite3.Connection, docs_root: str | Path) -> int:
    """Walk docs_root and insert all .md files into docs_fts. Returns count."""
    docs_root = Path(docs_root)
    count = 0

    for md_file in sorted(docs_root.rglob("*.md")):
        raw = md_file.read_text(encoding="utf-8", errors="replace")
        cleaned = _strip_mkdocs_syntax(raw)
        if not cleaned:
            continue

        rel_path = md_file.relative_to(docs_root).as_posix()
        category = _derive_category(rel_path)
        title = _extract_title(cleaned, md_file.stem)

        sections = _split_sections(cleaned)
        if not sections:
            sections = [("", cleaned)]

        for heading, body in sections:
            if not body.strip():
                continue
            section_title = f"{title} - {heading}" if heading else title
            conn.execute(
                "INSERT INTO docs_fts (title, content, path, category, section) "
                "VALUES (?, ?, ?, ?, ?)",
                (section_title, body, rel_path, category, heading),
            )
            count += 1

    conn.commit()
    return count
