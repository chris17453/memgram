# Build Tools

Four tools for managing build records — tracking CI/CD pipeline executions.

Builds have status, trigger type, optional commit/branch info, artifact URLs, and duration tracking.

## `create_build`

Create a build record.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Build name or identifier |
| `project` | string | **yes** | — | Project tag |
| `pipeline` | string | no | — | Pipeline name or path |
| `status` | string | no | `"pending"` | `pending`, `running`, `passed`, `failed`, or `cancelled` |
| `trigger_type` | string | no | `"push"` | `push`, `pr`, `manual`, or `schedule` |
| `commit_sha` | string | no | — | Git commit SHA |
| `branch` | string | no | — | Git branch name |
| `artifact_url` | string | no | — | URL to build artifacts |
| `duration_seconds` | number | no | — | Build duration in seconds |
| `session_id` | string | no | — | Session ID |
| `started_at` | string | no | — | ISO 8601 timestamp |
| `finished_at` | string | no | — | ISO 8601 timestamp |
| `tags` | string[] | no | — | Tags |

**Branch support:** Yes

### Example Request

```json
{
  "name": "build-142",
  "project": "myapp",
  "pipeline": "ci/main",
  "status": "running",
  "trigger_type": "push",
  "commit_sha": "a1b2c3d4e5f6",
  "branch": "main",
  "tags": ["ci", "main"]
}
```

## `update_build`

Update a build's fields — status, artifact URL, duration, timestamps, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `build_id` | string | **yes** | Build ID to update |
| `name` | string | no | Build name |
| `project` | string | no | Project tag |
| `pipeline` | string | no | Pipeline name |
| `status` | string | no | `pending`, `running`, `passed`, `failed`, or `cancelled` |
| `trigger_type` | string | no | `push`, `pr`, `manual`, or `schedule` |
| `commit_sha` | string | no | Git commit SHA |
| `branch` | string | no | Branch name |
| `artifact_url` | string | no | Artifact URL |
| `duration_seconds` | number | no | Duration in seconds |
| `session_id` | string | no | Session ID |
| `started_at` | string | no | Start timestamp |
| `finished_at` | string | no | Finish timestamp |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_build`

Get a build record by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `build_id` | string | **yes** | Build ID |

## `list_builds`

List builds filtered by project, branch, status, or pipeline.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `status` | string | no | — | `pending`, `running`, `passed`, `failed`, or `cancelled` |
| `pipeline` | string | no | — | Filter by pipeline |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes
