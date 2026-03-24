# People Tools

Four tools for managing people in the knowledge graph — team members, contributors, stakeholders, and contacts.

People can own components, lead features, author specs, and be assigned to plan tasks.

## `add_person`

Add a person to the knowledge graph with role, skills, and contact info.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Person's name |
| `type` | string | no | `"individual"` | `individual`, `contractor`, or `team_member` |
| `role` | string | no | — | Role (engineer, designer, pm, lead, devops, etc.) |
| `email` | string | no | — | Email address |
| `github` | string | no | — | GitHub username |
| `skills` | string[] | no | — | Skills and expertise areas |
| `notes` | string | no | — | Additional notes |

### Example Request

```json
{
  "name": "Alice Chen",
  "type": "team_member",
  "role": "engineer",
  "github": "alicechen",
  "skills": ["python", "fastapi", "oauth"]
}
```

## `update_person`

Update a person's fields — name, type, role, email, github, skills, notes.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `person_id` | string | **yes** | Person ID to update |
| `name` | string | no | New name |
| `type` | string | no | `individual`, `contractor`, or `team_member` |
| `role` | string | no | New role |
| `email` | string | no | Email |
| `github` | string | no | GitHub username |
| `skills` | string[] | no | Skills |
| `notes` | string | no | Notes |

Only provided fields are updated.

## `get_person`

Get a person with everything they own, lead, and authored — components, features, specs, and team memberships.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `person_id` | string | **yes** | Person ID |

## `list_people`

List people, optionally filtered by role.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `role` | string | no | — | Filter by role |
| `limit` | integer | no | `100` | Max results |
