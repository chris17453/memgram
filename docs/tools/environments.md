# Environment Tools

Four tools for managing environments — deployment targets like dev, staging, or production.

Environments track URLs, configuration, and type for a project.

## `create_environment`

Create an environment for a project.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Environment name (e.g. `prod-us-east`, `staging`) |
| `project` | string | **yes** | — | Project tag |
| `type` | string | no | `"development"` | `development`, `staging`, `production`, `testing`, or `local` |
| `url` | string | no | — | Base URL for this environment |
| `description` | string | no | — | Description |
| `config` | object | no | — | Arbitrary JSON configuration for this environment |
| `tags` | string[] | no | — | Tags |

### Example Request

```json
{
  "name": "prod-us-east",
  "project": "myapp",
  "type": "production",
  "url": "https://api.myapp.com",
  "description": "Primary production environment in US East",
  "tags": ["aws", "us-east-1"]
}
```

## `update_environment`

Update an environment's fields — name, type, url, description, config, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `environment_id` | string | **yes** | Environment ID to update |
| `name` | string | no | Environment name |
| `project` | string | no | Project tag |
| `type` | string | no | `development`, `staging`, `production`, `testing`, or `local` |
| `url` | string | no | Base URL |
| `description` | string | no | Description |
| `config` | object | no | JSON configuration |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_environment`

Get an environment by ID with its full configuration.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `environment_id` | string | **yes** | Environment ID |

## `list_environments`

List environments filtered by project or type.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `type` | string | no | — | `development`, `staging`, `production`, `testing`, or `local` |
| `limit` | integer | no | `50` | Max results |
