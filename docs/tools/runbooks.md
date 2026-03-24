# Runbook Tools

Four tools for managing runbooks — step-by-step operational procedures for a project.

Runbooks capture repeatable processes like deployments, incident response, or maintenance tasks with ordered steps and trigger conditions.

## `create_runbook`

Create a runbook with ordered steps.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | **yes** | — | Runbook title |
| `project` | string | **yes** | — | Project tag |
| `description` | string | no | — | Overview of what this runbook covers |
| `steps` | object[] | no | — | Ordered list of step objects (each with `order`, `title`, `command`, `notes`) |
| `trigger_conditions` | string | no | — | When this runbook should be executed |
| `last_executed` | string | no | — | ISO timestamp of last execution |
| `tags` | string[] | no | — | Tags |

### Step Object

| Field | Type | Description |
|-------|------|-------------|
| `order` | integer | Step order (1-based) |
| `title` | string | Short step title |
| `command` | string | Command to run, if applicable |
| `notes` | string | Additional context or warnings |

### Example Request

```json
{
  "title": "Production Deployment",
  "project": "myapp",
  "description": "Steps to deploy a new release to production",
  "steps": [
    {"order": 1, "title": "Run tests", "command": "make test", "notes": "All tests must pass"},
    {"order": 2, "title": "Build image", "command": "docker build -t myapp:latest ."},
    {"order": 3, "title": "Deploy canary", "command": "kubectl apply -f canary.yaml", "notes": "Monitor for 10 minutes"}
  ],
  "trigger_conditions": "On every version bump to main",
  "tags": ["deploy", "production"]
}
```

## `update_runbook`

Update a runbook's fields — title, description, steps, trigger conditions, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `runbook_id` | string | **yes** | Runbook ID to update |
| `title` | string | no | New title |
| `project` | string | no | Project tag |
| `description` | string | no | Description |
| `steps` | object[] | no | Replacement steps list |
| `trigger_conditions` | string | no | Trigger conditions |
| `last_executed` | string | no | Last execution timestamp |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_runbook`

Get a runbook by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `runbook_id` | string | **yes** | Runbook ID |

## `list_runbooks`

List runbooks filtered by project.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `limit` | integer | no | `50` | Max results |
