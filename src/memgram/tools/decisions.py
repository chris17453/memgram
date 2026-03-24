"""Decision record MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_decision",
        description=(
            "Record an architectural or design decision — captures the context, options "
            "considered, outcome, and consequences. Decisions track status from proposed "
            "through accepted to deprecated/superseded, forming a decision log for the project."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Decision title"},
                "project": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["proposed", "accepted", "deprecated", "superseded"],
                    "default": "proposed",
                },
                "context": {"type": "string", "description": "Background and motivation for this decision"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Options that were considered",
                },
                "outcome": {"type": "string", "description": "The chosen option and rationale"},
                "consequences": {"type": "string", "description": "Known consequences of this decision"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "author_id": {"type": "string", "description": "Person ID of the decision author"},
                "superseded_by": {"type": "string", "description": "Decision ID that supersedes this one"},
                "decided_at": {"type": "string", "description": "ISO timestamp when the decision was made"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "project"],
        },
    ),
    Tool(
        name="update_decision",
        description="Update a decision's fields — status, context, options, outcome, consequences, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "decision_id": {"type": "string"},
                "title": {"type": "string"},
                "project": {"type": "string"},
                "status": {"type": "string", "enum": ["proposed", "accepted", "deprecated", "superseded"]},
                "context": {"type": "string"},
                "options": {"type": "array", "items": {"type": "string"}},
                "outcome": {"type": "string"},
                "consequences": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "author_id": {"type": "string"},
                "superseded_by": {"type": "string"},
                "decided_at": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["decision_id"],
        },
    ),
    Tool(
        name="get_decision",
        description="Get a decision record by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "decision_id": {"type": "string"},
            },
            "required": ["decision_id"],
        },
    ),
    Tool(
        name="list_decisions",
        description="List decisions filtered by project, branch, or status.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "status": {"type": "string", "enum": ["proposed", "accepted", "deprecated", "superseded"]},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
