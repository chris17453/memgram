# Group Tools

Four tools for creating and managing named clusters of related items.

## `create_group`

Create a named group to cluster related items (e.g., "authentication system").

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Group name (normalized) |
| `description` | string | no | `""` | Group description |
| `project` | string | no | `null` | Project scope |
| `branch` | string | no | `null` | Branch scope |

**Branch support:** Yes

Group names are [normalized](../concepts/normalization.md), so `"Auth System"` and `"auth-system"` resolve to the same name.

### Example Request

```json
{
  "name": "auth-system",
  "description": "Everything about authentication",
  "project": "myapp"
}
```

## `add_to_group`

Add a thought, rule, or error pattern to a group. Duplicate additions are ignored.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `group_id` | string | **yes** | — | Group ID |
| `item_id` | string | **yes** | — | Item ID to add |
| `item_type` | string | **yes** | — | `thought`, `rule`, or `error_pattern` |

## `remove_from_group`

Remove an item from a group.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `group_id` | string | **yes** | — | Group ID |
| `item_id` | string | **yes** | — | Item ID to remove |

## `get_group`

Get a group and all its member items with full details. Look up by ID or by name (with optional project/branch scope).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `group_id` | string | no | `null` | Look up by ID |
| `name` | string | no | `null` | Look up by name (normalized) |
| `project` | string | no | `null` | Used with name lookup |
| `branch` | string | no | `null` | Used with name lookup |

Provide either `group_id` or `name` (with optional project/branch). If both are given, `group_id` takes precedence.

**Branch support:** Yes (for name-based lookup)

### Example Request

```json
{
  "name": "auth-system",
  "project": "myapp"
}
```

### Example Response

```json
{
  "id": "g1a2b3c4",
  "name": "authsystem",
  "description": "Everything about authentication",
  "project": "myapp",
  "members": [
    {
      "group_id": "g1a2b3c4",
      "item_id": "t1b2c3d4",
      "item_type": "thought",
      "detail": {
        "id": "t1b2c3d4",
        "summary": "Using PKCE flow for OAuth",
        "type": "decision"
      }
    },
    {
      "group_id": "g1a2b3c4",
      "item_id": "r4d5e6f7",
      "item_type": "rule",
      "detail": {
        "id": "r4d5e6f7",
        "summary": "Always use state param in OAuth",
        "severity": "critical"
      }
    }
  ]
}
```
