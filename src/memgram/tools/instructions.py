"""Agent instructions MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="get_instructions",
        description=(
            "Get all active instructions for the current context. Returns ordered instruction "
            "sections filtered by project and branch scope. Global instructions are always included. "
            "Call this at session start to understand how to use memgram and what behavioral rules to follow."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Filter by project (includes project-scoped + global instructions)",
                },
                "branch": {
                    "type": "string",
                    "description": "Filter by branch (includes branch-scoped + project + global)",
                },
                "section": {
                    "type": "string",
                    "description": "Get a specific section only (by slug)",
                },
                "include_global": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include global instructions (default: true)",
                },
            },
        },
    ),
    Tool(
        name="create_instruction",
        description=(
            "Create a new instruction section. Instructions tell agents how to behave — "
            "session lifecycle, recording rules, search strategies, etc. "
            "Scope: 'global' applies everywhere, 'project' applies to a specific project, "
            "'branch' applies to a specific branch within a project."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Section slug (e.g. 'session-lifecycle', 'what-to-record')",
                },
                "title": {
                    "type": "string",
                    "description": "Display title (e.g. 'Session Lifecycle')",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown instruction content",
                },
                "position": {
                    "type": "integer",
                    "description": "Sort order (auto-assigned if omitted)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "default": "medium",
                    "description": "Importance level — critical instructions are returned first",
                },
                "scope": {
                    "type": "string",
                    "enum": ["global", "project", "branch"],
                    "default": "global",
                    "description": "Scope level for this instruction",
                },
                "project": {"type": "string", "description": "Project tag (required for project/branch scope)"},
                "branch": {"type": "string", "description": "Branch name (required for branch scope)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
            },
            "required": ["section", "title", "content"],
        },
    ),
    Tool(
        name="update_instruction",
        description="Update an instruction section's title, content, position, scope, or active status.",
        inputSchema={
            "type": "object",
            "properties": {
                "instruction_id": {"type": "string", "description": "Instruction ID to update"},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "section": {"type": "string"},
                "position": {"type": "integer"},
                "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "scope": {"type": "string", "enum": ["global", "project", "branch"]},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "active": {"type": "boolean", "description": "Set false to deactivate"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["instruction_id"],
        },
    ),
    Tool(
        name="list_instruction_sections",
        description="List all instruction section names and titles for a given scope, without full content. Useful for seeing what instruction topics exist.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Filter by project"},
                "branch": {"type": "string", "description": "Filter by branch"},
            },
        },
    ),
]
