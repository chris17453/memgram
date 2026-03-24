# Maintenance & Health Tools

Four tools for managing item lifecycle, checking database health, and viewing agent contribution statistics.

## `pin_item`

Pin or unpin a thought or rule. Pinned items are always loaded in resume context via `get_resume_context`.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `item_id` | string | **yes** | — | ID of the thought or rule |
| `pinned` | boolean | no | `true` | Set to `false` to unpin |

The tool searches both the `thoughts` and `rules` tables for the given ID.

### Pinning Strategy

Use sparingly — pinned items consume token budget in every resume context. Good candidates:

- Architecture decisions that affect every session
- Critical security rules
- Key project conventions

## `archive_item`

Archive a thought or rule. Archived items are excluded from search results by default (unless `include_archived: true` is passed to `search`).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `item_id` | string | **yes** | — | ID of the thought or rule |

Archiving is a soft delete — the item remains in the database but is filtered out of normal operations. There is no unarchive tool; use `update_thought` with `archived: false` to restore a thought.

## `get_health`

Report database health: connectivity, WAL mode, foreign key status, vector availability, and per-table counts.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `include_counts` | boolean | no | `true` | When `false`, omits per-table row counts |

### Example Response

```json
{
  "backend": "sqlite",
  "journal_mode": "wal",
  "foreign_keys": 1,
  "vec_enabled": true,
  "counts": {
    "sessions": 12,
    "thoughts": 45,
    "rules": 8,
    "error_patterns": 2,
    "groups": 1,
    "links": 14,
    "projects": 3
  },
  "warnings": []
}
```

## `get_agent_stats`

Get contribution statistics broken down by AI agent type and model. Shows how many sessions, thoughts, rules, and error patterns each agent (Claude, Copilot, Codex, Cursor, etc.) has created.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter stats to a specific project (omit for global stats) |

### Example Response

```json
{
  "agents": [
    {
      "agent_type": "claude",
      "agent_model": "claude-sonnet-4",
      "sessions": 15,
      "thoughts": 42,
      "rules": 8,
      "errors": 3,
      "first_seen": "2025-01-15T10:30:00+00:00",
      "last_seen": "2025-03-16T14:22:00+00:00"
    },
    {
      "agent_type": "copilot",
      "agent_model": "gpt-4",
      "sessions": 7,
      "thoughts": 18,
      "rules": 2,
      "errors": 1,
      "first_seen": "2025-02-01T08:00:00+00:00",
      "last_seen": "2025-03-10T16:45:00+00:00"
    }
  ],
  "totals": {
    "total_agents": 2,
    "total_sessions": 22,
    "total_thoughts": 60,
    "total_rules": 10,
    "total_errors": 4
  },
  "project": null
}
```

### Agent Attribution

Every thought, rule, and error pattern now records which agent created it via `agent_type` and `agent_model` columns. These are:

- **Auto-resolved from the session** when a `session_id` is provided (the session's `agent_type` and `model` are copied to the item)
- **Explicitly provided** via `agent_type` and `agent_model` parameters on `add_thought`, `add_rule`, and `add_error_pattern`
- **Backfilled on upgrade** — existing items with a `session_id` are backfilled from their session's agent info during migration

### CLI

```bash
memgram agent-stats                    # Global stats
memgram agent-stats --project myapp    # Project-specific stats
```
