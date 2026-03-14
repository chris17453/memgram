"""Search, retrieval, grouping, and maintenance MCP tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..db import MemgramDB

TOOLS = [
    # ── Search ──────────────────────────────────────────────────────────
    Tool(
        name="search",
        description=(
            "Unified full-text search across thoughts, rules, error patterns, and session summaries. "
            "Results are ranked by relevance (text match + recency + access frequency + pin status + severity)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (natural language or keywords)"},
                "project": {"type": "string", "description": "Filter by project tag"},
                "branch": {"type": "string", "description": "Filter by git branch name"},
                "type_filter": {
                    "type": "string",
                    "enum": ["thought", "rule", "error_pattern", "session_summary"],
                    "description": "Only search this type",
                },
                "include_archived": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 20, "description": "Max results to return"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="search_by_embedding",
        description=(
            "RAG-style semantic search using vector similarity. Requires embeddings to have been stored. "
            "Pass the embedding vector directly. Returns items ranked by cosine distance."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "embedding": {"type": "array", "items": {"type": "number"}, "description": "Embedding vector"},
                "project": {"type": "string"},
                "branch": {"type": "string", "description": "Filter by git branch name"},
                "type_filter": {"type": "string", "enum": ["thought", "rule", "error_pattern", "session_summary"]},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["embedding"],
        },
    ),
    Tool(
        name="store_embedding",
        description=(
            "Store a vector embedding for an item (thought, rule, error pattern, session summary). "
            "Enables semantic/RAG search for that item."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "item_id": {"type": "string", "description": "ID of the item to embed"},
                "item_type": {"type": "string", "enum": ["thought", "rule", "error_pattern", "session_summary"]},
                "text_content": {"type": "string", "description": "The text that was embedded"},
                "embedding": {"type": "array", "items": {"type": "number"}, "description": "Embedding vector"},
                "model_name": {"type": "string", "description": "Name of the embedding model used"},
            },
            "required": ["item_id", "item_type", "text_content", "embedding", "model_name"],
        },
    ),
    # ── Retrieval ───────────────────────────────────────────────────────
    Tool(
        name="get_rules",
        description=(
            "Get active rules for a project/context. Always includes critical rules. "
            "Filter by severity and keywords to get the most relevant rules."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string", "description": "Git branch name (returns branch-specific + branch-global rules)"},
                "severity": {"type": "string", "enum": ["critical", "preference", "context_dependent"]},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Filter by keyword overlap"},
                "include_global": {"type": "boolean", "default": True, "description": "Include rules with no project tag"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="get_session_history",
        description="List past sessions with summaries, ordered by most recent.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string", "description": "Filter by git branch name"},
                "agent_type": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    ),
    Tool(
        name="get_related",
        description="Get all items linked to a given thought or rule (via thought_links graph).",
        inputSchema={
            "type": "object",
            "properties": {
                "item_id": {"type": "string", "description": "ID of the item to find links for"},
            },
            "required": ["item_id"],
        },
    ),
    Tool(
        name="get_project_summary",
        description="Get the living summary for a project (overview, tech stack, patterns, goals, stats).",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
            },
            "required": ["project"],
        },
    ),
    Tool(
        name="update_project_summary",
        description="Update a project's living summary. Creates it if it doesn't exist.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "summary": {"type": "string", "description": "Updated project overview"},
                "tech_stack": {"type": "array", "items": {"type": "string"}},
                "key_patterns": {"type": "array", "items": {"type": "string"}, "description": "Coding patterns/conventions"},
                "active_goals": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["project"],
        },
    ),
    # ── Groups ──────────────────────────────────────────────────────────
    Tool(
        name="create_group",
        description="Create a named group to cluster related items (e.g., 'authentication system').",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "project": {"type": "string"},
                "branch": {"type": "string", "description": "Git branch name (optional)"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="add_to_group",
        description="Add a thought, rule, or error pattern to a group.",
        inputSchema={
            "type": "object",
            "properties": {
                "group_id": {"type": "string"},
                "item_id": {"type": "string"},
                "item_type": {"type": "string", "enum": ["thought", "rule", "error_pattern"]},
            },
            "required": ["group_id", "item_id", "item_type"],
        },
    ),
    Tool(
        name="remove_from_group",
        description="Remove an item from a group.",
        inputSchema={
            "type": "object",
            "properties": {
                "group_id": {"type": "string"},
                "item_id": {"type": "string"},
            },
            "required": ["group_id", "item_id"],
        },
    ),
    Tool(
        name="get_group",
        description="Get a group and all its member items with full details. Look up by ID or name.",
        inputSchema={
            "type": "object",
            "properties": {
                "group_id": {"type": "string"},
                "name": {"type": "string"},
                "project": {"type": "string"},
                "branch": {"type": "string", "description": "Git branch name (used with name lookup)"},
            },
        },
    ),
    # ── Maintenance ─────────────────────────────────────────────────────
    Tool(
        name="pin_item",
        description="Pin or unpin a thought or rule. Pinned items are always loaded in resume context.",
        inputSchema={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "pinned": {"type": "boolean", "default": True},
            },
            "required": ["item_id"],
        },
    ),
    Tool(
        name="archive_item",
        description="Archive a thought or rule. Archived items are excluded from search by default.",
        inputSchema={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
            },
            "required": ["item_id"],
        },
    ),
    Tool(
        name="merge_projects",
        description="Merge all data from a source project into a target project (fix typos).",
        inputSchema={
            "type": "object",
            "properties": {
                "from_project": {"type": "string", "description": "Source project name to merge from"},
                "to_project": {"type": "string", "description": "Target project name to merge into"},
            },
            "required": ["from_project", "to_project"],
        },
    ),
]


def _json_result(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def register(server: Server, db: MemgramDB) -> None:
    """Register search, retrieval, grouping, and maintenance tools."""

    @server.call_tool()
    async def _handle(name: str, arguments: dict | None) -> list[TextContent]:
        args = arguments or {}

        # ── Search ──────────────────────────────────────────────────────
        if name == "search":
            results = db.search(
                query=args["query"],
                project=args.get("project"),
                type_filter=args.get("type_filter"),
                include_archived=args.get("include_archived", False),
                limit=args.get("limit", 20),
            )
            return _json_result({"count": len(results), "results": results})

        elif name == "search_by_embedding":
            has_embeddings = db.backend.has_embeddings()
            results = db.search_by_embedding(
                embedding=args["embedding"],
                project=args.get("project"),
                type_filter=args.get("type_filter"),
                limit=args.get("limit", 20),
            )
            return _json_result({
                "count": len(results),
                "results": results,
                "vec_enabled": getattr(db.backend, "vec_enabled", None),
                "has_embeddings": has_embeddings,
            })

        elif name == "store_embedding":
            try:
                db.store_embedding(
                    item_id=args["item_id"],
                    item_type=args["item_type"],
                    text_content=args["text_content"],
                    embedding=args["embedding"],
                    model_name=args["model_name"],
                )
                return _json_result({"status": "stored", "item_id": args["item_id"]})
            except RuntimeError as exc:
                return _json_result({
                    "status": "failed",
                    "error": str(exc),
                    "vec_enabled": getattr(db.backend, "vec_enabled", None),
                })

        # ── Retrieval ───────────────────────────────────────────────────
        elif name == "get_rules":
            rules = db.get_rules(
                project=args.get("project"),
                severity=args.get("severity"),
                keywords=args.get("keywords"),
                include_global=args.get("include_global", True),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(rules), "rules": rules})

        elif name == "get_session_history":
            sessions = db.list_sessions(
                project=args.get("project"),
                agent_type=args.get("agent_type"),
                limit=args.get("limit", 20),
            )
            return _json_result({"count": len(sessions), "sessions": sessions})

        elif name == "get_related":
            links = db.get_related(args["item_id"])
            return _json_result({"count": len(links), "links": links})

        elif name == "get_project_summary":
            ps = db.get_project_summary(args["project"])
            return _json_result(ps or {"error": f"No summary found for project '{args['project']}'."})

        elif name == "update_project_summary":
            ps = db.update_project_summary(
                project=args["project"],
                summary=args.get("summary"),
                tech_stack=args.get("tech_stack"),
                key_patterns=args.get("key_patterns"),
                active_goals=args.get("active_goals"),
            )
            return _json_result(ps)

        # ── Groups ──────────────────────────────────────────────────────
        elif name == "create_group":
            g = db.create_group(
                name=args["name"],
                description=args.get("description", ""),
                project=args.get("project"),
            )
            return _json_result(g)

        elif name == "add_to_group":
            result = db.add_to_group(args["group_id"], args["item_id"], args["item_type"])
            return _json_result(result)

        elif name == "remove_from_group":
            ok = db.remove_from_group(args["group_id"], args["item_id"])
            return _json_result({"removed": ok})

        elif name == "get_group":
            g = db.get_group(
                group_id=args.get("group_id"),
                name=args.get("name"),
                project=args.get("project"),
            )
            return _json_result(g or {"error": "Group not found"})

        # ── Maintenance ─────────────────────────────────────────────────
        elif name == "pin_item":
            result = db.pin_item(args["item_id"], pinned=args.get("pinned", True))
            return _json_result(result or {"error": "Item not found"})

        elif name == "archive_item":
            result = db.archive_item(args["item_id"])
            return _json_result(result or {"error": "Item not found"})

        elif name == "merge_projects":
            result = db.merge_projects(args["from_project"], args["to_project"])
            return _json_result(result)

        return _json_result({"error": f"Unknown tool: {name}"})
