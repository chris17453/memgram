"""Memgram MCP server — AI Memory Graph.

Stdio-based MCP server that provides persistent memory for AI assistants.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .db import create_db
from .tools import register_all


def create_server(db_path: str | Path | None = None, embedding_dim: int = 384) -> tuple[Server, any]:
    """Create and configure the memgram MCP server."""
    server = Server("memgram")
    db = create_db("sqlite", db_path=db_path, embedding_dim=embedding_dim)
    register_all(server, db)
    return server, db


async def run_stdio(db_path: str | Path | None = None, embedding_dim: int = 384) -> None:
    """Run the memgram MCP server over stdio."""
    server, db = create_server(db_path=db_path, embedding_dim=embedding_dim)
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        db.close()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Memgram — AI Memory Graph MCP Server")
    parser.add_argument(
        "--db-path",
        type=str,
        default=os.environ.get("MEMGRAM_DB_PATH"),
        help="Path to SQLite database (default: ~/.memgram/memgram.db)",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=int(os.environ.get("MEMGRAM_EMBEDDING_DIM", "384")),
        help="Embedding vector dimensions (default: 384 for all-MiniLM-L6-v2)",
    )
    args = parser.parse_args()
    asyncio.run(run_stdio(db_path=args.db_path, embedding_dim=args.embedding_dim))


if __name__ == "__main__":
    main()
