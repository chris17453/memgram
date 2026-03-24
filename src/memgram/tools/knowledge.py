"""Knowledge management MCP tools (thoughts, rules, errors, links)."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..db import MemgramDB

TOOLS = [
    Tool(
        name="add_thought",
        description=(
            "Store a thought, observation, decision, idea, or note. "
            "Use this to record anything worth remembering across sessions. "
            "IMPORTANT: You MUST pass session_id from your current session. Call start_session first if you don't have one."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "REQUIRED: Your current session ID from start_session. Used for attribution tracking."},
                "summary": {"type": "string", "description": "Short searchable summary of the thought"},
                "content": {"type": "string", "description": "Full detailed content"},
                "type": {
                    "type": "string",
                    "enum": ["observation", "decision", "idea", "error", "pattern", "note"],
                    "description": "Type of thought",
                    "default": "note",
                },
                "project": {"type": "string", "description": "Project tag"},
                "branch": {"type": "string", "description": "Git branch name (optional)"},
                "agent_type": {"type": "string", "description": "AI agent type: copilot, claude, cursor, codex, etc. (auto-resolved from session if omitted)"},
                "agent_model": {"type": "string", "description": "Model identifier: gpt-4, claude-sonnet-4, etc. (auto-resolved from session if omitted)"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords for search"},
                "associated_files": {"type": "array", "items": {"type": "string"}, "description": "Related file paths"},
                "pinned": {"type": "boolean", "description": "Pin to always load in this project's context", "default": False},
            },
            "required": ["summary", "project"],
        },
    ),
    Tool(
        name="update_thought",
        description="Update an existing thought's fields.",
        inputSchema={
            "type": "object",
            "properties": {
                "thought_id": {"type": "string"},
                "summary": {"type": "string"},
                "content": {"type": "string"},
                "type": {"type": "string", "enum": ["observation", "decision", "idea", "error", "pattern", "note"]},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "associated_files": {"type": "array", "items": {"type": "string"}},
                "pinned": {"type": "boolean"},
                "archived": {"type": "boolean"},
            },
            "required": ["thought_id"],
        },
    ),
    Tool(
        name="add_rule",
        description=(
            "Store a learned rule — something to always do, never do, or do in specific contexts. "
            "Rules persist across sessions and are automatically surfaced when relevant. "
            "IMPORTANT: You MUST pass session_id from your current session. Call start_session first if you don't have one."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "REQUIRED: Your current session ID from start_session. Used for attribution tracking."},
                "summary": {"type": "string", "description": "Short rule description (e.g., 'Always use type hints in Python')"},
                "content": {"type": "string", "description": "Full explanation of the rule and reasoning"},
                "type": {
                    "type": "string",
                    "enum": ["do", "dont", "context_dependent"],
                    "description": "'do' = always do this, 'dont' = never do this, 'context_dependent' = depends on situation",
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "preference", "context_dependent"],
                    "description": "'critical' = never violate, 'preference' = soft guideline, 'context_dependent' = situational",
                },
                "condition": {"type": "string", "description": "When does this rule apply? (e.g., 'When writing Python async code')"},
                "project": {"type": "string", "description": "Project tag (null = global rule)"},
                "branch": {"type": "string", "description": "Git branch name (optional, null = branch-global rule)"},
                "agent_type": {"type": "string", "description": "AI agent type (auto-resolved from session if omitted)"},
                "agent_model": {"type": "string", "description": "Model identifier (auto-resolved from session if omitted)"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "associated_files": {"type": "array", "items": {"type": "string"}},
                "pinned": {"type": "boolean", "default": False},
            },
            "required": ["summary", "type", "severity", "project"],
        },
    ),
    Tool(
        name="reinforce_rule",
        description=(
            "Reinforce a rule — bump its confidence when you encounter another case that confirms it. "
            "Higher reinforcement = higher priority in search results."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "rule_id": {"type": "string"},
                "note": {"type": "string", "description": "Optional note about why this was reinforced"},
            },
            "required": ["rule_id"],
        },
    ),
    Tool(
        name="add_error_pattern",
        description=(
            "Log a failure pattern: what went wrong, why, how it was fixed. "
            "Optionally link to a prevention rule so the AI never repeats the mistake. "
            "IMPORTANT: You MUST pass session_id from your current session. Call start_session first if you don't have one."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "REQUIRED: Your current session ID from start_session. Used for attribution tracking."},
                "error_description": {"type": "string", "description": "What went wrong"},
                "cause": {"type": "string", "description": "Root cause"},
                "fix": {"type": "string", "description": "How it was fixed"},
                "prevention_rule_id": {"type": "string", "description": "ID of a rule created to prevent this"},
                "project": {"type": "string"},
                "branch": {"type": "string", "description": "Git branch name (optional)"},
                "agent_type": {"type": "string", "description": "AI agent type (auto-resolved from session if omitted)"},
                "agent_model": {"type": "string", "description": "Model identifier (auto-resolved from session if omitted)"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "associated_files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["error_description", "project"],
        },
    ),
    Tool(
        name="link_items",
        description=(
            "Create a directional link between any two entities in the knowledge graph. "
            "Connects thoughts, rules, errors, specs, features, components, plans, and people. "
            "Link types: informs, contradicts, supersedes, related, caused_by, implements, owns, depends_on, authored_by."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "from_id": {"type": "string"},
                "from_type": {
                    "type": "string",
                    "enum": ["thought", "rule", "error_pattern", "spec", "feature", "component", "plan", "person"],
                },
                "to_id": {"type": "string"},
                "to_type": {
                    "type": "string",
                    "enum": ["thought", "rule", "error_pattern", "spec", "feature", "component", "plan", "person"],
                },
                "link_type": {
                    "type": "string",
                    "enum": ["informs", "contradicts", "supersedes", "related", "caused_by",
                             "implements", "owns", "depends_on", "authored_by"],
                    "default": "related",
                },
            },
            "required": ["from_id", "from_type", "to_id", "to_type"],
        },
    ),
]


def _json_result(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def register(server: Server, db: MemgramDB) -> None:
    """Register knowledge management tools with the MCP server."""

    @server.call_tool()
    async def _handle(name: str, arguments: dict | None) -> list[TextContent]:
        args = arguments or {}

        if name == "add_thought":
            thought = db.add_thought(
                summary=args["summary"],
                content=args.get("content", ""),
                type=args.get("type", "note"),
                session_id=args.get("session_id"),
                project=args.get("project"),
                keywords=args.get("keywords"),
                associated_files=args.get("associated_files"),
                pinned=args.get("pinned", False),
            )
            return _json_result(thought)

        elif name == "update_thought":
            fields = {k: v for k, v in args.items() if k != "thought_id"}
            if "pinned" in fields:
                fields["pinned"] = 1 if fields["pinned"] else 0
            if "archived" in fields:
                fields["archived"] = 1 if fields["archived"] else 0
            thought = db.update_thought(args["thought_id"], **fields)
            return _json_result(thought)

        elif name == "add_rule":
            rule = db.add_rule(
                summary=args["summary"],
                content=args.get("content", ""),
                type=args["type"],
                severity=args["severity"],
                condition=args.get("condition"),
                session_id=args.get("session_id"),
                project=args.get("project"),
                keywords=args.get("keywords"),
                associated_files=args.get("associated_files"),
                pinned=args.get("pinned", False),
            )
            return _json_result(rule)

        elif name == "reinforce_rule":
            rule = db.reinforce_rule(args["rule_id"], note=args.get("note"))
            return _json_result(rule)

        elif name == "add_error_pattern":
            ep = db.add_error_pattern(
                error_description=args["error_description"],
                cause=args.get("cause"),
                fix=args.get("fix"),
                prevention_rule_id=args.get("prevention_rule_id"),
                session_id=args.get("session_id"),
                project=args.get("project"),
                keywords=args.get("keywords"),
                associated_files=args.get("associated_files"),
            )
            return _json_result(ep)

        elif name == "link_items":
            link = db.link_items(
                from_id=args["from_id"],
                from_type=args["from_type"],
                to_id=args["to_id"],
                to_type=args["to_type"],
                link_type=args.get("link_type", "related"),
            )
            return _json_result(link)

        return _json_result({"error": f"Unknown knowledge tool: {name}"})
