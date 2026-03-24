# Spec Tools

Four tools for managing specifications — formal definitions of what needs to be built.

## `create_spec`

Create a specification with acceptance criteria, priority, status tracking, and links to features and people.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | **yes** | — | Spec title |
| `description` | string | no | — | Full spec content |
| `status` | string | no | `"draft"` | `draft`, `review`, `approved`, `implemented`, or `deprecated` |
| `priority` | string | no | `"medium"` | `low`, `medium`, `high`, or `critical` |
| `acceptance_criteria` | string[] | no | — | List of criteria that define "done" |
| `project` | string | **yes** | — | Project tag |
| `branch` | string | no | — | Git branch name |
| `session_id` | string | no | — | Session ID |
| `author_id` | string | no | — | Person ID of the spec author |
| `tags` | string[] | no | — | Tags |

**Branch support:** Yes

### Example Request

```json
{
  "title": "OAuth2 Login Flow",
  "description": "Users can log in via Google or GitHub OAuth2 with PKCE",
  "status": "draft",
  "priority": "high",
  "acceptance_criteria": [
    "Google OAuth login works end-to-end",
    "GitHub OAuth login works end-to-end",
    "Existing sessions are preserved on re-login"
  ],
  "project": "myapp"
}
```

## `update_spec`

Update a spec's fields — title, description, status, priority, acceptance criteria, author, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `spec_id` | string | **yes** | Spec ID to update |
| `title` | string | no | New title |
| `description` | string | no | New description |
| `status` | string | no | `draft`, `review`, `approved`, `implemented`, or `deprecated` |
| `priority` | string | no | `low`, `medium`, `high`, or `critical` |
| `acceptance_criteria` | string[] | no | Updated criteria |
| `project` | string | no | Project tag |
| `branch` | string | no | Branch name |
| `session_id` | string | no | Session ID |
| `author_id` | string | no | Person ID |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_spec`

Get a spec with its linked features.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `spec_id` | string | **yes** | Spec ID |

## `list_specs`

List specs filtered by project, branch, or status.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `status` | string | no | — | `draft`, `review`, `approved`, `implemented`, or `deprecated` |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes
