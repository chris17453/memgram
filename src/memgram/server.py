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
    export_parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Export only a specific project (default: all)",
    )

    # -- export-web --
    export_web_parser = subparsers.add_parser(
        "export-web",
        help="Export database as a navigable Jekyll website (GitHub Pages ready)",
    )
    export_web_parser.add_argument(
        "-o", "--output",
        type=str,
        default="memgram-web",
        help="Output directory (default: memgram-web)",
    )
    export_web_parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Export only a specific project (default: all)",
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
    proj_merge_parser.add_argument("--from", dest="from_project", type=str, required=True, help="Source project name")
    proj_merge_parser.add_argument("--to", dest="to_project", type=str, required=True, help="Target project name")
    proj_merge_parser.add_argument(
        "--db-path",
        type=str,
        default=default_db,
        help=f"Path to SQLite database (default: {default_db})",
    )

    stats_parser = subparsers.add_parser(
        "agent-stats",
        help="Show contribution statistics broken down by AI agent type and model",
    )
    stats_parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Filter stats to a specific project (optional)",
    )

    seed_parser = subparsers.add_parser(
        "seed-instructions",
        help="Seed instructions from a markdown file into the database",
    )
    seed_parser.add_argument(
        "-f", "--file",
        type=str,
        default="INSTRUCTIONS.md",
        help="Path to instructions markdown file (default: INSTRUCTIONS.md)",
    )
    seed_parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Scope instructions to a specific project (default: global)",
    )
    seed_parser.add_argument(
        "--scope",
        type=str,
        choices=["global", "project", "branch"],
        default="global",
        help="Instruction scope (default: global)",
    )
    seed_parser.add_argument(
        "--replace",
        action="store_true",
        help="Deactivate existing instructions in this scope before seeding",
    )

    proj_rename_parser = subparsers.add_parser(
        "rename-project",
        help="Rename a project to a new name (merges if the target already exists).",
    )
    proj_rename_parser.add_argument("--from", dest="from_project", type=str, required=True, help="Project to rename")
    proj_rename_parser.add_argument("--to", dest="to_project", type=str, required=True, help="New project name")
    proj_rename_parser.add_argument(
        "--db-path",
        type=str,
        default=default_db,
        help=f"Path to SQLite database (default: {default_db})",
    )

    args = parser.parse_args()

    if args.command == "export":
        from .export import export_markdown
        from .utils import normalize_name
        project = normalize_name(args.project) if args.project else None
        out_path, count = export_markdown(db_path=args.db_path, output_dir=args.output, project=project)
        print(f"Exported {count} files to {out_path.resolve()}")
    elif args.command == "export-web":
        from .export import export_html
        from .utils import normalize_name
        project = normalize_name(args.project) if args.project else None
        out_path, count = export_html(db_path=args.db_path, output_dir=args.output, project=project)
        print(f"Exported {count} HTML files to {out_path.resolve()}")
        print(f"\nReady to browse — no build step needed:")
        print(f"  python -m http.server -d {out_path.resolve()}")
        print(f"  # or just open {out_path.resolve()}/index.html")
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
    elif args.command == "agent-stats":
        from .utils import normalize_name
        db = create_db("sqlite", db_path=args.db_path)
        try:
            project = normalize_name(args.project) if args.project else None
            stats = db.get_agent_stats(project=project)
            if not stats["agents"]:
                print("No agent data found.")
            else:
                header = f"{'Agent Type':<16} {'Model':<28} {'Sessions':>8} {'Thoughts':>8} {'Rules':>6} {'Errors':>6}  First Seen"
                print(header)
                print("-" * len(header))
                for a in stats["agents"]:
                    print(
                        f"{(a['agent_type'] or '?'):<16} "
                        f"{(a['agent_model'] or '?'):<28} "
                        f"{a['sessions']:>8} {a['thoughts']:>8} {a['rules']:>6} {a['errors']:>6}  "
                        f"{(a['first_seen'] or '')[:10]}"
                    )
                print(f"\nTotal agents: {stats['totals']['total_agents']}")
        finally:
            db.close()
    elif args.command == "seed-instructions":
        import re
        from pathlib import Path
        from .utils import normalize_name

        md_path = Path(args.file)
        if not md_path.exists():
            print(f"Error: File not found: {md_path}")
            return

        text = md_path.read_text()
        # Split on ## headings (level 2)
        sections = re.split(r'^## ', text, flags=re.MULTILINE)
        # First chunk is preamble (before first ##)
        preamble = sections[0].strip()
        section_list = []
        for chunk in sections[1:]:
            lines = chunk.split('\n', 1)
            heading = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            slug = re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-')
            section_list.append((slug, heading, body))

        db = create_db("sqlite", db_path=args.db_path)
        try:
            project = normalize_name(args.project) if args.project else None
            scope = args.scope

            if args.replace:
                # Deactivate existing instructions in this scope
                db.backend.execute(
                    "UPDATE instructions SET active=0 WHERE scope=? AND COALESCE(project,'')=?",
                    (scope, project or ''),
                )

            # Seed preamble as "overview" section
            if preamble:
                # Strip the title line (# Title)
                preamble_body = re.sub(r'^#\s+.*\n*', '', preamble).strip()
                if preamble_body:
                    db.create_instruction(
                        section="overview", title="Overview", content=preamble_body,
                        position=0, scope=scope, project=project,
                    )

            for i, (slug, heading, body) in enumerate(section_list):
                db.create_instruction(
                    section=slug, title=heading, content=body,
                    position=i + 1, scope=scope, project=project,
                )

            total = len(section_list) + (1 if preamble else 0)
            print(f"Seeded {total} instruction sections from {md_path}")
            if project:
                print(f"  Scope: {scope}, project: {project}")
            else:
                print(f"  Scope: {scope}")
        finally:
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
