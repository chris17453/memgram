"""Memgram MCP tool modules."""

from __future__ import annotations

from mcp.server import Server
from mcp.types import Tool

from ..db import MemgramDB
from . import (
    attachments, audit, builds, comments, components, credentials, decisions,
    dependencies, deployments, diagrams, endpoints, environments, features, health,
    incidents, instructions, knowledge, people, plans, runbooks, search,
    sessions, specs, teams, tickets,
)

ALL_TOOLS: list[Tool] = (
    sessions.TOOLS + knowledge.TOOLS + search.TOOLS + plans.TOOLS
    + specs.TOOLS + features.TOOLS + components.TOOLS + people.TOOLS
    + teams.TOOLS + health.TOOLS + instructions.TOOLS + attachments.TOOLS
    + tickets.TOOLS + endpoints.TOOLS + credentials.TOOLS + environments.TOOLS
    + deployments.TOOLS + builds.TOOLS + incidents.TOOLS + dependencies.TOOLS
    + runbooks.TOOLS + decisions.TOOLS + diagrams.TOOLS + comments.TOOLS + audit.TOOLS
)


def register_all(server: Server, db: MemgramDB) -> None:
    """Register all memgram tools with the MCP server.

    Only one call_tool handler can be active, so we merge into a single dispatcher.
    """
    import json
    from mcp.types import TextContent

    tool_handlers = {}

    # Build a name→(module, handler_factory) map
    for mod in (sessions, knowledge, search, plans, specs, features, components, people,
                teams, health, instructions, attachments, tickets, endpoints, credentials,
                environments, deployments, builds, incidents, dependencies, runbooks,
                decisions, diagrams, comments, audit):
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
    # e.g. 'oxide-os', 'oxide_os', 'OxideOS' all become 'oxide-os'.
    if "project" in args and args["project"] is not None:
        args["project"] = normalize_name(args["project"])
    if "branch" in args and args["branch"] is not None:
        args["branch"] = normalize_name(args["branch"])
    if "keywords" in args and isinstance(args["keywords"], list):
        args["keywords"] = [normalize_name(k) for k in args["keywords"]]
    if "name" in args and args["name"] is not None and name in ("create_group", "get_group"):
        args["name"] = normalize_name(args["name"])
    # NOTE: from_project / to_project are intentionally NOT normalized here.
    # merge_projects and rename_project need exact string matching to
    # distinguish entries like "oxide-os" vs "oxideos" in the database.

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

    # ── Instructions ──────────────────────────────────────────────────────
    elif mod is instructions:
        if name == "get_instructions":
            result = db.get_instructions(
                project=args.get("project"), branch=args.get("branch"),
                section=args.get("section"),
                include_global=args.get("include_global", True),
            )
            return _json_result({"count": len(result), "instructions": result})
        elif name == "create_instruction":
            return _json_result(db.create_instruction(
                section=args["section"], title=args["title"],
                content=args.get("content", ""),
                position=args.get("position"),
                priority=args.get("priority", "medium"),
                scope=args.get("scope", "global"),
                project=args.get("project"), branch=args.get("branch"),
                tags=args.get("tags"),
            ))
        elif name == "update_instruction":
            fields = {k: v for k, v in args.items() if k != "instruction_id"}
            return _json_result(db.update_instruction(args["instruction_id"], **fields))
        elif name == "list_instruction_sections":
            result = db.list_instruction_sections(
                project=args.get("project"), branch=args.get("branch"),
            )
            return _json_result({"count": len(result), "sections": result})

    # ── Tickets ────────────────────────────────────────────────────────────
    elif mod is tickets:
        if name == "create_ticket":
            return _json_result(db.create_ticket(
                title=args["title"], description=args.get("description", ""),
                status=args.get("status", "open"), priority=args.get("priority", "medium"),
                type=args.get("type", "task"), ticket_number=args.get("ticket_number"),
                assignee_id=args.get("assignee_id"), reporter_id=args.get("reporter_id"),
                project=args.get("project"), branch=args.get("branch"),
                session_id=args.get("session_id"), parent_id=args.get("parent_id"),
                tags=args.get("tags"), due_date=args.get("due_date"),
            ))
        elif name == "update_ticket":
            fields = {k: v for k, v in args.items() if k != "ticket_id"}
            return _json_result(db.update_ticket(args["ticket_id"], **fields))
        elif name == "get_ticket":
            ticket = db.get_ticket(
                ticket_id=args.get("ticket_id"),
                ticket_number=args.get("ticket_number"),
            )
            return _json_result(ticket or {"error": "Ticket not found"})
        elif name == "list_tickets":
            result = db.list_tickets(
                project=args.get("project"), branch=args.get("branch"),
                status=args.get("status"), assignee_id=args.get("assignee_id"),
                type=args.get("type"), parent_id=args.get("parent_id"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "tickets": result})

    # ── Attachments ───────────────────────────────────────────────────────
    elif mod is attachments:
        if name == "add_attachment":
            return _json_result(db.add_attachment(
                entity_id=args["entity_id"], entity_type=args["entity_type"],
                url=args["url"], label=args.get("label", ""),
                type=args.get("type", "link"), mime_type=args.get("mime_type"),
                description=args.get("description", ""),
                position=args.get("position"),
            ))
        elif name == "get_attachments":
            result = db.get_attachments(
                entity_id=args["entity_id"],
                entity_type=args.get("entity_type"),
                type_filter=args.get("type_filter"),
            )
            return _json_result({"count": len(result), "attachments": result})
        elif name == "update_attachment":
            fields = {k: v for k, v in args.items() if k != "attachment_id"}
            return _json_result(db.update_attachment(args["attachment_id"], **fields))
        elif name == "remove_attachment":
            removed = db.remove_attachment(args["attachment_id"])
            return _json_result({"removed": removed, "attachment_id": args["attachment_id"]})

    # ── Endpoints ─────────────────────────────────────────────────────────
    elif mod is endpoints:
        if name == "create_endpoint":
            return _json_result(db.create_endpoint(
                path=args["path"], project=args.get("project"),
                method=args.get("method", "GET"), base_url=args.get("base_url", ""),
                description=args.get("description", ""), auth_type=args.get("auth_type", "none"),
                rate_limit=args.get("rate_limit"), request_schema=args.get("request_schema"),
                response_schema=args.get("response_schema"), status=args.get("status", "active"),
                branch=args.get("branch"), tags=args.get("tags"),
            ))
        elif name == "update_endpoint":
            fields = {k: v for k, v in args.items() if k != "endpoint_id"}
            return _json_result(db.update_endpoint(args["endpoint_id"], **fields))
        elif name == "get_endpoint":
            ep = db.get_endpoint(args["endpoint_id"])
            return _json_result(ep or {"error": f"Endpoint not found: {args['endpoint_id']}"})
        elif name == "list_endpoints":
            result = db.list_endpoints(
                project=args.get("project"), branch=args.get("branch"),
                method=args.get("method"), status=args.get("status"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "endpoints": result})

    # ── Credentials ───────────────────────────────────────────────────────
    elif mod is credentials:
        if name == "create_credential":
            return _json_result(db.create_credential(
                name=args["name"], project=args.get("project"),
                type=args.get("type", "api_key"), provider=args.get("provider", ""),
                vault_path=args.get("vault_path"), env_var=args.get("env_var"),
                description=args.get("description", ""),
                last_rotated=args.get("last_rotated"), expires_at=args.get("expires_at"),
                tags=args.get("tags"),
            ))
        elif name == "update_credential":
            fields = {k: v for k, v in args.items() if k != "credential_id"}
            return _json_result(db.update_credential(args["credential_id"], **fields))
        elif name == "get_credential":
            c = db.get_credential(args["credential_id"])
            return _json_result(c or {"error": f"Credential not found: {args['credential_id']}"})
        elif name == "list_credentials":
            result = db.list_credentials(
                project=args.get("project"), type=args.get("type"),
                provider=args.get("provider"), limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "credentials": result})

    # ── Environments ──────────────────────────────────────────────────────
    elif mod is environments:
        if name == "create_environment":
            return _json_result(db.create_environment(
                name=args["name"], project=args.get("project"),
                type=args.get("type", "development"), url=args.get("url"),
                description=args.get("description", ""),
                config=args.get("config"), tags=args.get("tags"),
            ))
        elif name == "update_environment":
            fields = {k: v for k, v in args.items() if k != "environment_id"}
            return _json_result(db.update_environment(args["environment_id"], **fields))
        elif name == "get_environment":
            e = db.get_environment(args["environment_id"])
            return _json_result(e or {"error": f"Environment not found: {args['environment_id']}"})
        elif name == "list_environments":
            result = db.list_environments(
                project=args.get("project"), type=args.get("type"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "environments": result})

    # ── Deployments ───────────────────────────────────────────────────────
    elif mod is deployments:
        if name == "create_deployment":
            return _json_result(db.create_deployment(
                version=args["version"], project=args.get("project"),
                environment_id=args.get("environment_id"),
                status=args.get("status", "pending"), strategy=args.get("strategy", "rolling"),
                description=args.get("description", ""), branch=args.get("branch"),
                session_id=args.get("session_id"), deployed_by=args.get("deployed_by"),
                rollback_to=args.get("rollback_to"), deployed_at=args.get("deployed_at"),
                tags=args.get("tags"),
            ))
        elif name == "update_deployment":
            fields = {k: v for k, v in args.items() if k != "deployment_id"}
            return _json_result(db.update_deployment(args["deployment_id"], **fields))
        elif name == "get_deployment":
            d = db.get_deployment(args["deployment_id"])
            return _json_result(d or {"error": f"Deployment not found: {args['deployment_id']}"})
        elif name == "list_deployments":
            result = db.list_deployments(
                project=args.get("project"), branch=args.get("branch"),
                status=args.get("status"), environment_id=args.get("environment_id"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "deployments": result})

    # ── Builds ────────────────────────────────────────────────────────────
    elif mod is builds:
        if name == "create_build":
            return _json_result(db.create_build(
                name=args["name"], project=args.get("project"),
                pipeline=args.get("pipeline", ""), status=args.get("status", "pending"),
                trigger_type=args.get("trigger_type", "push"),
                commit_sha=args.get("commit_sha"), branch=args.get("branch"),
                artifact_url=args.get("artifact_url"),
                duration_seconds=args.get("duration_seconds"),
                session_id=args.get("session_id"),
                started_at=args.get("started_at"), finished_at=args.get("finished_at"),
                tags=args.get("tags"),
            ))
        elif name == "update_build":
            fields = {k: v for k, v in args.items() if k != "build_id"}
            return _json_result(db.update_build(args["build_id"], **fields))
        elif name == "get_build":
            b = db.get_build(args["build_id"])
            return _json_result(b or {"error": f"Build not found: {args['build_id']}"})
        elif name == "list_builds":
            result = db.list_builds(
                project=args.get("project"), branch=args.get("branch"),
                status=args.get("status"), pipeline=args.get("pipeline"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "builds": result})

    # ── Incidents ─────────────────────────────────────────────────────────
    elif mod is incidents:
        if name == "create_incident":
            return _json_result(db.create_incident(
                title=args["title"], project=args.get("project"),
                severity=args.get("severity", "p3"), status=args.get("status", "investigating"),
                description=args.get("description", ""),
                root_cause=args.get("root_cause"), resolution=args.get("resolution"),
                timeline=args.get("timeline"), lead_id=args.get("lead_id"),
                started_at=args.get("started_at"), resolved_at=args.get("resolved_at"),
                tags=args.get("tags"),
            ))
        elif name == "update_incident":
            fields = {k: v for k, v in args.items() if k != "incident_id"}
            return _json_result(db.update_incident(args["incident_id"], **fields))
        elif name == "get_incident":
            i = db.get_incident(args["incident_id"])
            return _json_result(i or {"error": f"Incident not found: {args['incident_id']}"})
        elif name == "list_incidents":
            result = db.list_incidents(
                project=args.get("project"), severity=args.get("severity"),
                status=args.get("status"), lead_id=args.get("lead_id"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "incidents": result})

    # ── Dependencies ──────────────────────────────────────────────────────
    elif mod is dependencies:
        if name == "create_dependency":
            return _json_result(db.create_dependency(
                name=args["name"], project=args.get("project"),
                version=args.get("version", ""), type=args.get("type", "library"),
                source=args.get("source"), license=args.get("license"),
                description=args.get("description", ""),
                pinned_version=args.get("pinned_version"),
                latest_version=args.get("latest_version"), tags=args.get("tags"),
            ))
        elif name == "update_dependency":
            fields = {k: v for k, v in args.items() if k != "dependency_id"}
            return _json_result(db.update_dependency(args["dependency_id"], **fields))
        elif name == "get_dependency":
            d = db.get_dependency(args["dependency_id"])
            return _json_result(d or {"error": f"Dependency not found: {args['dependency_id']}"})
        elif name == "list_dependencies":
            result = db.list_dependencies(
                project=args.get("project"), type=args.get("type"),
                limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "dependencies": result})

    # ── Runbooks ──────────────────────────────────────────────────────────
    elif mod is runbooks:
        if name == "create_runbook":
            return _json_result(db.create_runbook(
                title=args["title"], project=args.get("project"),
                description=args.get("description", ""),
                steps=args.get("steps"), trigger_conditions=args.get("trigger_conditions"),
                last_executed=args.get("last_executed"), tags=args.get("tags"),
            ))
        elif name == "update_runbook":
            fields = {k: v for k, v in args.items() if k != "runbook_id"}
            return _json_result(db.update_runbook(args["runbook_id"], **fields))
        elif name == "get_runbook":
            r = db.get_runbook(args["runbook_id"])
            return _json_result(r or {"error": f"Runbook not found: {args['runbook_id']}"})
        elif name == "list_runbooks":
            result = db.list_runbooks(
                project=args.get("project"), limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "runbooks": result})

    # ── Decisions (ADRs) ──────────────────────────────────────────────────
    elif mod is decisions:
        if name == "create_decision":
            return _json_result(db.create_decision(
                title=args["title"], project=args.get("project"),
                status=args.get("status", "proposed"), context=args.get("context", ""),
                options=args.get("options"), outcome=args.get("outcome"),
                consequences=args.get("consequences"), branch=args.get("branch"),
                session_id=args.get("session_id"), author_id=args.get("author_id"),
                superseded_by=args.get("superseded_by"),
                decided_at=args.get("decided_at"), tags=args.get("tags"),
            ))
        elif name == "update_decision":
            fields = {k: v for k, v in args.items() if k != "decision_id"}
            return _json_result(db.update_decision(args["decision_id"], **fields))
        elif name == "get_decision":
            d = db.get_decision(args["decision_id"])
            return _json_result(d or {"error": f"Decision not found: {args['decision_id']}"})
        elif name == "list_decisions":
            result = db.list_decisions(
                project=args.get("project"), branch=args.get("branch"),
                status=args.get("status"), limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "decisions": result})

    # ── Diagrams ─────────────────────────────────────────────────────────
    elif mod is diagrams:
        if name == "create_diagram":
            # Validate JSON for non-mermaid types
            dtype = args.get("diagram_type", "mermaid")
            if dtype in ("chart", "network", "servicemap", "table"):
                import json as _json
                try:
                    _json.loads(args["definition"])
                except (ValueError, KeyError):
                    return _json_result({"error": f"definition must be valid JSON for diagram_type '{dtype}'"})
            return _json_result(db.create_diagram(
                title=args["title"], definition=args.get("definition", ""),
                diagram_type=dtype, description=args.get("description", ""),
                data_source=args.get("data_source"), project=args.get("project"),
                branch=args.get("branch"), session_id=args.get("session_id"),
                tags=args.get("tags"),
            ))
        elif name == "update_diagram":
            fields = {k: v for k, v in args.items() if k != "diagram_id"}
            # Validate JSON if updating definition for non-mermaid types
            dtype = fields.get("diagram_type")
            defn = fields.get("definition")
            if defn and dtype in ("chart", "network", "servicemap", "table"):
                import json as _json
                try:
                    _json.loads(defn)
                except ValueError:
                    return _json_result({"error": f"definition must be valid JSON for diagram_type '{dtype}'"})
            return _json_result(db.update_diagram(args["diagram_id"], **fields))
        elif name == "get_diagram":
            d = db.get_diagram(args["diagram_id"])
            return _json_result(d or {"error": f"Diagram not found: {args['diagram_id']}"})
        elif name == "list_diagrams":
            result = db.list_diagrams(
                project=args.get("project"), branch=args.get("branch"),
                diagram_type=args.get("diagram_type"), limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "diagrams": result})
        elif name == "delete_diagram":
            ok = db.delete_diagram(args["diagram_id"])
            return _json_result({"deleted": ok, "diagram_id": args["diagram_id"]})

    # ── Comments ──────────────────────────────────────────────────────────
    elif mod is comments:
        if name == "add_comment":
            return _json_result(db.add_comment(
                entity_id=args["entity_id"], entity_type=args["entity_type"],
                content=args["content"], author=args.get("author", ""),
                parent_id=args.get("parent_id"), project=args.get("project"),
                tags=args.get("tags"),
            ))
        elif name == "update_comment":
            fields = {k: v for k, v in args.items() if k != "comment_id"}
            return _json_result(db.update_comment(args["comment_id"], **fields))
        elif name == "get_comments":
            result = db.get_comments(
                entity_id=args["entity_id"], entity_type=args.get("entity_type"),
                project=args.get("project"), limit=args.get("limit", 50),
            )
            return _json_result({"count": len(result), "comments": result})
        elif name == "delete_comment":
            deleted = db.delete_comment(args["comment_id"])
            return _json_result({"deleted": deleted, "comment_id": args["comment_id"]})

    # ── Audit Log ─────────────────────────────────────────────────────────
    elif mod is audit:
        if name == "log_audit":
            return _json_result(db.log_audit(
                entity_id=args["entity_id"], entity_type=args["entity_type"],
                action=args["action"], field_changed=args.get("field_changed"),
                old_value=args.get("old_value"), new_value=args.get("new_value"),
                actor=args.get("actor"), project=args.get("project"),
            ))
        elif name == "get_audit_log":
            result = db.get_audit_log(
                entity_id=args.get("entity_id"), entity_type=args.get("entity_type"),
                action=args.get("action"), actor=args.get("actor"),
                project=args.get("project"), limit=args.get("limit", 100),
            )
            return _json_result({"count": len(result), "entries": result})

    return _json_result({"error": f"Unknown tool: {name}"})
