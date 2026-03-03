---
title: Maintenance Tools
layout: default
parent: Tools Reference
nav_order: 6
---

# Maintenance Tools

Two tools for managing item lifecycle: pinning and archiving.

---

## `pin_item`

Pin or unpin a thought or rule. Pinned items are always loaded in resume context via `get_resume_context`.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `item_id` | string | **yes** | — | ID of the thought or rule |
| `pinned` | boolean | no | `true` | Set to `false` to unpin |

The tool searches both the `thoughts` and `rules` tables for the given ID.

### Example Request — Pin

```json
{
  "item_id": "r4d5e6f7",
  "pinned": true
}
```

### Example Request — Unpin

```json
{
  "item_id": "r4d5e6f7",
  "pinned": false
}
```

### Example Response

```json
{
  "id": "r4d5e6f7",
  "summary": "Always use state param in OAuth redirects",
  "pinned": 1,
  "updated_at": "2025-01-15T16:00:00+00:00"
}
```

Returns `{"error": "Item not found"}` if the ID doesn't match any thought or rule.

### Pinning Strategy

Use sparingly — pinned items consume token budget in every resume context. Good candidates:
- Architecture decisions that affect every session
- Critical security rules
- Key project conventions

---

## `archive_item`

Archive a thought or rule. Archived items are excluded from search results by default (unless `include_archived: true` is passed to `search`).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `item_id` | string | **yes** | — | ID of the thought or rule |

Archiving is a soft delete — the item remains in the database but is filtered out of normal operations. There is no unarchive tool; use `update_thought` with `archived: false` to restore a thought.

### Example Request

```json
{
  "item_id": "t9a8b7c6"
}
```

### Example Response

```json
{
  "id": "t9a8b7c6",
  "summary": "Outdated: Using session cookies for auth",
  "archived": 1,
  "updated_at": "2025-01-15T16:05:00+00:00"
}
```

Returns `{"error": "Item not found"}` if the ID doesn't match any thought or rule.
