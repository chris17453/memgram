# Dependency Tools

Four tools for tracking project dependencies — libraries, services, databases, APIs, and tools that a project relies on.

Record version info, license, and source to keep your dependency inventory current.

## `create_dependency`

Track a project dependency.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Dependency name (e.g. `react`, `postgres`) |
| `project` | string | **yes** | — | Project tag |
| `version` | string | no | — | Currently used version |
| `type` | string | no | `"library"` | `library`, `service`, `database`, `api`, or `tool` |
| `source` | string | no | — | Where it comes from (e.g. npm, pypi, URL) |
| `license` | string | no | — | License identifier (e.g. MIT, Apache-2.0) |
| `description` | string | no | — | What this dependency does / why it's needed |
| `pinned_version` | string | no | — | Pinned/locked version if different from version |
| `latest_version` | string | no | — | Latest known available version |
| `tags` | string[] | no | — | Tags |

### Example Request

```json
{
  "name": "react",
  "project": "myapp",
  "version": "18.2.0",
  "type": "library",
  "source": "npm",
  "license": "MIT",
  "description": "UI rendering library",
  "latest_version": "18.3.1",
  "tags": ["frontend", "ui"]
}
```

## `update_dependency`

Update a dependency's fields — version, type, source, license, description, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dependency_id` | string | **yes** | Dependency ID to update |
| `name` | string | no | Dependency name |
| `project` | string | no | Project tag |
| `version` | string | no | Current version |
| `type` | string | no | `library`, `service`, `database`, `api`, or `tool` |
| `source` | string | no | Source |
| `license` | string | no | License identifier |
| `description` | string | no | Description |
| `pinned_version` | string | no | Pinned version |
| `latest_version` | string | no | Latest available version |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_dependency`

Get a dependency by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dependency_id` | string | **yes** | Dependency ID |

## `list_dependencies`

List dependencies filtered by project or type.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `type` | string | no | — | `library`, `service`, `database`, `api`, or `tool` |
| `limit` | integer | no | `50` | Max results |
