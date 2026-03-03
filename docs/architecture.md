---
title: Architecture
layout: default
nav_order: 8
---

# Architecture

Memgram is structured as a layered system: CLI entry point, MCP server, tool dispatch, business logic, and database backend.

---

## File Structure

```
src/memgram/
├── server.py              # MCP server entry point (stdio) + CLI subcommands
├── models.py              # Data models (dataclasses)
├── utils.py               # ID generation, timestamps, name normalization
├── export.py              # Markdown export (memgram export)
├── db/
│   ├── __init__.py        # create_db() factory
│   ├── base.py            # DatabaseBackend ABC + MemgramDB business logic
│   └── sqlite.py          # SQLite + FTS5 + sqlite-vec backend
└── tools/
    ├── __init__.py        # Tool registration & dispatch (normalization choke point)
    ├── sessions.py        # Session management tool definitions
    ├── knowledge.py       # Knowledge management tool definitions
    └── search.py          # Search/retrieval/groups/maintenance tool definitions
```

---

## Layers

### CLI Entry Point (`server.py`)

The `main()` function uses `argparse` with two subcommands:

- **`serve`** (default) — starts the MCP server over stdio via `asyncio.run(run_stdio())`
- **`export`** — dumps the database as linked markdown files

Global flags like `--db-path` go before the subcommand. Subcommand flags like `--embedding-dim` go after.

### MCP Server

`create_server()` instantiates an MCP `Server`, creates the database via `create_db()`, and registers all tools via `register_all()`. The server communicates over stdio using the MCP protocol.

### Tool Dispatch (`tools/__init__.py`)

This is the **normalization choke point** for the entire system. All tool calls flow through `_call_module_handler()`, which:

1. Normalizes `project` values (e.g., `"My-App"` → `"myapp"`)
2. Normalizes `branch` values (e.g., `"feature/auth-flow"` → `"featureauthflow"`)
3. Normalizes `keywords` arrays (each keyword normalized)
4. Normalizes group `name` values
5. Dispatches to the appropriate module handler

Tool definitions live in three modules:
- `sessions.py` — 4 session management tools
- `knowledge.py` — 6 knowledge management tools
- `search.py` — 14 search, retrieval, group, and maintenance tools

Each module exports a `TOOLS` list (MCP `Tool` objects with JSON schemas) and a `register()` function. The dispatch in `__init__.py` merges them into a single handler.

### Business Logic (`db/base.py`)

`MemgramDB` contains all business logic — scoring, resume context assembly, search aggregation. It delegates raw SQL to a `DatabaseBackend` instance.

Key methods:
- `_compute_score()` — the 5-factor scoring formula used for search ranking
- `get_resume_context()` — assembles everything an AI needs to resume work
- `search()` — unified FTS search across all tables with scoring
- `search_by_embedding()` — RAG-style vector similarity search

### Database Backend (`db/sqlite.py`)

`SQLiteBackend` implements the `DatabaseBackend` ABC with:
- **SQLite** for storage (WAL mode, foreign keys)
- **FTS5** for full-text search (with triggers for automatic indexing)
- **sqlite-vec** for vector similarity search (cosine distance)

Schema initialization is idempotent — tables, FTS virtual tables, triggers, and indexes are all `CREATE IF NOT EXISTS`. The `_migrate_add_branch()` method adds the `branch` column to existing databases.

---

## Backend Abstraction

The `DatabaseBackend` ABC defines the interface that all backends must implement:

| Method | Purpose |
|--------|---------|
| `connect()` / `close()` | Lifecycle management |
| `execute()` / `fetchone()` / `fetchall()` | SQL primitives |
| `fts_search()` / `fts_search_errors()` / `fts_search_sessions()` | Full-text search |
| `store_embedding()` / `vector_search()` / `delete_embedding()` | Vector operations |
| `ph` property | Parameter placeholder (`?` for SQLite, `%s` for Postgres) |

This abstraction allows adding PostgreSQL/pgvector or other backends without changing any business logic.

---

## Dispatch Pipeline

```
AI Client (stdio)
    │
    ▼
MCP Server (server.py)
    │
    ▼
Tool Dispatcher (tools/__init__.py)
    ├── Normalize project, branch, keywords, group names
    └── Route to module handler
         │
         ▼
    MemgramDB (db/base.py)
    ├── Business logic (scoring, context assembly)
    └── Delegate SQL to backend
         │
         ▼
    SQLiteBackend (db/sqlite.py)
    ├── SQLite + WAL
    ├── FTS5 full-text search
    └── sqlite-vec vector search
```

---

## Extension Points

### Adding a New Tool

1. Define the `Tool` object with JSON schema in the appropriate module (`sessions.py`, `knowledge.py`, or `search.py`)
2. Add the handler case in `tools/__init__.py` under the module's dispatch section
3. Add any needed business logic methods to `MemgramDB` in `db/base.py`
4. Add any needed SQL to `DatabaseBackend` / `SQLiteBackend`

### Adding a New Backend

1. Create a new file in `db/` (e.g., `postgres.py`)
2. Implement the `DatabaseBackend` ABC
3. Update `create_db()` in `db/__init__.py` to support the new backend type

### Adding New Columns

Follow the migration pattern in `_migrate_add_branch()` — use `ALTER TABLE ADD COLUMN` wrapped in a try/except for idempotency.
