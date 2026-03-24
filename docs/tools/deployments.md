# Deployment Tools

Four tools for tracking deployments — version releases across environments.

Deployments have strategy, status tracking, and can be linked to projects, branches, and sessions. Use `rollback_to` to reference a previous deployment ID.

## `create_deployment`

Record a deployment.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `version` | string | **yes** | — | Version being deployed (e.g. `v1.2.3`) |
| `project` | string | **yes** | — | Project tag |
| `environment_id` | string | no | — | Target environment identifier (e.g. production, staging) |
| `status` | string | no | `"pending"` | `pending`, `deploying`, `deployed`, `failed`, or `rolled_back` |
| `strategy` | string | no | `"rolling"` | `rolling`, `canary`, `blue_green`, or `recreate` |
| `description` | string | no | — | Deployment notes or changelog summary |
| `branch` | string | no | — | Git branch name |
| `session_id` | string | no | — | Session ID |
| `deployed_by` | string | no | — | Person ID or name of who triggered the deploy |
| `rollback_to` | string | no | — | Deployment ID this is rolling back to |
| `deployed_at` | string | no | now | ISO timestamp of deploy |
| `tags` | string[] | no | — | Tags |

**Branch support:** Yes

### Example Request

```json
{
  "version": "v1.2.3",
  "project": "myapp",
  "environment_id": "env-prod-us-east",
  "status": "deploying",
  "strategy": "canary",
  "description": "Release with OAuth2 login flow",
  "branch": "main",
  "tags": ["release", "oauth"]
}
```

## `update_deployment`

Update a deployment's fields — status, description, strategy, tags, etc.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `deployment_id` | string | **yes** | Deployment ID to update |
| `version` | string | no | Version |
| `project` | string | no | Project tag |
| `environment_id` | string | no | Target environment |
| `status` | string | no | `pending`, `deploying`, `deployed`, `failed`, or `rolled_back` |
| `strategy` | string | no | `rolling`, `canary`, `blue_green`, or `recreate` |
| `description` | string | no | Description |
| `branch` | string | no | Branch name |
| `session_id` | string | no | Session ID |
| `deployed_by` | string | no | Who triggered the deploy |
| `rollback_to` | string | no | Deployment ID to roll back to |
| `deployed_at` | string | no | Deploy timestamp |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_deployment`

Get a deployment by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `deployment_id` | string | **yes** | Deployment ID |

## `list_deployments`

List deployments filtered by project, branch, status, or environment.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `status` | string | no | — | `pending`, `deploying`, `deployed`, `failed`, or `rolled_back` |
| `environment_id` | string | no | — | Filter by environment |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes
