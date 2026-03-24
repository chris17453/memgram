# Decision Tools

Four tools for recording architectural and design decisions — capturing context, options considered, outcome, and consequences.

Decisions track status from proposed through accepted to deprecated/superseded, forming a decision log for the project.

## `create_decision`

Record an architectural or design decision.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | **yes** | — | Decision title |
| `project` | string | **yes** | — | Project tag |
| `status` | string | no | `"proposed"` | `proposed`, `accepted`, `deprecated`, or `superseded` |
| `context` | string | no | — | Background and motivation for this decision |
| `options` | string[] | no | — | Options that were considered |
| `outcome` | string | no | — | The chosen option and rationale |
| `consequences` | string | no | — | Known consequences of this decision |
| `branch` | string | no | — | Git branch name |
| `session_id` | string | no | — | Session ID |
| `author_id` | string | no | — | Person ID of the decision author |
| `superseded_by` | string | no | — | Decision ID that supersedes this one |
| `decided_at` | string | no | — | ISO timestamp when the decision was made |
| `tags` | string[] | no | — | Tags |

**Branch support:** Yes

### Example Request

```json
{
  "title": "Use PostgreSQL over MongoDB",
  "project": "myapp",
  "status": "accepted",
  "context": "Need a primary database for user and transaction data",
  "options": ["PostgreSQL", "MongoDB", "CockroachDB"],
  "outcome": "PostgreSQL — strong ACID guarantees, team expertise, and mature ecosystem",
  "consequences": "Need to manage schema migrations; no native document storage",
  "tags": ["database", "architecture"]
}
```

## `update_decision`

Update a decision's fields — status, context, options, outcome, consequences, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `decision_id` | string | **yes** | Decision ID to update |
| `title` | string | no | New title |
| `project` | string | no | Project tag |
| `status` | string | no | `proposed`, `accepted`, `deprecated`, or `superseded` |
| `context` | string | no | Context |
| `options` | string[] | no | Options considered |
| `outcome` | string | no | Chosen outcome |
| `consequences` | string | no | Consequences |
| `branch` | string | no | Branch name |
| `session_id` | string | no | Session ID |
| `author_id` | string | no | Author person ID |
| `superseded_by` | string | no | Superseding decision ID |
| `decided_at` | string | no | Decision timestamp |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_decision`

Get a decision record by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `decision_id` | string | **yes** | Decision ID |

## `list_decisions`

List decisions filtered by project, branch, or status.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `status` | string | no | — | `proposed`, `accepted`, `deprecated`, or `superseded` |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes
