# Architecture

Memgram is structured as a layered system: CLI entry point, MCP server, tool dispatch, business logic, and database backend.

## File Structure

```
src/memgram/
|-- server.py              # MCP server entry point (stdio) + CLI subcommands
|-- models.py              # Data models (dataclasses)
|-- utils.py               # ID generation, timestamps, name normalization
|-- export.py              # Markdown + HTML export (memgram export / export-web)
|-- db/
|   |-- __init__.py        # create_db() factory
|   |-- base.py            # DatabaseBackend ABC + MemgramDB business logic
|   \-- sqlite.py          # SQLite + FTS5 + sqlite-vec backend
\-- tools/
    |-- __init__.py        # Tool registration & dispatch (normalization choke point)
    |-- sessions.py        # Session management tool definitions
    |-- knowledge.py       # Knowledge management tool definitions
    |-- search.py          # Search/retrieval/groups tool definitions
    |-- health.py          # Health and agent stats tool definitions
    |-- plans.py           # Plan management tool definitions
    |-- specs.py           # Spec management tool definitions
    |-- features.py        # Feature tracking tool definitions
    |-- components.py      # Component tracking tool definitions
    |-- people.py          # People/contact tool definitions
    |-- teams.py           # Team management tool definitions
    |-- tickets.py         # Ticket tracking tool definitions
    |-- instructions.py    # Agent instructions tool definitions
    |-- attachments.py     # Attachment (URL/file ref) tool definitions
    |-- endpoints.py       # API endpoint tool definitions
    |-- credentials.py     # Secret reference tool definitions
    |-- environments.py    # Environment tool definitions
    |-- deployments.py     # Deployment record tool definitions
    |-- builds.py          # CI/CD build tool definitions
    |-- incidents.py       # Incident tracking tool definitions
    |-- dependencies.py    # External dependency tool definitions
    |-- runbooks.py        # Operational runbook tool definitions
    |-- decisions.py       # ADR (decision record) tool definitions
    |-- comments.py        # Threaded comment tool definitions
    \-- audit.py           # Audit log tool definitions
```

## Layers

### CLI Entry Point (`server.py`)

The `main()` function uses `argparse` with subcommands:

- **`serve`** (default) — starts the MCP server over stdio via `asyncio.run(run_stdio())`
- **`export`** — dumps the database as linked markdown files (with optional `--project` filter)
- **`export-web`** — dumps the database as a navigable Jekyll HTML website
- **`agent-stats`** — shows contribution statistics by AI agent type and model
- **`list-projects`**, **`merge-projects`**, **`rename-project`** — project management

Global flags like `--db-path` go before the subcommand. Subcommand flags like `--embedding-dim` go after.

### MCP Server

`create_server()` instantiates an MCP `Server`, creates the database via `create_db()`, and registers all tools via `register_all()`. The server communicates over stdio using the MCP protocol.

### Tool Dispatch (`tools/__init__.py`)

This is the **normalization choke point** for the entire system. All tool calls flow through `_call_module_handler()`, which:

1. Normalizes `project` values (e.g., `"My-App"` -> `"myapp"`)
2. Normalizes `branch` values (e.g., `"feature/auth-flow"` -> `"featureauthflow"`)
3. Normalizes `keywords` arrays (each keyword normalized)
4. Normalizes group `name` values
5. Dispatches to the appropriate module handler

Tool definitions live in three modules:

- `sessions.py` — session management tools
- `knowledge.py` — knowledge management tools (thoughts, rules, errors, links)
- `search.py` — search, retrieval, and group tools
- `health.py` — health and reporting tools (`get_health`, `get_agent_stats`)
- `plans.py`, `specs.py`, `features.py`, `components.py`, `people.py`, `teams.py`, `tickets.py` — project management tools
- `endpoints.py`, `credentials.py`, `environments.py`, `deployments.py`, `builds.py` — infrastructure/DevOps tools
- `incidents.py`, `dependencies.py`, `runbooks.py`, `decisions.py` — operations/architecture tools
- `instructions.py` — agent instruction management tools
- `attachments.py`, `comments.py`, `audit.py` — cross-cutting tools (any entity)

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

## Dispatch Pipeline

```
AI Client (stdio)
    |
    v
MCP Server (server.py)
    |
    v
Tool Dispatcher (tools/__init__.py)
    |-- Normalize project, branch, keywords, group names
    \-- Route to module handler
         |
         v
    MemgramDB (db/base.py)
    |-- Business logic (scoring, context assembly)
    \-- Delegate SQL to backend
         |
         v
    SQLiteBackend (db/sqlite.py)
    |-- SQLite + WAL
    |-- FTS5 full-text search
    \-- sqlite-vec vector search
```

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
