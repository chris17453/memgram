# Memgram — AI Memory Graph

A persistent memory layer for AI assistants, built as an [MCP](https://modelcontextprotocol.io/) server. Memgram gives any MCP-compatible AI (Copilot CLI, Claude Desktop, Claude Code, Cursor, etc.) the ability to remember thoughts, rules, decisions, and errors across sessions.

## Features

- **24 MCP tools** for storing/retrieving knowledge
- **Session management** — track what was done, when, by which AI/model
- **Two-dimensional scoping** — filter by `project` and/or `branch`
- **Name normalization** — `oxide-os`, `oxide_os`, `OxideOS` all match as `oxideos`
- **Compaction-aware** — save/restore state at context window boundaries
- **Rules engine** — learned do/don't patterns with severity and reinforcement
- **Error patterns** — failure knowledge that prevents repeated mistakes
- **FTS5 full-text search** with relevance scoring (recency + access + severity + pinned)
- **sqlite-vec vector search** for RAG-style semantic retrieval
- **Thought groups** — cluster related items together
- **Project summaries** — living overviews that auto-update
- **Markdown export** — dump the entire database as linked markdown files
- **Abstracted DB layer** — SQLite now, PostgreSQL/pgvector ready

## Quick Start

```bash
# Install
uv add memgram

# Run as MCP server (stdio) — default subcommand
memgram serve

# Or just:
memgram

# With custom DB path
memgram --db-path /path/to/memgram.db serve

# With custom embedding dimensions (default: 384)
memgram serve --embedding-dim 1536

# Export database as markdown
memgram export -o memgram-export
```

## CLI Subcommands

| Command | Description |
|---------|-------------|
| `memgram serve` | Run the MCP server over stdio (default when no subcommand given) |
| `memgram export` | Export the database as a tree of linked markdown files |

Global flags (`--db-path`) go before the subcommand; subcommand-specific flags go after.

## MCP Configuration

### Copilot CLI / VS Code

Add to your MCP settings (`.vscode/mcp.json` or global config):

```json
{
  "servers": {
    "memgram": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/memgram", "memgram"],
      "env": {
        "MEMGRAM_DB_PATH": "~/.memgram/memgram.db"
      }
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memgram": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/memgram", "memgram"],
      "env": {
        "MEMGRAM_DB_PATH": "~/.memgram/memgram.db"
      }
    }
  }
}
```

### Claude Code

Add to `.claude/settings.json` or project-level `.mcp.json`:

```json
{
  "mcpServers": {
    "memgram": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/memgram", "memgram"],
      "env": {
        "MEMGRAM_DB_PATH": "~/.memgram/memgram.db"
      }
    }
  }
}
```

## Scoping Model

Memgram uses a two-dimensional scoping system: **project** + **branch**.

| Dimension | Purpose | Example |
|-----------|---------|---------|
| `project` | Isolates knowledge per codebase/repo | `"myapp"`, `"oxideos"` |
| `branch` | Isolates knowledge per feature branch | `"featureauth"`, `"fixloginbug"` |

Both are optional and normalized (lowercased, non-alphanumeric stripped): `feature/auth-flow` becomes `featureauthflow`.

**How scoping works:**
- **No project, no branch** — item is fully global
- **Project only** — item scoped to that project, visible on all branches
- **Project + branch** — item scoped to that specific branch

**Retrieval behavior:**
- `get_rules` and `get_resume_context` use NULL-inclusive matching: when you pass `branch="featureauth"`, you get items where `branch='featureauth'` **plus** items where `branch IS NULL` (branch-global items). This means project-wide rules always surface regardless of which branch you're on.
- `search` and `list_sessions` use exact matching: only items matching the specified branch are returned.

**Guidance:**
- Use `branch` for feature-specific decisions, temporary workarounds, and branch-only context
- Omit `branch` for project-wide truths (coding standards, architecture decisions, persistent rules)
- When a branch merges, its branch-scoped knowledge stays in the DB but stops surfacing (since no one queries that branch anymore)

## Tools

### Session Management
| Tool | Branch | Description |
|------|--------|-------------|
| `start_session` | yes | Begin a session. Returns resume context (last snapshot, pinned items, rules). |
| `end_session` | — | Close with structured summary (decisions, files, next hints). |
| `save_snapshot` | — | Compaction checkpoint — goal, progress, blockers, next steps. |
| `get_resume_context` | yes | Everything needed to resume: session, snapshot, rules, project summary. |

### Knowledge Management
| Tool | Branch | Description |
|------|--------|-------------|
| `add_thought` | yes | Store a thought (observation, decision, idea, pattern, note). |
| `update_thought` | yes | Modify an existing thought. |
| `add_rule` | yes | Learned pattern — do/don't/context-dependent with severity. |
| `reinforce_rule` | — | Bump a rule's confidence when re-confirmed. |
| `add_error_pattern` | yes | Log a failure: what broke, why, how to fix. |
| `link_items` | — | Connect items (informs, contradicts, supersedes, related, caused_by). |

### Search & Retrieval
| Tool | Branch | Description |
|------|--------|-------------|
| `search` | yes | FTS5 full-text search across all tables with relevance scoring. |
| `search_by_embedding` | yes | RAG-style vector similarity search (requires stored embeddings). |
| `store_embedding` | — | Store a vector embedding for an item. |
| `get_rules` | yes | Get active rules for a context (project, branch, severity, keywords). |
| `get_session_history` | yes | Past sessions with summaries. |
| `get_related` | — | Items linked via the thought graph. |
| `get_project_summary` | — | Living project overview. |
| `update_project_summary` | — | Update project overview, tech stack, patterns, goals. |

### Groups & Maintenance
| Tool | Branch | Description |
|------|--------|-------------|
| `create_group` | yes | Create a named cluster (e.g., "authentication system"). |
| `add_to_group` | — | Add items to a group. |
| `remove_from_group` | — | Remove item from group. |
| `get_group` | yes | Get group with all member details. |
| `pin_item` | — | Pin/unpin — pinned items always load in resume context. |
| `archive_item` | — | Archive — excluded from search by default. |

## Architecture

```
src/memgram/
├── server.py              # MCP server entry point (stdio) + CLI subcommands
├── models.py              # Data models
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

## Database

Default location: `~/.memgram/memgram.db`

12 tables: sessions, thoughts, rules, compaction_snapshots, thought_links, error_patterns, project_summaries, session_summaries, thought_groups, group_members, embedding_meta + a sqlite-vec virtual table for vector search.

Existing databases are auto-migrated: the `branch` column is added to the 7 relevant tables on startup (idempotent). Existing rows get `branch=NULL`, which works seamlessly.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMGRAM_DB_PATH` | `~/.memgram/memgram.db` | SQLite database path |
| `MEMGRAM_EMBEDDING_DIM` | `384` | Embedding vector dimensions |
