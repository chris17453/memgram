"""People management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="add_person",
        description=(
            "Add a person to the knowledge graph — a team member, contributor, stakeholder, etc. "
            "People can own components, lead features, author specs, and be assigned to plan tasks. "
            "Track their role, skills, and contact info."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person's name"},
                "type": {
                    "type": "string",
                    "enum": ["individual", "contractor", "team_member"],
                    "description": "Person type — individual contributor, contractor, or team member",
                    "default": "individual",
                },
                "role": {"type": "string", "description": "Role (engineer, designer, pm, lead, devops, etc.)"},
                "email": {"type": "string"},
                "github": {"type": "string", "description": "GitHub username"},
                "skills": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Skills and expertise areas",
                },
                "notes": {"type": "string", "description": "Additional notes about this person"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="update_person",
        description="Update a person's fields — name, role, email, github, skills, notes.",
        inputSchema={
            "type": "object",
            "properties": {
                "person_id": {"type": "string"},
                "name": {"type": "string"},
                "type": {"type": "string", "enum": ["individual", "contractor", "team_member"]},
                "role": {"type": "string"},
                "email": {"type": "string"},
                "github": {"type": "string"},
                "skills": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "string"},
            },
            "required": ["person_id"],
        },
    ),
    Tool(
        name="get_person",
        description=(
            "Get a person with everything they own, lead, and authored — "
            "components, features, specs, and team memberships."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "person_id": {"type": "string"},
            },
            "required": ["person_id"],
        },
    ),
    Tool(
        name="list_people",
        description="List people, optionally filtered by role.",
        inputSchema={
            "type": "object",
            "properties": {
                "role": {"type": "string", "description": "Filter by role"},
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
]
