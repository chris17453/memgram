"""Credential reference management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_credential",
        description=(
            "Store a REFERENCE to a secret or credential — never the actual secret value. "
            "Track where credentials live (vault paths, env vars), who provides them, "
            "when they expire, and when they were last rotated. Use this to maintain an "
            "inventory of credentials across projects without exposing sensitive data."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Human-readable credential name"},
                "project": {"type": "string", "description": "Project this credential belongs to"},
                "type": {
                    "type": "string",
                    "enum": ["api_key", "token", "password", "certificate", "ssh_key", "oauth"],
                    "default": "api_key",
                },
                "provider": {"type": "string", "description": "Service or provider (e.g. AWS, Stripe, GitHub)"},
                "vault_path": {"type": "string", "description": "Path in secrets manager / vault"},
                "env_var": {"type": "string", "description": "Environment variable name that holds the secret"},
                "description": {"type": "string", "description": "What this credential is used for"},
                "last_rotated": {"type": "string", "description": "ISO-8601 date when the credential was last rotated"},
                "expires_at": {"type": "string", "description": "ISO-8601 date when the credential expires"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "project"],
        },
    ),
    Tool(
        name="update_credential",
        description="Update a credential reference — name, type, provider, vault path, env var, rotation/expiry dates, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "credential_id": {"type": "string"},
                "name": {"type": "string"},
                "project": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["api_key", "token", "password", "certificate", "ssh_key", "oauth"],
                },
                "provider": {"type": "string"},
                "vault_path": {"type": "string"},
                "env_var": {"type": "string"},
                "description": {"type": "string"},
                "last_rotated": {"type": "string"},
                "expires_at": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["credential_id"],
        },
    ),
    Tool(
        name="get_credential",
        description="Get a credential reference and its metadata.",
        inputSchema={
            "type": "object",
            "properties": {
                "credential_id": {"type": "string"},
            },
            "required": ["credential_id"],
        },
    ),
    Tool(
        name="list_credentials",
        description="List credential references filtered by project, type, or provider.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["api_key", "token", "password", "certificate", "ssh_key", "oauth"],
                },
                "provider": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
