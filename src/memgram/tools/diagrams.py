"""Diagram and visualization MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_diagram",
        description=(
            "Create a diagram or visualization — stores mermaid syntax, Chart.js configs, "
            "network graph definitions, service maps, or enhanced table specs. Diagrams are "
            "first-class entities that export to markdown (as fenced codeblocks) and HTML "
            "(with rendered interactive visualizations)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Diagram title"},
                "definition": {
                    "type": "string",
                    "description": (
                        "Diagram source: mermaid syntax for mermaid type, "
                        "Chart.js JSON config for chart type, "
                        '{"nodes":[],"edges":[]} JSON for network/servicemap type, '
                        '{"columns":[],"rows":[]} JSON for table type'
                    ),
                },
                "diagram_type": {
                    "type": "string",
                    "enum": ["mermaid", "chart", "network", "servicemap", "table"],
                    "default": "mermaid",
                    "description": "Visualization type",
                },
                "description": {"type": "string", "description": "What this diagram shows"},
                "data_source": {
                    "type": "string",
                    "description": "Future: query or entity type for auto-population",
                },
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "definition", "project"],
        },
    ),
    Tool(
        name="update_diagram",
        description="Update a diagram's fields — definition, type, description, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "diagram_id": {"type": "string"},
                "title": {"type": "string"},
                "diagram_type": {
                    "type": "string",
                    "enum": ["mermaid", "chart", "network", "servicemap", "table"],
                },
                "definition": {"type": "string"},
                "description": {"type": "string"},
                "data_source": {"type": "string"},
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "session_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["diagram_id"],
        },
    ),
    Tool(
        name="get_diagram",
        description="Get a diagram by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "diagram_id": {"type": "string"},
            },
            "required": ["diagram_id"],
        },
    ),
    Tool(
        name="list_diagrams",
        description="List diagrams filtered by project, branch, or type.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "diagram_type": {
                    "type": "string",
                    "enum": ["mermaid", "chart", "network", "servicemap", "table"],
                },
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="delete_diagram",
        description="Delete a diagram by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "diagram_id": {"type": "string"},
            },
            "required": ["diagram_id"],
        },
    ),
]
