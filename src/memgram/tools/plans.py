"""Plan and task tracking MCP tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import TextContent, Tool

TOOLS = [
    Tool(
        name="create_plan",
        description=(
            "Create a plan to organize and track work. Plans have scope (project/sprint/session/milestone), "
            "priority, optional due dates, and can be pinned to a session. "
            "Use cases: multi-session refactors, migration tracking, release prep, incident response, "
            "bug investigation, sprint breakdowns."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Plan title"},
                "description": {"type": "string", "description": "Detailed plan description and goals"},
                "scope": {
                    "type": "string",
                    "enum": ["project", "sprint", "session", "milestone", "custom"],
                    "description": "Scope of the plan",
                    "default": "project",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Plan priority",
                    "default": "medium",
                },
                "session_id": {"type": "string", "description": "Pin this plan to a session"},
                "project": {"type": "string", "description": "Project tag"},
                "branch": {"type": "string", "description": "Git branch name"},
                "due_date": {"type": "string", "description": "Target completion date (ISO 8601)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
            },
            "required": ["title", "project"],
        },
    ),
    Tool(
        name="update_plan",
        description="Update a plan's title, description, status, priority, scope, due date, or tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "Plan ID to update"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["draft", "active", "paused", "completed", "abandoned"],
                },
                "scope": {
                    "type": "string",
                    "enum": ["project", "sprint", "session", "milestone", "custom"],
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "session_id": {"type": "string", "description": "Pin/re-pin to a session"},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "due_date": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["plan_id"],
        },
    ),
    Tool(
        name="get_plan",
        description="Get a plan with all its tasks, progress counts, and status.",
        inputSchema={
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "Plan ID"},
            },
            "required": ["plan_id"],
        },
    ),
    Tool(
        name="list_plans",
        description=(
            "List plans filtered by project, branch, session, or status. "
            "Returns plans sorted by priority then recency."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Filter by project"},
                "branch": {"type": "string", "description": "Filter by branch"},
                "session_id": {"type": "string", "description": "Filter by pinned session"},
                "status": {
                    "type": "string",
                    "enum": ["draft", "active", "paused", "completed", "abandoned"],
                    "description": "Filter by status",
                },
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="add_plan_task",
        description=(
            "Add a task to a plan. Tasks track individual work items with status, "
            "ordering, optional assignee, and dependencies on other tasks."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "Plan to add task to"},
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task details"},
                "assignee": {"type": "string", "description": "Who is responsible (agent name, person, etc.)"},
                "depends_on": {"type": "string", "description": "Task ID this task depends on (must complete first)"},
                "position": {"type": "integer", "description": "Sort position (auto-assigned if omitted)"},
            },
            "required": ["plan_id", "title"],
        },
    ),
    Tool(
        name="update_plan_task",
        description=(
            "Update a plan task's status, title, description, assignee, or dependencies. "
            "Status flow: pending → in_progress → completed (or skipped/blocked). "
            "Completed tasks automatically get a completed_at timestamp."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to update"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "skipped", "blocked"],
                },
                "assignee": {"type": "string"},
                "depends_on": {"type": "string"},
                "position": {"type": "integer"},
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="delete_plan_task",
        description="Remove a task from a plan.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to delete"},
            },
            "required": ["task_id"],
        },
    ),
]
