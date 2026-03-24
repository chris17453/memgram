"""Audit-log MCP tools — track who changed what and when on any entity."""

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
        name="log_audit",
        description=(
            "Record an audit-log entry for a change to any entity. Use after creating, "
            "updating, deleting, or changing the status of an entity to maintain a full "
            "change history."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity that was changed",
                },
                "entity_type": {
                    "type": "string",
                    "enum": _ENTITY_TYPES,
                    "description": "Type of entity that was changed",
                },
                "action": {
                    "type": "string",
                    "enum": ["created", "updated", "deleted", "status_changed"],
                    "description": "What kind of change occurred",
                },
                "field_changed": {
                    "type": "string",
                    "description": "Name of the field that was modified (e.g. 'status', 'content')",
                },
                "old_value": {
                    "type": "string",
                    "description": "Previous value of the field (before the change)",
                },
                "new_value": {
                    "type": "string",
                    "description": "New value of the field (after the change)",
                },
                "actor": {
                    "type": "string",
                    "description": "Who or what performed the change (username, agent, system)",
                },
                "project": {
                    "type": "string",
                    "description": "Project scope",
                },
            },
            "required": ["entity_id", "entity_type", "action"],
        },
    ),
    Tool(
        name="get_audit_log",
        description=(
            "Query the audit log. All filters are optional — combine them to narrow results. "
            "Returns entries in reverse chronological order."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Filter by entity ID",
                },
                "entity_type": {
                    "type": "string",
                    "enum": _ENTITY_TYPES,
                    "description": "Filter by entity type",
                },
                "action": {
                    "type": "string",
                    "enum": ["created", "updated", "deleted", "status_changed"],
                    "description": "Filter by action type",
                },
                "actor": {
                    "type": "string",
                    "description": "Filter by who performed the change",
                },
                "project": {
                    "type": "string",
                    "description": "Filter by project scope",
                },
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "description": "Max entries to return (default 100)",
                },
            },
            "required": [],
        },
    ),
]
