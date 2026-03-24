"""Spec management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_spec",
        description=(
            "Create a specification — a formal definition of what needs to be built. "
            "Specs have acceptance criteria, priority, status tracking, and can be linked "
            "to features, components, and people. Assign an author to track who wrote it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Spec title"},
                "description": {"type": "string", "description": "Full spec content"},
                "status": {
                    "type": "string",
                    "enum": ["draft", "review", "approved", "implemented", "deprecated"],
                    "default": "draft",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "default": "medium",
                },
                "acceptance_criteria": {
                    "type": "array", "items": {"type": "string"},
                    "description": "List of acceptance criteria that define 'done'",
                },
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "author_id": {"type": "string", "description": "Person ID of the spec author"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "project"],
        },
    ),
    Tool(
        name="update_spec",
        description="Update a spec's fields — title, description, status, priority, acceptance criteria, author, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "spec_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string", "enum": ["draft", "review", "approved", "implemented", "deprecated"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "author_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["spec_id"],
        },
    ),
    Tool(
        name="get_spec",
        description="Get a spec with its linked features.",
        inputSchema={
            "type": "object",
            "properties": {
                "spec_id": {"type": "string"},
            },
            "required": ["spec_id"],
        },
    ),
    Tool(
        name="list_specs",
        description="List specs filtered by project, branch, or status.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "status": {"type": "string", "enum": ["draft", "review", "approved", "implemented", "deprecated"]},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
