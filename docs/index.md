# Memgram — AI Memory Graph

A persistent memory layer for AI assistants, built as an [MCP](https://modelcontextprotocol.io/) server. Memgram gives any MCP-compatible AI (Copilot CLI, Claude Desktop, Claude Code, Cursor, etc.) the ability to remember thoughts, rules, decisions, and errors across sessions.

## Features

- **24 MCP tools** for storing and retrieving knowledge
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

## Quick Install

```bash
uv add memgram
memgram serve
```

See the [Getting Started](getting-started.md) guide for a full walkthrough.

## Navigation

| Section | Description |
|---------|-------------|
| [Getting Started](getting-started.md) | Install, setup, and your first session |
| [Concepts](concepts/index.md) | Scoping, normalization, scoring, knowledge graph |
| [Configuration](configuration/index.md) | CLI flags, env vars, MCP client configs |
| [Tools Reference](tools/index.md) | All 24 MCP tools with params and examples |
| [Data Model](data-model/index.md) | Database tables, schema, relationships |
| [Guides](guides/index.md) | AI instructions, session workflow, branch workflow, export |
| [Architecture](architecture.md) | Code structure, dispatch pipeline, extension points |
