"""Memgram MCP tool modules."""

from __future__ import annotations

from mcp.server import Server
from mcp.types import Tool

from ..db import MemgramDB
from . import health, knowledge, search, sessions

ALL_TOOLS: list[Tool] = sessions.TOOLS + knowledge.TOOLS + search.TOOLS + health.TOOLS


def register_all(server: Server, db: MemgramDB) -> None:
    """Register all memgram tools with the MCP server.

    Only one call_tool handler can be active, so we merge into a single dispatcher.
    """
    import json
    from mcp.types import TextContent

    tool_handlers = {}

    # Build a name→(module, handler_factory) map
    for mod in (sessions, knowledge, search, health):
        for tool in mod.TOOLS:
            tool_handlers[tool.name] = mod

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return ALL_TOOLS

    @server.call_tool()
    async def _dispatch(name: str, arguments: dict | None) -> list[TextContent]:
        mod = tool_handlers.get(name)
        if not mod:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
        # Each module has a _handle-style function; call the module's dispatch logic
        return await _call_module_handler(mod, name, arguments, db)


async def _call_module_handler(mod, name: str, arguments: dict | None, db: MemgramDB):
    """Dispatch a tool call to the appropriate module handler."""
    import json
    from mcp.types import TextContent
    from ..utils import normalize_name

    args = arguments or {}

    # Normalize project names and keywords so variant spellings always match.
    # e.g. 'oxide-os', 'oxide_os', 'OxideOS' all become 'oxideos'.
    if "project" in args and args["project"] is not None:
        args["project"] = normalize_name(args["project"])
    if "branch" in args and args["branch"] is not None:
        args["branch"] = normalize_name(args["branch"])
    if "keywords" in args and isinstance(args["keywords"], list):
        args["keywords"] = [normalize_name(k) for k in args["keywords"]]
    if "name" in args and args["name"] is not None and name in ("create_group", "get_group"):
        args["name"] = normalize_name(args["name"])
    if "from_project" in args and args["from_project"] is not None:
        args["from_project"] = normalize_name(args["from_project"])
    if "to_project" in args and args["to_project"] is not None:
        args["to_project"] = normalize_name(args["to_project"])

    def _json_result(data):
        return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]

    # ── Sessions ────────────────────────────────────────────────────────
    if mod is sessions:
        if name == "start_session":
            session = db.create_session(
                agent_type=args["agent_type"], model=args["model"],
                project=args.get("project"), branch=args.get("branch"),
                goal=args.get("goal"),
            )
            resume = db.get_resume_context(project=args.get("project"), branch=args.get("branch"))
            return _json_result({"session": session, "resume_context": resume})
        elif name == "end_session":
            session = db.end_session(args["session_id"], summary=args.get("summary"))
            ss = db.add_session_summary(
                session_id=args["session_id"], project=session.get("project"),
                branch=session.get("branch"),
                goal=session.get("goal"), outcome=args.get("outcome", args.get("summary")),
                decisions_made=args.get("decisions_made"), rules_learned=args.get("rules_learned"),
                errors_encountered=args.get("errors_encountered"),
                files_modified=args.get("files_modified"),
                unresolved_items=args.get("unresolved_items"),
                next_session_hints=args.get("next_session_hints"),
            )
            if session.get("project"):
                db.update_project_summary(session["project"])
            return _json_result({"session": session, "session_summary": ss})
        elif name == "save_snapshot":
            snapshot = db.save_snapshot(
                session_id=args["session_id"], current_goal=args.get("current_goal"),
                progress_summary=args.get("progress_summary"),
                open_questions=args.get("open_questions"), blockers=args.get("blockers"),
                next_steps=args.get("next_steps"), active_files=args.get("active_files"),
                key_decisions=args.get("key_decisions"),
            )
            return _json_result(snapshot)
        elif name == "get_resume_context":
            return _json_result(db.get_resume_context(project=args.get("project"), branch=args.get("branch")))

    # ── Knowledge ───────────────────────────────────────────────────────
    elif mod is knowledge:
        if name == "add_thought":
            return _json_result(db.add_thought(
                summary=args["summary"], content=args.get("content", ""),
                type=args.get("type", "note"), session_id=args.get("session_id"),
                project=args.get("project"), branch=args.get("branch"),
                keywords=args.get("keywords"),
                associated_files=args.get("associated_files"),
                pinned=args.get("pinned", False),
            ))
        elif name == "update_thought":
            fields = {k: v for k, v in args.items() if k != "thought_id"}
            if "pinned" in fields:
                fields["pinned"] = 1 if fields["pinned"] else 0
            if "archived" in fields:
                fields["archived"] = 1 if fields["archived"] else 0
            return _json_result(db.update_thought(args["thought_id"], **fields))
        elif name == "add_rule":
            return _json_result(db.add_rule(
                summary=args["summary"], content=args.get("content", ""),
                type=args["type"], severity=args["severity"],
                condition=args.get("condition"), session_id=args.get("session_id"),
                project=args.get("project"), branch=args.get("branch"),
                keywords=args.get("keywords"),
                associated_files=args.get("associated_files"),
                pinned=args.get("pinned", False),
            ))
        elif name == "reinforce_rule":
            return _json_result(db.reinforce_rule(args["rule_id"], note=args.get("note")))
        elif name == "add_error_pattern":
            return _json_result(db.add_error_pattern(
                error_description=args["error_description"], cause=args.get("cause"),
                fix=args.get("fix"), prevention_rule_id=args.get("prevention_rule_id"),
                session_id=args.get("session_id"), project=args.get("project"),
                branch=args.get("branch"),
                keywords=args.get("keywords"), associated_files=args.get("associated_files"),
            ))
        elif name == "link_items":
            return _json_result(db.link_items(
                from_id=args["from_id"], from_type=args["from_type"],
                to_id=args["to_id"], to_type=args["to_type"],
                link_type=args.get("link_type", "related"),
            ))

    # ── Search / Retrieval / Groups / Maintenance ───────────────────────
    elif mod is search:
        if name == "search":
            results = db.search(
                query=args["query"], project=args.get("project"),
                branch=args.get("branch"),
                type_filter=args.get("type_filter"),
                include_archived=args.get("include_archived", False),
                limit=args.get("limit", 20),
            )
            return _json_result({"count": len(results), "results": results})
        elif name == "search_by_embedding":
            results = db.search_by_embedding(
                embedding=args["embedding"], project=args.get("project"),
                branch=args.get("branch"),
                type_filter=args.get("type_filter"), limit=args.get("limit", 20),
            )
            return _json_result({"count": len(results), "results": results})
        elif name == "store_embedding":
            db.store_embedding(
                item_id=args["item_id"], item_type=args["item_type"],
                text_content=args["text_content"], embedding=args["embedding"],
                model_name=args["model_name"],
            )
            return _json_result({"status": "stored", "item_id": args["item_id"]})
        elif name == "get_rules":
            rules = db.get_rules(
                project=args.get("project"), branch=args.get("branch"),
                severity=args.get("severity"),
                keywords=args.get("keywords"),
                include_global=args.get("include_global", True),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(rules), "rules": rules})
        elif name == "get_session_history":
            ss = db.list_sessions(
                project=args.get("project"), branch=args.get("branch"),
                agent_type=args.get("agent_type"),
                limit=args.get("limit", 20),
            )
            return _json_result({"count": len(ss), "sessions": ss})
        elif name == "get_related":
            links = db.get_related(args["item_id"])
            return _json_result({"count": len(links), "links": links})
        elif name == "get_project_summary":
            ps = db.get_project_summary(args["project"])
            return _json_result(ps or {"error": f"No summary for project '{args['project']}'"})
        elif name == "update_project_summary":
            return _json_result(db.update_project_summary(
                project=args["project"], summary=args.get("summary"),
                tech_stack=args.get("tech_stack"), key_patterns=args.get("key_patterns"),
                active_goals=args.get("active_goals"),
            ))
        elif name == "create_group":
            return _json_result(db.create_group(
                name=args["name"], description=args.get("description", ""),
                project=args.get("project"), branch=args.get("branch"),
            ))
        elif name == "add_to_group":
            return _json_result(db.add_to_group(args["group_id"], args["item_id"], args["item_type"]))
        elif name == "remove_from_group":
            return _json_result({"removed": db.remove_from_group(args["group_id"], args["item_id"])})
        elif name == "get_group":
            g = db.get_group(group_id=args.get("group_id"), name=args.get("name"), project=args.get("project"), branch=args.get("branch"))
            return _json_result(g or {"error": "Group not found"})
        elif name == "pin_item":
            result = db.pin_item(args["item_id"], pinned=args.get("pinned", True))
            return _json_result(result or {"error": "Item not found"})
        elif name == "archive_item":
            result = db.archive_item(args["item_id"])
            return _json_result(result or {"error": "Item not found"})

        elif name == "merge_projects":
            result = db.merge_projects(args["from_project"], args["to_project"])
            return _json_result(result)

    # ── Health / Diagnostics ─────────────────────────────────────────────
    elif mod is health:
        if name == "get_health":
            diagnostics = db.health()
            if not args.get("include_counts", True):
                diagnostics = {k: v for k, v in diagnostics.items() if k != "counts"}
            return _json_result(diagnostics)

    return _json_result({"error": f"Unknown tool: {name}"})
