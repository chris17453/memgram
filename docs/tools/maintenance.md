# Maintenance & Health Tools

Three tools for managing item lifecycle and checking database health.

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
