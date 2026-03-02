"""Memgram — AI Memory Graph MCP Server."""

__version__ = "0.1.0"

from .db import create_db
from .server import main

__all__ = ["create_db", "main", "__version__"]
