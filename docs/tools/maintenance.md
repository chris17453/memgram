# Maintenance Tools

Two tools for managing item lifecycle: pinning and archiving.

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
