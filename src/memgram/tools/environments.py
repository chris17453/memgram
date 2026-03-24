"""Environment management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_environment",
        description=(
            "Create an environment — a deployment target like dev, staging, or production. "
            "Environments track URLs, configuration, and type for a project."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Environment name (e.g. 'prod-us-east', 'staging')"},
                "project": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["development", "staging", "production", "testing", "local"],
                    "default": "development",
                },
                "url": {"type": "string", "description": "Base URL for this environment"},
                "description": {"type": "string"},
                "config": {
                    "type": "object",
                    "description": "Arbitrary JSON configuration for this environment",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "project"],
        },
    ),
    Tool(
        name="update_environment",
        description="Update an environment's fields — name, type, url, description, config, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "environment_id": {"type": "string"},
                "name": {"type": "string"},
                "project": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["development", "staging", "production", "testing", "local"],
                },
                "url": {"type": "string"},
                "description": {"type": "string"},
                "config": {"type": "object"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["environment_id"],
        },
    ),
    Tool(
        name="get_environment",
        description="Get an environment by ID with its full configuration.",
        inputSchema={
            "type": "object",
            "properties": {
                "environment_id": {"type": "string"},
            },
            "required": ["environment_id"],
        },
    ),
    Tool(
        name="list_environments",
        description="List environments filtered by project or type.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["development", "staging", "production", "testing", "local"],
                },
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
