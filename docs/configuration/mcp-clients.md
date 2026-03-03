# MCP Client Configuration

Memgram works with any MCP-compatible AI client. Below are configuration examples for the most common clients.

## Copilot CLI / VS Code

Add to your MCP settings (`.vscode/mcp.json` or global settings):

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

## Claude Desktop

Add to `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

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

## Claude Code

Add to `.claude/settings.json` (global) or project-level `.mcp.json`:

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

## Notes

- Replace `/path/to/memgram` with the actual path to your memgram installation
- The `MEMGRAM_DB_PATH` env var is optional — defaults to `~/.memgram/memgram.db`
- All clients start the server over stdio automatically — you don't need to run `memgram serve` manually
- The same database can be shared across multiple clients (SQLite WAL mode supports concurrent readers)
