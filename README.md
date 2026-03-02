# Memgram — AI Memory Graph

A persistent memory layer for AI assistants, built as an [MCP](https://modelcontextprotocol.io/) server. Memgram gives any MCP-compatible AI (Copilot CLI, Claude Desktop, Cursor, etc.) the ability to remember thoughts, rules, decisions, and errors across sessions.

## Features

- **24 MCP tools** for storing/retrieving knowledge
- **Session management** — track what was done, when, by which AI/model
- **Compaction-aware** — save/restore state at context window boundaries
- **Rules engine** — learned do/don't patterns with severity and reinforcement
- **Error patterns** — failure knowledge that prevents repeated mistakes
- **FTS5 full-text search** with relevance scoring (recency + access + severity + pinned)
- **sqlite-vec vector search** for RAG-style semantic retrieval
- **Thought groups** — cluster related items together
- **Project summaries** — living overviews that auto-update
- **Abstracted DB layer** — SQLite now, PostgreSQL/pgvector ready

## Quick Start

```bash
# Install
uv add memgram

# Run as MCP server (stdio)
uv run memgram

# Or with custom DB path
uv run memgram --db-path /path/to/memgram.db

# Or with custom embedding dimensions (default: 384)
uv run memgram --embedding-dim 1536
```

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

## Tools

### Session Management
| Tool | Description |
|------|-------------|
| `start_session` | Begin a session. Returns resume context (last snapshot, pinned items, rules). |
| `end_session` | Close with structured summary (decisions, files, next hints). |
| `save_snapshot` | Compaction checkpoint — goal, progress, blockers, next steps. |
| `get_resume_context` | Everything needed to resume: session, snapshot, rules, project summary. |

### Knowledge Management
| Tool | Description |
|------|-------------|
| `add_thought` | Store a thought (observation, decision, idea, pattern, note). |
| `update_thought` | Modify an existing thought. |
| `add_rule` | Learned pattern — do/don't/context-dependent with severity. |
| `reinforce_rule` | Bump a rule's confidence when re-confirmed. |
| `add_error_pattern` | Log a failure: what broke, why, how to fix. |
| `link_items` | Connect items (informs, contradicts, supersedes, related, caused_by). |

### Search & Retrieval
| Tool | Description |
|------|-------------|
| `search` | FTS5 full-text search across all tables with relevance scoring. |
| `search_by_embedding` | RAG-style vector similarity search (requires stored embeddings). |
| `store_embedding` | Store a vector embedding for an item. |
| `get_rules` | Get active rules for a context (project, severity, keywords). |
| `get_session_history` | Past sessions with summaries. |
| `get_related` | Items linked via the thought graph. |
| `get_project_summary` | Living project overview. |
| `update_project_summary` | Update project overview, tech stack, patterns, goals. |

### Groups & Maintenance
| Tool | Description |
|------|-------------|
| `create_group` | Create a named cluster (e.g., "authentication system"). |
| `add_to_group` | Add items to a group. |
| `remove_from_group` | Remove item from group. |
| `get_group` | Get group with all member details. |
| `pin_item` | Pin/unpin — pinned items always load in resume context. |
| `archive_item` | Archive — excluded from search by default. |

## AI Instructions

Add these instructions to your AI's system prompt or rules file:

```
You have access to memgram, a persistent memory system. Use it as follows:

SESSION LIFECYCLE:
- Call start_session at the beginning of every conversation
- Call get_rules when starting work on any file/project
- Call save_snapshot before any context compaction
- Call end_session with a summary when done

RECORDING KNOWLEDGE:
- Log important decisions with add_thought (type: decision)
- Log errors with add_error_pattern when something fails
- Create rules with add_rule when learning something generalizable
- Link related items with link_items

SEARCHING:
- Use search proactively before making decisions to check existing knowledge
- Use get_rules at the start of work to load relevant rules
- Use get_resume_context to pick up where the last session left off

MAINTENANCE:
- Pin critical thoughts/rules that should always be in context
- Reinforce rules when they prove correct again
- Update project summaries periodically
```

## Architecture

```
src/memgram/
├── server.py              # MCP server entry point (stdio)
├── models.py              # Data models
├── utils.py               # ID generation, timestamps
├── db/
│   ├── __init__.py        # create_db() factory
│   ├── base.py            # DatabaseBackend ABC + MemgramDB business logic
│   └── sqlite.py          # SQLite + FTS5 + sqlite-vec backend
└── tools/
    ├── __init__.py        # Tool registration & dispatch
    ├── sessions.py        # Session management tool definitions
    ├── knowledge.py       # Knowledge management tool definitions
    └── search.py          # Search/retrieval/groups/maintenance tool definitions
```

## Database

Default location: `~/.memgram/memgram.db`

11 tables: sessions, thoughts, rules, compaction_snapshots, thought_links, error_patterns, project_summaries, session_summaries, thought_groups, group_members, embedding_meta + a sqlite-vec virtual table for vector search.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMGRAM_DB_PATH` | `~/.memgram/memgram.db` | SQLite database path |
| `MEMGRAM_EMBEDDING_DIM` | `384` | Embedding vector dimensions |
# memgram
