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
from .db.sqlite import DEFAULT_DB_PATH
from .tools import register_all


def _resolve_db_path() -> str:
    """Resolve the default db path from env or the built-in default."""
    return os.environ.get("MEMGRAM_DB_PATH", str(DEFAULT_DB_PATH))


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
    """CLI entry point with subcommands."""
    default_db = _resolve_db_path()

    parser = argparse.ArgumentParser(
        description="Memgram — AI Memory Graph MCP Server",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=default_db,
        help=f"Path to SQLite database (default: {default_db})",
    )
    subparsers = parser.add_subparsers(dest="command")

    # -- serve (default) --
    serve_parser = subparsers.add_parser("serve", help="Run the MCP server over stdio (default)")
    serve_parser.add_argument(
        "--embedding-dim",
        type=int,
        default=int(os.environ.get("MEMGRAM_EMBEDDING_DIM", "384")),
        help="Embedding vector dimensions (default: 384 for all-MiniLM-L6-v2)",
    )

    # -- export --
    export_parser = subparsers.add_parser("export", help="Export database as markdown files")
    export_parser.add_argument(
        "-o", "--output",
        type=str,
        default="memgram-export",
        help="Output directory (default: memgram-export)",
    )

    args = parser.parse_args()

    if args.command == "export":
        from .export import export_markdown
        out_path, count = export_markdown(db_path=args.db_path, output_dir=args.output)
        print(f"Exported {count} files to {out_path.resolve()}")
    else:
        # Default: serve (works with no subcommand or explicit "serve")
        embedding_dim = getattr(args, "embedding_dim", int(os.environ.get("MEMGRAM_EMBEDDING_DIM", "384")))
        asyncio.run(run_stdio(db_path=args.db_path, embedding_dim=embedding_dim))


if __name__ == "__main__":
    main()
