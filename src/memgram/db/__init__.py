"""Memgram database layer.

Usage:
    from memgram.db import create_db

    db = create_db("sqlite")                        # default ~/.memgram/memgram.db
    db = create_db("sqlite", db_path="/tmp/test.db") # custom path
    # Future: db = create_db("postgres", dsn="...")
"""

from __future__ import annotations

from typing import Any

from .base import DatabaseBackend, MemgramDB


def create_db(backend: str = "sqlite", **kwargs: Any) -> MemgramDB:
    """Factory to create a MemgramDB with the specified backend.

    Args:
        backend: "sqlite" (default). Future: "postgres", "mssql".
        **kwargs: Passed to the backend constructor.

    Returns:
        A ready-to-use MemgramDB instance.
    """
    if backend == "sqlite":
        from .sqlite import SQLiteBackend
        return MemgramDB(SQLiteBackend(**kwargs))
    else:
        raise ValueError(f"Unknown backend: {backend!r}. Available: sqlite")


__all__ = ["create_db", "MemgramDB", "DatabaseBackend"]
