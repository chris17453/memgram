"""Dependency management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_dependency",
        description=(
            "Track a project dependency — a library, service, database, API, or tool "
            "that a project relies on. Record version info, license, and source to keep "
            "your dependency inventory current."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Dependency name (e.g. 'react', 'postgres')"},
                "project": {"type": "string"},
                "version": {"type": "string", "description": "Currently used version"},
                "type": {
                    "type": "string",
                    "enum": ["library", "service", "database", "api", "tool"],
                    "default": "library",
                },
                "source": {"type": "string", "description": "Where it comes from (e.g. npm, pypi, URL)"},
                "license": {"type": "string", "description": "License identifier (e.g. MIT, Apache-2.0)"},
                "description": {"type": "string", "description": "What this dependency does / why it's needed"},
                "pinned_version": {"type": "string", "description": "Pinned/locked version if different from version"},
                "latest_version": {"type": "string", "description": "Latest known available version"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "project"],
        },
    ),
    Tool(
        name="update_dependency",
        description="Update a dependency's fields — version, type, source, license, description, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "dependency_id": {"type": "string"},
                "name": {"type": "string"},
                "project": {"type": "string"},
                "version": {"type": "string"},
                "type": {"type": "string", "enum": ["library", "service", "database", "api", "tool"]},
                "source": {"type": "string"},
                "license": {"type": "string"},
                "description": {"type": "string"},
                "pinned_version": {"type": "string"},
                "latest_version": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["dependency_id"],
        },
    ),
    Tool(
        name="get_dependency",
        description="Get a dependency by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "dependency_id": {"type": "string"},
            },
            "required": ["dependency_id"],
        },
    ),
    Tool(
        name="list_dependencies",
        description="List dependencies filtered by project or type.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "type": {"type": "string", "enum": ["library", "service", "database", "api", "tool"]},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
