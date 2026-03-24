"""Incident management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_incident",
        description=(
            "Create an incident record — tracks outages, bugs, and production issues. "
            "Incidents have severity levels (p0–p4), status tracking through investigation "
            "to resolution, and support timelines, root-cause analysis, and post-mortems. "
            "Assign a lead to track who is driving the response."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Incident title"},
                "project": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["p0", "p1", "p2", "p3", "p4"],
                    "default": "p3",
                },
                "status": {
                    "type": "string",
                    "enum": ["investigating", "identified", "monitoring", "resolved", "postmortem"],
                    "default": "investigating",
                },
                "description": {"type": "string", "description": "What happened and what is the impact"},
                "root_cause": {"type": "string", "description": "Identified root cause of the incident"},
                "resolution": {"type": "string", "description": "How the incident was resolved"},
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                    "description": "Chronological list of events during the incident",
                },
                "lead_id": {"type": "string", "description": "Person ID of the incident lead"},
                "started_at": {"type": "string", "description": "When the incident started (ISO 8601)"},
                "resolved_at": {"type": "string", "description": "When the incident was resolved (ISO 8601)"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "project"],
        },
    ),
    Tool(
        name="update_incident",
        description="Update an incident's fields — severity, status, root cause, resolution, timeline, lead, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "title": {"type": "string"},
                "project": {"type": "string"},
                "severity": {"type": "string", "enum": ["p0", "p1", "p2", "p3", "p4"]},
                "status": {"type": "string", "enum": ["investigating", "identified", "monitoring", "resolved", "postmortem"]},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "resolution": {"type": "string"},
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
                "lead_id": {"type": "string"},
                "started_at": {"type": "string"},
                "resolved_at": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="get_incident",
        description="Get an incident by ID with its full details, timeline, and linked entities.",
        inputSchema={
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
            },
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="list_incidents",
        description="List incidents filtered by project, severity, status, or lead.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "severity": {"type": "string", "enum": ["p0", "p1", "p2", "p3", "p4"]},
                "status": {"type": "string", "enum": ["investigating", "identified", "monitoring", "resolved", "postmortem"]},
                "lead_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
