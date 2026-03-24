"""Ticket tracking MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_ticket",
        description=(
            "Create a ticket with an auto-generated ticket number (e.g. MG-1, MYAPP-42). "
            "Tickets track bugs, tasks, features, improvements, and questions. "
            "They can be assigned to people, linked to a project/branch/session, "
            "and organized into parent/child hierarchies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Ticket title"},
                "description": {"type": "string", "description": "Detailed description"},
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "review", "resolved", "closed", "wontfix"],
                    "default": "open",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "default": "medium",
                },
                "type": {
                    "type": "string",
                    "enum": ["bug", "task", "feature", "improvement", "question"],
                    "default": "task",
                },
                "ticket_number": {
                    "type": "string",
                    "description": "Custom ticket number (auto-generated if omitted, e.g. MG-1)",
                },
                "assignee_id": {"type": "string", "description": "Person ID to assign to"},
                "reporter_id": {"type": "string", "description": "Person ID who reported this"},
                "project": {"type": "string", "description": "Project tag (used for ticket number prefix)"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "parent_id": {"type": "string", "description": "Parent ticket ID for sub-tickets"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "due_date": {"type": "string", "description": "Due date (ISO 8601)"},
            },
            "required": ["title", "project"],
        },
    ),
    Tool(
        name="update_ticket",
        description=(
            "Update a ticket's fields. Status flow: open → in_progress → review → resolved → closed. "
            "resolved_at is auto-set when status moves to resolved/closed."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket ID to update"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "review", "resolved", "closed", "wontfix"],
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "type": {
                    "type": "string",
                    "enum": ["bug", "task", "feature", "improvement", "question"],
                },
                "assignee_id": {"type": "string"},
                "reporter_id": {"type": "string"},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "parent_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "due_date": {"type": "string"},
            },
            "required": ["ticket_id"],
        },
    ),
    Tool(
        name="get_ticket",
        description=(
            "Get a ticket by ID or ticket number (e.g. 'MG-42'). "
            "Returns the ticket with its sub-tickets and attachments."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket ID"},
                "ticket_number": {"type": "string", "description": "Ticket number (e.g. MG-42)"},
            },
        },
    ),
    Tool(
        name="list_tickets",
        description=(
            "List tickets filtered by project, branch, status, assignee, type, or parent. "
            "Returns tickets sorted by priority then recency."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Filter by project"},
                "branch": {"type": "string", "description": "Filter by branch"},
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "review", "resolved", "closed", "wontfix"],
                },
                "assignee_id": {"type": "string", "description": "Filter by assignee"},
                "type": {
                    "type": "string",
                    "enum": ["bug", "task", "feature", "improvement", "question"],
                },
                "parent_id": {"type": "string", "description": "Filter by parent ticket"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
