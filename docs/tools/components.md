# Component Tools

Four tools for defining system components — services, modules, libraries, APIs, UI elements, databases, and infrastructure.

## `create_component`

Define a system component with an owner, tech stack, and links to features and specs via `link_items`.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Component name |
| `description` | string | no | — | What this component does |
| `type` | string | no | `"module"` | `service`, `module`, `library`, `api`, `ui`, `database`, or `infrastructure` |
| `project` | string | **yes** | — | Project tag |
| `branch` | string | no | — | Git branch name |
| `owner_id` | string | no | — | Person ID who owns this component |
| `tech_stack` | string[] | no | — | Technologies used (e.g. `["python", "fastapi", "postgres"]`) |
| `tags` | string[] | no | — | Tags |

**Branch support:** Yes

### Example Request

```json
{
  "name": "Auth Service",
  "description": "Handles OAuth2 login, token refresh, and session management",
  "type": "service",
  "project": "myapp",
  "owner_id": "p1a2b3c4d5e6",
  "tech_stack": ["python", "fastapi", "jwt"]
}
```

## `update_component`

Update a component's fields — name, description, type, owner, tech stack, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `component_id` | string | **yes** | Component ID to update |
| `name` | string | no | New name |
| `description` | string | no | New description |
| `type` | string | no | `service`, `module`, `library`, `api`, `ui`, `database`, or `infrastructure` |
| `project` | string | no | Project tag |
| `branch` | string | no | Branch name |
| `owner_id` | string | no | Person ID |
| `tech_stack` | string[] | no | Technologies |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_component`

Get a component with its links to features, people, and other entities.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `component_id` | string | **yes** | Component ID |

## `list_components`

List components filtered by project, branch, type, or owner.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `type` | string | no | — | `service`, `module`, `library`, `api`, `ui`, `database`, or `infrastructure` |
| `owner_id` | string | no | — | Filter by owner person ID |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes
