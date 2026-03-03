# Getting Started

This guide walks you through installing memgram, configuring it with your AI client, and running your first session.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** package manager (recommended) or pip
- An MCP-compatible AI client (VS Code/Copilot, Claude Desktop, Claude Code, Cursor)

## Installation

```bash
# Using uv (recommended)
uv add memgram

# Or with pip
pip install memgram
```

## Running the Server

Memgram runs as an MCP server over stdio. Your AI client starts it automatically, but you can also run it directly:

```bash
# Default — runs the MCP server over stdio
memgram serve

# Short form (serve is the default subcommand)
memgram

# Custom database path
memgram --db-path /path/to/memgram.db serve

# Custom embedding dimensions (default: 384)
memgram serve --embedding-dim 1536
```

The database is created automatically at `~/.memgram/memgram.db` on first run.

## MCP Client Setup

Add memgram to your AI client's MCP configuration. See the [MCP Clients](configuration/mcp-clients.md) page for full configs.

**Quick example (Claude Code):**

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

## First Session Walkthrough

Once configured, your AI assistant has access to all 24 memgram tools. A typical first session looks like:

### 1. Start a session

The AI calls `start_session` with its agent type, model, and your project info:

```json
{
  "agent_type": "copilot",
  "model": "claude-sonnet-4",
  "project": "myapp",
  "branch": "main",
  "goal": "Initial setup and architecture decisions"
}
```

This returns a session ID and any existing resume context (empty on first run).

### 2. Record knowledge as you work

As the AI makes decisions and observations, it stores them:

```json
{ "tool": "add_thought", "summary": "Using FastAPI for the REST API", "type": "decision" }
{ "tool": "add_rule", "summary": "Always use type hints", "type": "do", "severity": "critical" }
{ "tool": "add_error_pattern", "error_description": "Import failed", "cause": "Missing dep", "fix": "Added to pyproject.toml" }
```

### 3. Save snapshots before compaction

When the context window gets long:

```json
{
  "tool": "save_snapshot",
  "session_id": "abc123",
  "current_goal": "Setting up project structure",
  "progress_summary": "Created FastAPI app, added auth routes",
  "next_steps": ["Add database models", "Write tests"]
}
```

### 4. End the session

```json
{
  "tool": "end_session",
  "session_id": "abc123",
  "summary": "Set up project with FastAPI, JWT auth, and basic routes",
  "files_modified": ["src/main.py", "src/auth.py", "src/routes.py"]
}
```

### 5. Next session picks up where you left off

When a new conversation starts, `start_session` returns the previous session summary, last snapshot, pinned items, and active rules — so the AI has full context.

## Next Steps

- Learn about [scoping](concepts/scoping.md) to organize knowledge by project and branch
- See the full [tools reference](tools/index.md) for all 24 tools
- Read the [AI instructions guide](guides/ai-instructions.md) for the complete agent usage guide
