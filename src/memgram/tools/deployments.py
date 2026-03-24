"""Deployment tracking MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_deployment",
        description=(
            "Record a deployment — track version releases across environments. "
            "Deployments have strategy, status tracking, and can be linked to projects, "
            "branches, and sessions. Use rollback_to to reference a previous deployment ID."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "version": {"type": "string", "description": "Version being deployed (e.g. v1.2.3)"},
                "project": {"type": "string"},
                "environment_id": {
                    "type": "string",
                    "description": "Target environment identifier (e.g. production, staging)",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "deploying", "deployed", "failed", "rolled_back"],
                    "default": "pending",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["rolling", "canary", "blue_green", "recreate"],
                    "default": "rolling",
                },
                "description": {"type": "string", "description": "Deployment notes or changelog summary"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "deployed_by": {"type": "string", "description": "Person ID or name of who triggered the deploy"},
                "rollback_to": {"type": "string", "description": "Deployment ID this is rolling back to"},
                "deployed_at": {"type": "string", "description": "ISO timestamp of deploy (defaults to now)"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["version", "project"],
        },
    ),
    Tool(
        name="update_deployment",
        description="Update a deployment's fields — status, description, strategy, tags, etc.",
        inputSchema={
            "type": "object",
            "properties": {
                "deployment_id": {"type": "string"},
                "version": {"type": "string"},
                "project": {"type": "string"},
                "environment_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "deploying", "deployed", "failed", "rolled_back"],
                },
                "strategy": {
                    "type": "string",
                    "enum": ["rolling", "canary", "blue_green", "recreate"],
                },
                "description": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "deployed_by": {"type": "string"},
                "rollback_to": {"type": "string"},
                "deployed_at": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["deployment_id"],
        },
    ),
    Tool(
        name="get_deployment",
        description="Get a deployment by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "deployment_id": {"type": "string"},
            },
            "required": ["deployment_id"],
        },
    ),
    Tool(
        name="list_deployments",
        description="List deployments filtered by project, branch, status, or environment.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "deploying", "deployed", "failed", "rolled_back"],
                },
                "environment_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
