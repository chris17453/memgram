"""Runbook management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_runbook",
        description=(
            "Create a runbook — a step-by-step operational procedure for a project. "
            "Runbooks capture repeatable processes like deployments, incident response, "
            "or maintenance tasks with ordered steps and trigger conditions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Runbook title"},
                "project": {"type": "string"},
                "description": {"type": "string", "description": "Overview of what this runbook covers"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "order": {"type": "integer", "description": "Step order (1-based)"},
                            "title": {"type": "string", "description": "Short step title"},
                            "command": {"type": "string", "description": "Command to run, if applicable"},
                            "notes": {"type": "string", "description": "Additional context or warnings"},
                        },
                    },
                    "description": "Ordered list of step objects",
                },
                "trigger_conditions": {
                    "type": "string",
                    "description": "When this runbook should be executed",
                },
                "last_executed": {
                    "type": "string",
                    "description": "ISO timestamp of last execution",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "project"],
        },
    ),
    Tool(
        name="update_runbook",
        description="Update a runbook's fields — title, description, steps, trigger conditions, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "runbook_id": {"type": "string"},
                "title": {"type": "string"},
                "project": {"type": "string"},
                "description": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "order": {"type": "integer"},
                            "title": {"type": "string"},
                            "command": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                    },
                },
                "trigger_conditions": {"type": "string"},
                "last_executed": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["runbook_id"],
        },
    ),
    Tool(
        name="get_runbook",
        description="Get a runbook by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "runbook_id": {"type": "string"},
            },
            "required": ["runbook_id"],
        },
    ),
    Tool(
        name="list_runbooks",
        description="List runbooks filtered by project.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
