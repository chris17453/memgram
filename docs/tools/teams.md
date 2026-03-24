# Team Tools

Six tools for managing teams — groups of people who work together.

Teams can own components, lead features, and be scoped to projects.

## `create_team`

Create a team with a lead and project scope. Add members with `add_team_member`.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Team name |
| `description` | string | no | — | What this team does |
| `project` | string | **yes** | — | Project scope |
| `lead_id` | string | no | — | Person ID of the team lead |
| `tags` | string[] | no | — | Tags |

**Branch support:** Yes (via `project`)

### Example Request

```json
{
  "name": "Auth Team",
  "description": "Owns authentication, authorization, and identity",
  "project": "myapp",
  "lead_id": "p1a2b3c4d5e6"
}
```

## `update_team`

Update a team's fields — name, description, project, lead, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id` | string | **yes** | Team ID to update |
| `name` | string | no | New name |
| `description` | string | no | New description |
| `project` | string | no | Project tag |
| `lead_id` | string | no | Person ID |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_team`

Get a team with all its members and their details.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id` | string | **yes** | Team ID |

## `list_teams`

List teams, optionally filtered by project.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes (via `project`)

## `add_team_member`

Add a person to a team with a role.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | **yes** | — | Team ID |
| `person_id` | string | **yes** | — | Person ID to add |
| `role` | string | no | `"member"` | `member`, `lead`, or `contributor` |

### Example Request

```json
{
  "team_id": "t1a2b3c4d5e6",
  "person_id": "p1a2b3c4d5e6",
  "role": "lead"
}
```

## `remove_team_member`

Remove a person from a team.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `team_id` | string | **yes** | Team ID |
| `person_id` | string | **yes** | Person ID to remove |
