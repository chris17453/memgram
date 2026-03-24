"""Team management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_team",
        description=(
            "Create a team — a group of people who work together. "
            "Teams can own components, lead features, and be scoped to projects. "
            "Assign a lead and add members with add_team_member."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Team name"},
                "description": {"type": "string", "description": "What this team does"},
                "project": {"type": "string", "description": "Project scope"},
                "lead_id": {"type": "string", "description": "Person ID of the team lead"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="update_team",
        description="Update a team's fields — name, description, project, lead, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "team_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "project": {"type": "string"},
                "lead_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["team_id"],
        },
    ),
    Tool(
        name="get_team",
        description="Get a team with all its members and their details.",
        inputSchema={
            "type": "object",
            "properties": {
                "team_id": {"type": "string"},
            },
            "required": ["team_id"],
        },
    ),
    Tool(
        name="list_teams",
        description="List teams, optionally filtered by project.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="add_team_member",
        description="Add a person to a team with a role (member, lead, contributor).",
        inputSchema={
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "Team ID"},
                "person_id": {"type": "string", "description": "Person ID to add"},
                "role": {
                    "type": "string",
                    "enum": ["member", "lead", "contributor"],
                    "default": "member",
                    "description": "Role within the team",
                },
            },
            "required": ["team_id", "person_id"],
        },
    ),
    Tool(
        name="remove_team_member",
        description="Remove a person from a team.",
        inputSchema={
            "type": "object",
            "properties": {
                "team_id": {"type": "string"},
                "person_id": {"type": "string"},
            },
            "required": ["team_id", "person_id"],
        },
    ),
]
