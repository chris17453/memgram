"""Component management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_component",
        description=(
            "Define a system component — a service, module, library, API, UI element, "
            "database, or infrastructure piece. Components have an owner (person), "
            "tech stack, and can be linked to features and specs via link_items."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Component name"},
                "description": {"type": "string", "description": "What this component does"},
                "type": {
                    "type": "string",
                    "enum": ["service", "module", "library", "api", "ui", "database", "infrastructure"],
                    "default": "module",
                },
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "owner_id": {"type": "string", "description": "Person ID who owns this component"},
                "tech_stack": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Technologies used (e.g. ['python', 'fastapi', 'postgres'])",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="update_component",
        description="Update a component's fields — name, description, type, owner, tech stack, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "component_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "type": {"type": "string", "enum": ["service", "module", "library", "api", "ui", "database", "infrastructure"]},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "owner_id": {"type": "string"},
                "tech_stack": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["component_id"],
        },
    ),
    Tool(
        name="get_component",
        description="Get a component with its links to features, people, and other entities.",
        inputSchema={
            "type": "object",
            "properties": {
                "component_id": {"type": "string"},
            },
            "required": ["component_id"],
        },
    ),
    Tool(
        name="list_components",
        description="List components filtered by project, branch, type, or owner.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "type": {"type": "string", "enum": ["service", "module", "library", "api", "ui", "database", "infrastructure"]},
                "owner_id": {"type": "string", "description": "Filter by owner person ID"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
