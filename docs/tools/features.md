# Feature Tools

Four tools for tracking features — distinct capabilities or user-facing functionality.

## `create_feature`

Define a feature that can be linked to a spec, assigned a lead person, and connected to components via `link_items`. Track status from proposed through shipped.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Feature name |
| `description` | string | no | — | What this feature does |
| `status` | string | no | `"proposed"` | `proposed`, `in_progress`, `completed`, `shipped`, or `deprecated` |
| `priority` | string | no | `"medium"` | `low`, `medium`, `high`, or `critical` |
| `spec_id` | string | no | — | Spec this feature implements |
| `project` | string | **yes** | — | Project tag |
| `branch` | string | no | — | Git branch name |
| `session_id` | string | no | — | Session ID |
| `lead_id` | string | no | — | Person ID of the feature lead |
| `tags` | string[] | no | — | Tags |

**Branch support:** Yes

### Example Request

```json
{
  "name": "Google OAuth Login",
  "description": "Users can sign in with their Google account",
  "status": "in_progress",
  "priority": "high",
  "spec_id": "s1a2b3c4d5e6",
  "project": "myapp",
  "branch": "feature/oauth"
}
```

## `update_feature`

Update a feature's fields — name, description, status, priority, spec, lead, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `feature_id` | string | **yes** | Feature ID to update |
| `name` | string | no | New name |
| `description` | string | no | New description |
| `status` | string | no | `proposed`, `in_progress`, `completed`, `shipped`, or `deprecated` |
| `priority` | string | no | `low`, `medium`, `high`, or `critical` |
| `spec_id` | string | no | Spec ID |
| `project` | string | no | Project tag |
| `branch` | string | no | Branch name |
| `session_id` | string | no | Session ID |
| `lead_id` | string | no | Person ID |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_feature`

Get a feature with its links to components, specs, and other entities.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `feature_id` | string | **yes** | Feature ID |

## `list_features`

List features filtered by project, branch, status, or spec.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `status` | string | no | — | `proposed`, `in_progress`, `completed`, `shipped`, or `deprecated` |
| `spec_id` | string | no | — | Filter by parent spec |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes
