"""Health and diagnostics tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..db import MemgramDB

TOOLS = [
    Tool(
        name="get_health",
        description="Report database health (connectivity, WAL mode, foreign key status, vector availability, table counts).",
        inputSchema={
            "type": "object",
            "properties": {
                "include_counts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include per-table row counts in the response.",
                },
            },
        },
    ),
]


def _json_result(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def register(server: Server, db: MemgramDB) -> None:
    """Register health/diagnostics tools."""

    @server.call_tool()
    async def _handle(name: str, arguments: dict | None) -> list[TextContent]:
        args = arguments or {}

        if name == "get_health":
            diagnostics = db.health()
            if not args.get("include_counts", True):
                diagnostics = {k: v for k, v in diagnostics.items() if k != "counts"}
            return _json_result(diagnostics)

        return _json_result({"error": f"Unknown tool: {name}"})
