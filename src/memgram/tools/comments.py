"""Threaded comment MCP tools — add discussion threads to any entity."""

from __future__ import annotations

from mcp.types import Tool

_ENTITY_TYPES = [
    "person", "team", "component", "feature", "spec", "plan",
    "thought", "rule", "error_pattern", "ticket", "endpoint",
    "credential", "environment", "deployment", "build", "incident",
    "dependency", "runbook", "decision", "instruction",
]

TOOLS = [
    Tool(
        name="add_comment",
        description=(
            "Add a threaded comment to any entity (person, team, component, feature, "
            "spec, plan, thought, rule, error_pattern, ticket, endpoint, credential, "
            "environment, deployment, build, incident, dependency, runbook, decision, "
            "instruction). Supports nested threading via parent_id."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to comment on",
                },
                "entity_type": {
                    "type": "string",
                    "enum": _ENTITY_TYPES,
                    "description": "Type of entity to comment on",
                },
                "content": {
                    "type": "string",
                    "description": "Comment body (plain text or markdown)",
                },
                "author": {
                    "type": "string",
                    "description": "Who wrote the comment (e.g. username, agent name)",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent comment ID for threaded replies",
                },
                "project": {
                    "type": "string",
                    "description": "Project scope",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorising the comment",
                },
            },
            "required": ["entity_id", "entity_type", "content"],
        },
    ),
    Tool(
        name="update_comment",
        description="Update an existing comment's content, author, or tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "Comment ID to update",
                },
                "content": {
                    "type": "string",
                    "description": "New comment body",
                },
                "author": {
                    "type": "string",
                    "description": "Updated author",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Replacement tag list",
                },
            },
            "required": ["comment_id"],
        },
    ),
    Tool(
        name="get_comments",
        description=(
            "Retrieve comments for an entity. Returns threaded structure "
            "(top-level and replies). Optionally filter by entity_type or project."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity whose comments to fetch",
                },
                "entity_type": {
                    "type": "string",
                    "enum": _ENTITY_TYPES,
                    "description": "Type of entity (optional, narrows search if entity_id is reused)",
                },
                "project": {
                    "type": "string",
                    "description": "Filter by project scope",
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "description": "Max comments to return (default 50)",
                },
            },
            "required": ["entity_id"],
        },
    ),
    Tool(
        name="delete_comment",
        description="Delete a comment by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "Comment ID to delete",
                },
            },
            "required": ["comment_id"],
        },
    ),
]
