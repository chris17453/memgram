# CLI Reference

Memgram provides five subcommands: `serve` (default), `export`, `migrate-exports`, `list-projects`, `merge-projects`, and `rename-project`.

## Usage

```
memgram [--db-path PATH] <command> [options]
```

Global flags go **before** the subcommand. Subcommand-specific flags go **after**.

## Global Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--db-path PATH` | `~/.memgram/memgram.db` | Path to the SQLite database |

## Subcommands

### `serve`

Run the MCP server over stdio. This is the **default** subcommand — if you run `memgram` with no subcommand, it runs `serve`.

```bash
memgram serve
memgram                          # same as above
memgram serve --embedding-dim 1536
memgram --db-path /tmp/test.db serve
```

| Flag | Default | Description |
|------|---------|-------------|
| `--embedding-dim N` | `384` | Embedding vector dimensions for sqlite-vec |

The embedding dimension should match your embedding model:

- `384` — all-MiniLM-L6-v2 (default)
- `1536` — OpenAI text-embedding-3-small
- `3072` — OpenAI text-embedding-3-large

### `export`

Export the entire database as a tree of linked markdown files.

```bash
memgram export
memgram export -o ./my-export
memgram --db-path /tmp/test.db export -o ./my-export
```

| Flag | Default | Description |
|------|---------|-------------|
| `-o`, `--output DIR` | `memgram-export` | Output directory |

See the [Export guide](../guides/export.md) for details on the slugged output structure.

### `migrate-exports`

Rewrite legacy ID-based export filenames to human-readable slugs and fix links in place.

```bash
memgram migrate-exports
memgram migrate-exports -i ./memgram-export
```

| Flag | Default | Description |
|------|---------|-------------|
| `-i`, `--input DIR` | `memgram-export` | Existing export directory to migrate |

Idempotent — re-running is safe; only legacy filenames are rewritten.

### `list-projects`

List all projects with counts, including projects that only exist in data tables (no summary).

```bash
memgram list-projects
memgram list-projects --db-path /tmp/test.db
```

### `merge-projects`

Merge all data from a source project into a target project (useful for typo cleanup).

```bash
memgram merge-projects oxide-os oxideos
memgram merge-projects oldname newname --db-path /tmp/test.db
```

### `rename-project`

Rename a project; if the target already exists, the data is merged.

```bash
memgram rename-project oxide-os-oxide- oxideos
memgram rename-project oldname newname --db-path /tmp/test.db
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMGRAM_DB_PATH` | `~/.memgram/memgram.db` | SQLite database path (overridden by `--db-path`) |
| `MEMGRAM_EMBEDDING_DIM` | `384` | Embedding vector dimensions (overridden by `--embedding-dim`) |

Environment variables are checked at startup. CLI flags take precedence.

## Database Location

The default database path is `~/.memgram/memgram.db`. The parent directory is created automatically on first run.

Priority order:

1. `--db-path` CLI flag (highest)
2. `MEMGRAM_DB_PATH` environment variable
3. `~/.memgram/memgram.db` (default)
