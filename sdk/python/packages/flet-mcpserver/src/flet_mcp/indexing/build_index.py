"""Orchestrate building the full index database."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from flet_mcp.indexing.db import create_database

logger = logging.getLogger(__name__)


def build_index(
    output_path: str | Path,
    docs_root: str | Path | None = None,
    examples_root: str | Path | None = None,
    schema_classes: list[type] | None = None,
    schema_base_cls: type | None = None,
    flet_version: str = "",
) -> Path:
    """Build the full index database. Each indexer is optional and errors are non-fatal."""
    output_path = Path(output_path)
    conn = create_database(output_path)

    doc_count = 0
    example_count = 0
    schema_count = 0

    # Index docs
    if docs_root and Path(docs_root).is_dir():
        try:
            from flet_mcp.indexing.docs_indexer import index_docs

            doc_count = index_docs(conn, docs_root)
            logger.info("Indexed %d doc sections", doc_count)
        except Exception:
            logger.exception("Failed to index docs")

    # Index examples
    if examples_root and Path(examples_root).is_dir():
        try:
            from flet_mcp.indexing.examples_indexer import index_examples

            example_count = index_examples(conn, examples_root)
            logger.info("Indexed %d examples", example_count)
        except Exception:
            logger.exception("Failed to index examples")

    # Index schemas
    try:
        from flet_mcp.indexing.schema_extractor import index_schemas

        schema_count = index_schemas(conn, schema_classes, schema_base_cls)
        logger.info("Indexed %d control schemas", schema_count)
    except Exception:
        logger.exception("Failed to index schemas")

    # Write metadata
    for key, value in [
        ("flet_version", flet_version),
        ("doc_count", str(doc_count)),
        ("example_count", str(example_count)),
        ("schema_count", str(schema_count)),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()
    conn.close()

    logger.info(
        "Index built: %d docs, %d examples, %d schemas → %s",
        doc_count,
        example_count,
        schema_count,
        output_path,
    )
    return output_path
