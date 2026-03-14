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

    migrate_parser = subparsers.add_parser(
        "migrate-exports",
        help="Rename legacy ID-named export files to slug filenames and fix links",
    )
    migrate_parser.add_argument(
        "-i", "--input",
        type=str,
        default="memgram-export",
        help="Existing export directory to migrate (default: memgram-export)",
    )

    proj_list_parser = subparsers.add_parser(
        "list-projects",
        help="List all projects with summaries and counts",
    )
    proj_list_parser.add_argument(
        "--db-path",
        type=str,
        default=default_db,
        help=f"Path to SQLite database (default: {default_db})",
    )

    proj_merge_parser = subparsers.add_parser(
        "merge-projects",
        help="Merge all data from a source project into a target project (fix typos).",
    )
    proj_merge_parser.add_argument("from_project", type=str, help="Source project name")
    proj_merge_parser.add_argument("to_project", type=str, help="Target project name")
    proj_merge_parser.add_argument(
        "--db-path",
        type=str,
        default=default_db,
        help=f"Path to SQLite database (default: {default_db})",
    )

    proj_rename_parser = subparsers.add_parser(
        "rename-project",
        help="Rename a project to a new name (merges if the target already exists).",
    )
    proj_rename_parser.add_argument("from_project", type=str, help="Project to rename")
    proj_rename_parser.add_argument("to_project", type=str, help="New project name")
    proj_rename_parser.add_argument(
        "--db-path",
        type=str,
        default=default_db,
        help=f"Path to SQLite database (default: {default_db})",
    )

    args = parser.parse_args()

    if args.command == "export":
        from .export import export_markdown
        out_path, count = export_markdown(db_path=args.db_path, output_dir=args.output)
        print(f"Exported {count} files to {out_path.resolve()}")
    elif args.command == "migrate-exports":
        from .export import rename_existing_exports
        result = rename_existing_exports(output_dir=args.input)
        print(
            f"Migrated exports in {Path(args.input).resolve()}: "
            f"{result['renamed']} files renamed, {result['updated']} files updated."
        )
    elif args.command == "list-projects":
        db = create_db("sqlite", db_path=args.db_path)
        try:
            projects = db.list_projects()
            if not projects:
                print("No projects found.")
            else:
                for ps in projects:
                    print(f"{ps['project']}: sessions={ps['total_sessions']}, thoughts={ps['total_thoughts']}, rules={ps['total_rules']}")
        finally:
            db.close()
    elif args.command == "merge-projects":
        db = create_db("sqlite", db_path=args.db_path)
        result = db.merge_projects(args.from_project, args.to_project)
        print(f"Merged project '{args.from_project}' into '{args.to_project}': {result['updated']}")
        db.close()
    elif args.command == "rename-project":
        db = create_db("sqlite", db_path=args.db_path)
        result = db.rename_project(args.from_project, args.to_project)
        print(f"Renamed project '{args.from_project}' to '{args.to_project}': {result['updated']}")
        db.close()
    else:
        # Default: serve (works with no subcommand or explicit "serve")
        embedding_dim = getattr(args, "embedding_dim", int(os.environ.get("MEMGRAM_EMBEDDING_DIM", "384")))
        asyncio.run(run_stdio(db_path=args.db_path, embedding_dim=embedding_dim))


if __name__ == "__main__":
    main()
