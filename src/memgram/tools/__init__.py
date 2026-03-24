"""Memgram MCP tool modules."""

from __future__ import annotations

from mcp.server import Server
from mcp.types import Tool

from ..db import MemgramDB
from . import components, features, health, knowledge, people, plans, search, sessions, specs, teams

ALL_TOOLS: list[Tool] = (
    sessions.TOOLS + knowledge.TOOLS + search.TOOLS + plans.TOOLS
    + specs.TOOLS + features.TOOLS + components.TOOLS + people.TOOLS
    + teams.TOOLS + health.TOOLS
)


def register_all(server: Server, db: MemgramDB) -> None:
    """Register all memgram tools with the MCP server.

    Only one call_tool handler can be active, so we merge into a single dispatcher.
    """
    import json
    from mcp.types import TextContent

    tool_handlers = {}

    # Build a name→(module, handler_factory) map
    for mod in (sessions, knowledge, search, plans, specs, features, components, people, teams, health):
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
            return _json_result({
                "session": session,
                "resume_context": resume,
                "_instructions": (
                    f"Session started. Your session_id is: {session['id']}. "
                    "You MUST pass this session_id to every add_thought, add_rule, and "
                    "add_error_pattern call for proper attribution tracking."
                ),
            })
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
        # Warn (but don't block) if session_id is missing — agents must call start_session first
        _session_warning = None
        if name in ("add_thought", "add_rule", "add_error_pattern") and not args.get("session_id"):
            _session_warning = (
                "WARNING: No session_id provided. This item will have no session link or agent attribution. "
                "Call start_session first and pass the returned session ID to all add_thought/add_rule/add_error_pattern calls."
            )
        if name == "add_thought":
            result = db.add_thought(
                summary=args["summary"], content=args.get("content", ""),
                type=args.get("type", "note"), session_id=args.get("session_id"),
                project=args.get("project"), branch=args.get("branch"),
                agent_type=args.get("agent_type"), agent_model=args.get("agent_model"),
                keywords=args.get("keywords"),
                associated_files=args.get("associated_files"),
                pinned=args.get("pinned", False),
            )
            if _session_warning:
                result = {"_warning": _session_warning, **result}
            return _json_result(result)
        elif name == "update_thought":
            fields = {k: v for k, v in args.items() if k != "thought_id"}
            if "pinned" in fields:
                fields["pinned"] = 1 if fields["pinned"] else 0
            if "archived" in fields:
                fields["archived"] = 1 if fields["archived"] else 0
            return _json_result(db.update_thought(args["thought_id"], **fields))
        elif name == "add_rule":
            result = db.add_rule(
                summary=args["summary"], content=args.get("content", ""),
                type=args["type"], severity=args["severity"],
                condition=args.get("condition"), session_id=args.get("session_id"),
                project=args.get("project"), branch=args.get("branch"),
                agent_type=args.get("agent_type"), agent_model=args.get("agent_model"),
                keywords=args.get("keywords"),
                associated_files=args.get("associated_files"),
                pinned=args.get("pinned", False),
            )
            if _session_warning:
                result = {"_warning": _session_warning, **result}
            return _json_result(result)
        elif name == "reinforce_rule":
            return _json_result(db.reinforce_rule(args["rule_id"], note=args.get("note")))
        elif name == "add_error_pattern":
            result = db.add_error_pattern(
                error_description=args["error_description"], cause=args.get("cause"),
                fix=args.get("fix"), prevention_rule_id=args.get("prevention_rule_id"),
                session_id=args.get("session_id"), project=args.get("project"),
                branch=args.get("branch"),
                agent_type=args.get("agent_type"), agent_model=args.get("agent_model"),
                keywords=args.get("keywords"), associated_files=args.get("associated_files"),
            )
            if _session_warning:
                result = {"_warning": _session_warning, **result}
            return _json_result(result)
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

    # ── Plans / Task Tracking ────────────────────────────────────────────
    elif mod is plans:
        if name == "create_plan":
            result = db.create_plan(
                title=args["title"], description=args.get("description", ""),
                scope=args.get("scope", "project"), priority=args.get("priority", "medium"),
                session_id=args.get("session_id"), project=args.get("project"),
                branch=args.get("branch"), due_date=args.get("due_date"),
                tags=args.get("tags"),
            )
            return _json_result(result)
        elif name == "update_plan":
            fields = {k: v for k, v in args.items() if k != "plan_id"}
            return _json_result(db.update_plan(args["plan_id"], **fields))
        elif name == "get_plan":
            plan = db.get_plan(args["plan_id"])
            return _json_result(plan or {"error": f"Plan not found: {args['plan_id']}"})
        elif name == "list_plans":
            result = db.list_plans(
                project=args.get("project"), branch=args.get("branch"),
                session_id=args.get("session_id"), status=args.get("status"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "plans": result})
        elif name == "add_plan_task":
            result = db.add_plan_task(
                plan_id=args["plan_id"], title=args["title"],
                description=args.get("description", ""),
                assignee=args.get("assignee"), depends_on=args.get("depends_on"),
                position=args.get("position"),
            )
            return _json_result(result)
        elif name == "update_plan_task":
            fields = {k: v for k, v in args.items() if k != "task_id"}
            return _json_result(db.update_plan_task(args["task_id"], **fields))
        elif name == "delete_plan_task":
            deleted = db.delete_plan_task(args["task_id"])
            return _json_result({"deleted": deleted, "task_id": args["task_id"]})

    # ── Specs ────────────────────────────────────────────────────────────
    elif mod is specs:
        if name == "create_spec":
            return _json_result(db.create_spec(
                title=args["title"], description=args.get("description", ""),
                status=args.get("status", "draft"), priority=args.get("priority", "medium"),
                acceptance_criteria=args.get("acceptance_criteria"),
                project=args.get("project"), branch=args.get("branch"),
                session_id=args.get("session_id"), author_id=args.get("author_id"),
                tags=args.get("tags"),
            ))
        elif name == "update_spec":
            fields = {k: v for k, v in args.items() if k != "spec_id"}
            return _json_result(db.update_spec(args["spec_id"], **fields))
        elif name == "get_spec":
            spec = db.get_spec(args["spec_id"])
            return _json_result(spec or {"error": f"Spec not found: {args['spec_id']}"})
        elif name == "list_specs":
            result = db.list_specs(
                project=args.get("project"), branch=args.get("branch"),
                status=args.get("status"), limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "specs": result})

    # ── Features ─────────────────────────────────────────────────────────
    elif mod is features:
        if name == "create_feature":
            return _json_result(db.create_feature(
                name=args["name"], description=args.get("description", ""),
                status=args.get("status", "proposed"), priority=args.get("priority", "medium"),
                spec_id=args.get("spec_id"),
                project=args.get("project"), branch=args.get("branch"),
                session_id=args.get("session_id"), lead_id=args.get("lead_id"),
                tags=args.get("tags"),
            ))
        elif name == "update_feature":
            fields = {k: v for k, v in args.items() if k != "feature_id"}
            return _json_result(db.update_feature(args["feature_id"], **fields))
        elif name == "get_feature":
            feat = db.get_feature(args["feature_id"])
            return _json_result(feat or {"error": f"Feature not found: {args['feature_id']}"})
        elif name == "list_features":
            result = db.list_features(
                project=args.get("project"), branch=args.get("branch"),
                status=args.get("status"), spec_id=args.get("spec_id"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "features": result})

    # ── Components ───────────────────────────────────────────────────────
    elif mod is components:
        if name == "create_component":
            return _json_result(db.create_component(
                name=args["name"], description=args.get("description", ""),
                type=args.get("type", "module"),
                project=args.get("project"), branch=args.get("branch"),
                owner_id=args.get("owner_id"),
                tech_stack=args.get("tech_stack"), tags=args.get("tags"),
            ))
        elif name == "update_component":
            fields = {k: v for k, v in args.items() if k != "component_id"}
            return _json_result(db.update_component(args["component_id"], **fields))
        elif name == "get_component":
            comp = db.get_component(args["component_id"])
            return _json_result(comp or {"error": f"Component not found: {args['component_id']}"})
        elif name == "list_components":
            result = db.list_components(
                project=args.get("project"), branch=args.get("branch"),
                type=args.get("type"), owner_id=args.get("owner_id"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "components": result})

    # ── People ───────────────────────────────────────────────────────────
    elif mod is people:
        if name == "add_person":
            return _json_result(db.add_person(
                name=args["name"], type=args.get("type", "individual"),
                role=args.get("role", ""),
                email=args.get("email"), github=args.get("github"),
                skills=args.get("skills"), notes=args.get("notes", ""),
            ))
        elif name == "update_person":
            fields = {k: v for k, v in args.items() if k != "person_id"}
            return _json_result(db.update_person(args["person_id"], **fields))
        elif name == "get_person":
            person = db.get_person(args["person_id"])
            return _json_result(person or {"error": f"Person not found: {args['person_id']}"})
        elif name == "list_people":
            result = db.list_people(
                role=args.get("role"), limit=args.get("limit", 100),
            )
            return _json_result({"count": len(result), "people": result})

    # ── Teams ────────────────────────────────────────────────────────────
    elif mod is teams:
        if name == "create_team":
            return _json_result(db.create_team(
                name=args["name"], description=args.get("description", ""),
                project=args.get("project"), lead_id=args.get("lead_id"),
                tags=args.get("tags"),
            ))
        elif name == "update_team":
            fields = {k: v for k, v in args.items() if k != "team_id"}
            return _json_result(db.update_team(args["team_id"], **fields))
        elif name == "get_team":
            team = db.get_team(args["team_id"])
            return _json_result(team or {"error": f"Team not found: {args['team_id']}"})
        elif name == "list_teams":
            result = db.list_teams(
                project=args.get("project"), limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "teams": result})
        elif name == "add_team_member":
            return _json_result(db.add_team_member(
                team_id=args["team_id"], person_id=args["person_id"],
                role=args.get("role", "member"),
            ))
        elif name == "remove_team_member":
            removed = db.remove_team_member(args["team_id"], args["person_id"])
            return _json_result({"removed": removed})

    # ── Health / Diagnostics / Reporting ──────────────────────────────────
    elif mod is health:
        if name == "get_health":
            diagnostics = db.health()
            if not args.get("include_counts", True):
                diagnostics = {k: v for k, v in diagnostics.items() if k != "counts"}
            return _json_result(diagnostics)
        elif name == "get_agent_stats":
            return _json_result(db.get_agent_stats(project=args.get("project")))

    return _json_result({"error": f"Unknown tool: {name}"})
