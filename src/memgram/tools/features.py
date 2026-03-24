"""Feature management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_feature",
        description=(
            "Define a feature — a distinct capability or user-facing functionality. "
            "Features can be linked to a spec, assigned a lead person, and connected "
            "to components via link_items. Track status from proposed through shipped."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Feature name"},
                "description": {"type": "string", "description": "What this feature does"},
                "status": {
                    "type": "string",
                    "enum": ["proposed", "in_progress", "completed", "shipped", "deprecated"],
                    "default": "proposed",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "default": "medium",
                },
                "spec_id": {"type": "string", "description": "Spec this feature implements"},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "lead_id": {"type": "string", "description": "Person ID of the feature lead"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "project"],
        },
    ),
    Tool(
        name="update_feature",
        description="Update a feature's fields — name, description, status, priority, spec, lead, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "feature_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string", "enum": ["proposed", "in_progress", "completed", "shipped", "deprecated"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "spec_id": {"type": "string"},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "lead_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["feature_id"],
        },
    ),
    Tool(
        name="get_feature",
        description="Get a feature with its links to components, specs, and other entities.",
        inputSchema={
            "type": "object",
            "properties": {
                "feature_id": {"type": "string"},
            },
            "required": ["feature_id"],
        },
    ),
    Tool(
        name="list_features",
        description="List features filtered by project, branch, status, or spec.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "status": {"type": "string", "enum": ["proposed", "in_progress", "completed", "shipped", "deprecated"]},
                "spec_id": {"type": "string", "description": "Filter by parent spec"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
