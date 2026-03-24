"""Attachment management MCP tools — link files, images, audio, docs to any entity."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="add_attachment",
        description=(
            "Attach a URL or local file path to any entity (person, team, component, feature, "
            "spec, plan, thought, rule, error_pattern, project, instruction). "
            "Use for profile photos, architecture diagrams, audio recordings, documentation links, etc. "
            "Files are NOT stored in the database — only the URL/path is saved."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to attach to",
                },
                "entity_type": {
                    "type": "string",
                    "enum": [
                        "person", "team", "component", "feature", "spec",
                        "plan", "thought", "rule", "error_pattern", "project", "instruction",
                    ],
                    "description": "Type of entity to attach to",
                },
                "url": {
                    "type": "string",
                    "description": "URL or relative file path (e.g. 'https://...', './assets/photo.png')",
                },
                "label": {
                    "type": "string",
                    "description": "Display label (e.g. 'Profile Photo', 'Architecture Diagram')",
                },
                "type": {
                    "type": "string",
                    "enum": ["link", "image", "audio", "video", "document"],
                    "default": "link",
                    "description": "Attachment type",
                },
                "mime_type": {
                    "type": "string",
                    "description": "MIME type (e.g. 'image/png', 'audio/mp3') — optional",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the attachment",
                },
                "position": {
                    "type": "integer",
                    "description": "Sort order (auto-assigned if omitted)",
                },
            },
            "required": ["entity_id", "entity_type", "url"],
        },
    ),
    Tool(
        name="get_attachments",
        description=(
            "Get all attachments for an entity. Optionally filter by attachment type "
            "(image, audio, video, document, link)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity",
                },
                "entity_type": {
                    "type": "string",
                    "description": "Type of entity (optional, narrows search if entity_id is reused)",
                },
                "type_filter": {
                    "type": "string",
                    "enum": ["link", "image", "audio", "video", "document"],
                    "description": "Filter by attachment type",
                },
            },
            "required": ["entity_id"],
        },
    ),
    Tool(
        name="update_attachment",
        description="Update an attachment's label, URL, type, MIME type, description, or position.",
        inputSchema={
            "type": "object",
            "properties": {
                "attachment_id": {"type": "string", "description": "Attachment ID to update"},
                "url": {"type": "string"},
                "label": {"type": "string"},
                "type": {"type": "string", "enum": ["link", "image", "audio", "video", "document"]},
                "mime_type": {"type": "string"},
                "description": {"type": "string"},
                "position": {"type": "integer"},
            },
            "required": ["attachment_id"],
        },
    ),
    Tool(
        name="remove_attachment",
        description="Remove an attachment by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "attachment_id": {"type": "string", "description": "Attachment ID to remove"},
            },
            "required": ["attachment_id"],
        },
    ),
]
