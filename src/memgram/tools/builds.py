"""Build management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_build",
        description=(
            "Create a build record — tracks a CI/CD pipeline execution. "
            "Builds have status, trigger type, optional commit/branch info, "
            "artifact URLs, and duration tracking."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Build name or identifier"},
                "project": {"type": "string"},
                "pipeline": {"type": "string", "description": "Pipeline name or path"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "passed", "failed", "cancelled"],
                    "default": "pending",
                },
                "trigger_type": {
                    "type": "string",
                    "enum": ["push", "pr", "manual", "schedule"],
                    "default": "push",
                },
                "commit_sha": {"type": "string", "description": "Git commit SHA"},
                "branch": {"type": "string"},
                "artifact_url": {"type": "string", "description": "URL to build artifacts"},
                "duration_seconds": {"type": "number", "description": "Build duration in seconds"},
                "session_id": {"type": "string"},
                "started_at": {"type": "string", "description": "ISO 8601 timestamp"},
                "finished_at": {"type": "string", "description": "ISO 8601 timestamp"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "project"],
        },
    ),
    Tool(
        name="update_build",
        description="Update a build's fields — status, artifact URL, duration, timestamps, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "build_id": {"type": "string"},
                "name": {"type": "string"},
                "project": {"type": "string"},
                "pipeline": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "passed", "failed", "cancelled"],
                },
                "trigger_type": {
                    "type": "string",
                    "enum": ["push", "pr", "manual", "schedule"],
                },
                "commit_sha": {"type": "string"},
                "branch": {"type": "string"},
                "artifact_url": {"type": "string"},
                "duration_seconds": {"type": "number"},
                "session_id": {"type": "string"},
                "started_at": {"type": "string"},
                "finished_at": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["build_id"],
        },
    ),
    Tool(
        name="get_build",
        description="Get a build record by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "build_id": {"type": "string"},
            },
            "required": ["build_id"],
        },
    ),
    Tool(
        name="list_builds",
        description="List builds filtered by project, branch, status, or pipeline.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "passed", "failed", "cancelled"],
                },
                "pipeline": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
