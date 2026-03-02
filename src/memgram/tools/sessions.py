"""Session management MCP tools."""

from __future__ import annotations

from typing import Any, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..db import MemgramDB

TOOLS = [
    Tool(
        name="start_session",
        description=(
            "Start a new memgram session. Call this at the beginning of every conversation. "
            "Returns the session ID plus resume context (last session summary, pinned items, active rules)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "agent_type": {"type": "string", "description": "AI agent type: copilot, claude, cursor, etc."},
                "model": {"type": "string", "description": "Model name: gpt-4, claude-sonnet, etc."},
                "project": {"type": "string", "description": "Project tag (optional, for cross-project context leave empty)"},
                "goal": {"type": "string", "description": "What this session aims to accomplish"},
            },
            "required": ["agent_type", "model"],
        },
    ),
    Tool(
        name="end_session",
        description=(
            "End the current session with a summary. Also creates a structured session summary. "
            "Call this when finishing work."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to close"},
                "summary": {"type": "string", "description": "Summary of what was accomplished"},
                "outcome": {"type": "string", "description": "What actually happened"},
                "decisions_made": {"type": "array", "items": {"type": "string"}, "description": "Key decisions made"},
                "rules_learned": {"type": "array", "items": {"type": "string"}, "description": "Rule IDs created this session"},
                "errors_encountered": {"type": "array", "items": {"type": "string"}, "description": "Error pattern IDs from this session"},
                "files_modified": {"type": "array", "items": {"type": "string"}, "description": "Files touched this session"},
                "unresolved_items": {"type": "array", "items": {"type": "string"}, "description": "Open questions/issues"},
                "next_session_hints": {"type": "string", "description": "What the next session should know"},
            },
            "required": ["session_id", "summary"],
        },
    ),
    Tool(
        name="save_snapshot",
        description=(
            "Save a compaction checkpoint. Call this BEFORE context compaction to preserve state. "
            "Records current goal, progress, blockers, and next steps so the AI can resume seamlessly."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "current_goal": {"type": "string", "description": "What we're currently working on"},
                "progress_summary": {"type": "string", "description": "What's been done so far"},
                "open_questions": {"type": "array", "items": {"type": "string"}},
                "blockers": {"type": "array", "items": {"type": "string"}},
                "next_steps": {"type": "array", "items": {"type": "string"}},
                "active_files": {"type": "array", "items": {"type": "string"}, "description": "Files currently being worked on"},
                "key_decisions": {"type": "array", "items": {"type": "string"}, "description": "Decisions made in this segment"},
            },
            "required": ["session_id"],
        },
    ),
    Tool(
        name="get_resume_context",
        description=(
            "Get everything needed to resume work: last session info, latest compaction snapshot, "
            "pinned thoughts, active rules, and project summary. Call this after compaction or at session start."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project tag to scope context (optional)"},
            },
        },
    ),
]


import json


def _json_result(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def register(server: Server, db: MemgramDB) -> None:
    """Register session management tools with the MCP server."""

    @server.call_tool()
    async def _handle(name: str, arguments: dict | None) -> list[TextContent]:
        args = arguments or {}

        if name == "start_session":
            session = db.create_session(
                agent_type=args["agent_type"],
                model=args["model"],
                project=args.get("project"),
                goal=args.get("goal"),
            )
            resume = db.get_resume_context(project=args.get("project"))
            return _json_result({"session": session, "resume_context": resume})

        elif name == "end_session":
            session = db.end_session(args["session_id"], summary=args.get("summary"))
            # Create structured session summary
            ss = db.add_session_summary(
                session_id=args["session_id"],
                project=session.get("project"),
                goal=session.get("goal"),
                outcome=args.get("outcome", args.get("summary")),
                decisions_made=args.get("decisions_made"),
                rules_learned=args.get("rules_learned"),
                errors_encountered=args.get("errors_encountered"),
                files_modified=args.get("files_modified"),
                unresolved_items=args.get("unresolved_items"),
                next_session_hints=args.get("next_session_hints"),
            )
            # Update project summary counts if project is set
            if session.get("project"):
                db.update_project_summary(session["project"])
            return _json_result({"session": session, "session_summary": ss})

        elif name == "save_snapshot":
            snapshot = db.save_snapshot(
                session_id=args["session_id"],
                current_goal=args.get("current_goal"),
                progress_summary=args.get("progress_summary"),
                open_questions=args.get("open_questions"),
                blockers=args.get("blockers"),
                next_steps=args.get("next_steps"),
                active_files=args.get("active_files"),
                key_decisions=args.get("key_decisions"),
            )
            return _json_result(snapshot)

        elif name == "get_resume_context":
            ctx = db.get_resume_context(project=args.get("project"))
            return _json_result(ctx)

        return _json_result({"error": f"Unknown session tool: {name}"})
