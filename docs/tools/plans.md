# Plan Tools

Seven tools for organizing and tracking work with plans and tasks.

## `create_plan`

Create a plan to organize and track work. Plans have scope, priority, optional due dates, and can be pinned to a session.

Use cases: multi-session refactors, migration tracking, release prep, incident response, bug investigation, sprint breakdowns.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | **yes** | — | Plan title |
| `description` | string | no | — | Detailed plan description and goals |
| `scope` | string | no | `"project"` | `project`, `sprint`, `session`, `milestone`, or `custom` |
| `priority` | string | no | `"medium"` | `low`, `medium`, `high`, or `critical` |
| `session_id` | string | no | — | Pin this plan to a session |
| `project` | string | **yes** | — | Project tag |
| `branch` | string | no | — | Git branch name |
| `due_date` | string | no | — | Target completion date (ISO 8601) |
| `tags` | string[] | no | — | Tags for categorization |

**Branch support:** Yes

### Example Request

```json
{
  "title": "Migrate auth to OAuth2",
  "description": "Replace session-based auth with OAuth2 + PKCE",
  "scope": "project",
  "priority": "high",
  "project": "myapp",
  "branch": "feature/oauth",
  "tags": ["auth", "migration"]
}
```

## `update_plan`

Update a plan's title, description, status, priority, scope, due date, or tags.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `plan_id` | string | **yes** | — | Plan ID to update |
| `title` | string | no | — | New title |
| `description` | string | no | — | New description |
| `status` | string | no | — | `draft`, `active`, `paused`, `completed`, or `abandoned` |
| `scope` | string | no | — | `project`, `sprint`, `session`, `milestone`, or `custom` |
| `priority` | string | no | — | `low`, `medium`, `high`, or `critical` |
| `session_id` | string | no | — | Pin/re-pin to a session |
| `project` | string | no | — | Project tag |
| `branch` | string | no | — | Branch name |
| `due_date` | string | no | — | Due date (ISO 8601) |
| `tags` | string[] | no | — | Tags |

Only provided fields are updated.

## `get_plan`

Get a plan with all its tasks, progress counts, and status.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `plan_id` | string | **yes** | Plan ID |

## `list_plans`

List plans filtered by project, branch, session, or status. Returns plans sorted by priority then recency.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `session_id` | string | no | — | Filter by pinned session |
| `status` | string | no | — | `draft`, `active`, `paused`, `completed`, or `abandoned` |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes

## `add_plan_task`

Add a task to a plan. Tasks track individual work items with status, ordering, optional assignee, and dependencies on other tasks.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `plan_id` | string | **yes** | — | Plan to add task to |
| `title` | string | **yes** | — | Task title |
| `description` | string | no | — | Task details |
| `assignee` | string | no | — | Who is responsible |
| `depends_on` | string | no | — | Task ID this depends on |
| `position` | integer | no | auto | Sort position |

### Example Request

```json
{
  "plan_id": "p1a2b3c4d5e6",
  "title": "Set up OAuth provider config",
  "description": "Add Google and GitHub OAuth credentials",
  "assignee": "backend-team"
}
```

## `update_plan_task`

Update a plan task's status, title, description, assignee, or dependencies.

Status flow: `pending` -> `in_progress` -> `completed` (or `skipped`/`blocked`). Completed tasks automatically get a `completed_at` timestamp.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `task_id` | string | **yes** | — | Task ID to update |
| `title` | string | no | — | New title |
| `description` | string | no | — | New description |
| `status` | string | no | — | `pending`, `in_progress`, `completed`, `skipped`, or `blocked` |
| `assignee` | string | no | — | New assignee |
| `depends_on` | string | no | — | Task ID dependency |
| `position` | integer | no | — | New sort position |

## `delete_plan_task`

Remove a task from a plan.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `task_id` | string | **yes** | Task ID to delete |
