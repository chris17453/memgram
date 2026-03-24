# Ticket Tools

Four tools for tracking bugs, tasks, features, improvements, and questions with auto-generated ticket numbers.

Tickets get auto-numbered per project (e.g. `MYAPP-1`, `MYAPP-2`). They can be assigned to people, linked to projects/branches/sessions, and organized into parent/child hierarchies for sub-tasks.

## `create_ticket`

Create a ticket with an auto-generated ticket number.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | **yes** | — | Ticket title |
| `description` | string | no | `""` | Detailed description |
| `status` | string | no | `"open"` | `open`, `in_progress`, `review`, `resolved`, `closed`, or `wontfix` |
| `priority` | string | no | `"medium"` | `low`, `medium`, `high`, or `critical` |
| `type` | string | no | `"task"` | `bug`, `task`, `feature`, `improvement`, or `question` |
| `ticket_number` | string | no | auto | Custom ticket number (auto-generated if omitted) |
| `assignee_id` | string | no | — | Person ID to assign to |
| `reporter_id` | string | no | — | Person ID who reported this |
| `project` | string | **yes** | — | Project tag (used for ticket number prefix) |
| `branch` | string | no | — | Git branch name |
| `session_id` | string | no | — | Session ID |
| `parent_id` | string | no | — | Parent ticket ID for sub-tickets |
| `tags` | string[] | no | — | Tags |
| `due_date` | string | no | — | Due date (ISO 8601) |

**Branch support:** Yes

### Ticket Numbering

Ticket numbers are auto-generated from the project name:
- Project `myapp` → `MYAPP-1`, `MYAPP-2`, ...
- No project → `MG-1`, `MG-2`, ...
- You can override with `ticket_number` for custom numbering

### Example Request

```json
{
  "title": "OAuth callback fails with CSRF error",
  "description": "The OAuth callback endpoint returns 403 when state param is missing",
  "type": "bug",
  "priority": "high",
  "project": "myapp",
  "assignee_id": "p1a2b3c4d5e6",
  "tags": ["auth", "oauth", "bug"]
}
```

### Example Response

```json
{
  "id": "a1b2c3d4e5f6",
  "ticket_number": "MYAPP-1",
  "title": "OAuth callback fails with CSRF error",
  "status": "open",
  "priority": "high",
  "type": "bug",
  "project": "myapp"
}
```

## `update_ticket`

Update a ticket's fields. `resolved_at` is auto-set when status moves to `resolved` or `closed`, and cleared when re-opened.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `ticket_id` | string | **yes** | Ticket ID to update |
| `title` | string | no | New title |
| `description` | string | no | New description |
| `status` | string | no | `open`, `in_progress`, `review`, `resolved`, `closed`, or `wontfix` |
| `priority` | string | no | `low`, `medium`, `high`, or `critical` |
| `type` | string | no | `bug`, `task`, `feature`, `improvement`, or `question` |
| `assignee_id` | string | no | Person ID |
| `reporter_id` | string | no | Person ID |
| `project` | string | no | Project tag |
| `branch` | string | no | Branch name |
| `session_id` | string | no | Session ID |
| `parent_id` | string | no | Parent ticket ID |
| `tags` | string[] | no | Tags |
| `due_date` | string | no | Due date |

### Status Flow

```
open → in_progress → review → resolved → closed
                                  ↘ wontfix
```

## `get_ticket`

Get a ticket by ID or ticket number. Returns the ticket with its sub-tickets and attachments.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `ticket_id` | string | no | Ticket ID |
| `ticket_number` | string | no | Ticket number (e.g. `MYAPP-42`) |

Provide either `ticket_id` or `ticket_number`.

## `list_tickets`

List tickets filtered by project, branch, status, assignee, type, or parent. Returns tickets sorted by priority then recency.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `status` | string | no | — | Filter by status |
| `assignee_id` | string | no | — | Filter by assignee |
| `type` | string | no | — | Filter by type |
| `parent_id` | string | no | — | Filter by parent ticket (list sub-tickets) |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes
