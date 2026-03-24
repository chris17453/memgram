"""API endpoint management MCP tools."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_endpoint",
        description=(
            "Create an API endpoint definition — a formal record of a route in your service. "
            "Endpoints track method, path, auth, rate limits, and request/response schemas. "
            "Link them to a project to keep your API surface documented and discoverable."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "URL path (e.g. /api/v1/users)"},
                "project": {"type": "string"},
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                    "default": "GET",
                },
                "base_url": {"type": "string", "description": "Base URL of the API (e.g. https://api.example.com)"},
                "description": {"type": "string", "description": "What this endpoint does"},
                "auth_type": {
                    "type": "string",
                    "enum": ["none", "api_key", "bearer", "oauth", "basic"],
                    "description": "Authentication method required",
                },
                "rate_limit": {"type": "string", "description": "Rate limit (e.g. 100/min, 1000/hour)"},
                "request_schema": {"type": "string", "description": "JSON schema or description of the request body"},
                "response_schema": {"type": "string", "description": "JSON schema or description of the response body"},
                "status": {
                    "type": "string",
                    "enum": ["active", "deprecated", "planned"],
                    "default": "active",
                },
                "branch": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["path", "project"],
        },
    ),
    Tool(
        name="update_endpoint",
        description="Update an endpoint's fields — path, method, auth, rate limit, schemas, status, tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "endpoint_id": {"type": "string"},
                "path": {"type": "string"},
                "project": {"type": "string"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]},
                "base_url": {"type": "string"},
                "description": {"type": "string"},
                "auth_type": {"type": "string", "enum": ["none", "api_key", "bearer", "oauth", "basic"]},
                "rate_limit": {"type": "string"},
                "request_schema": {"type": "string"},
                "response_schema": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "deprecated", "planned"]},
                "branch": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["endpoint_id"],
        },
    ),
    Tool(
        name="get_endpoint",
        description="Get an API endpoint definition by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "endpoint_id": {"type": "string"},
            },
            "required": ["endpoint_id"],
        },
    ),
    Tool(
        name="list_endpoints",
        description="List API endpoints filtered by project, branch, method, or status.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "branch": {"type": "string"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]},
                "status": {"type": "string", "enum": ["active", "deprecated", "planned"]},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]
