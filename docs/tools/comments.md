# Comment Tools

Four tools for adding threaded discussion comments to any entity.

Comments can be attached to any entity type (person, team, component, feature, spec, plan, thought, rule, error_pattern, ticket, endpoint, credential, environment, deployment, build, incident, dependency, runbook, decision, instruction). Supports nested threading via `parent_id`.

## `add_comment`

Add a threaded comment to any entity.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `entity_id` | string | **yes** | — | ID of the entity to comment on |
| `entity_type` | string | **yes** | — | Type of entity (see supported types below) |
| `content` | string | **yes** | — | Comment body (plain text or markdown) |
| `author` | string | no | — | Who wrote the comment (e.g. username, agent name) |
| `parent_id` | string | no | — | Parent comment ID for threaded replies |
| `project` | string | no | — | Project scope |
| `tags` | string[] | no | — | Tags |

### Supported Entity Types

`person`, `team`, `component`, `feature`, `spec`, `plan`, `thought`, `rule`, `error_pattern`, `ticket`, `endpoint`, `credential`, `environment`, `deployment`, `build`, `incident`, `dependency`, `runbook`, `decision`, `instruction`

### Example Request

```json
{
  "entity_id": "a1b2c3d4e5f6",
  "entity_type": "ticket",
  "content": "Reproduced this on staging — the CSRF token is missing from the redirect URL",
  "author": "alice",
  "project": "myapp",
  "tags": ["investigation"]
}
```

## `update_comment`

Update an existing comment's content, author, or tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `comment_id` | string | **yes** | Comment ID to update |
| `content` | string | no | New comment body |
| `author` | string | no | Updated author |
| `tags` | string[] | no | Replacement tag list |

Only provided fields are updated.

## `get_comments`

Retrieve comments for an entity. Returns threaded structure (top-level and replies).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `entity_id` | string | **yes** | — | ID of the entity whose comments to fetch |
| `entity_type` | string | no | — | Type of entity (narrows search if entity_id is reused) |
| `project` | string | no | — | Filter by project scope |
| `limit` | integer | no | `50` | Max comments to return |

## `delete_comment`

Delete a comment by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `comment_id` | string | **yes** | Comment ID to delete |
