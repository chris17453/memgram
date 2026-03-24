# Instruction Tools

Four tools for managing agent instructions — behavioral rules and usage guidance stored in the database.

Instructions replace static `INSTRUCTIONS.md` files with a database-backed, scoped, sectional system. Agents can query their instructions at session start and instructions can be managed without editing files.

## `get_instructions`

Get all active instructions for the current context. Returns instructions sorted by priority (critical first), then position, filtered by project and branch scope. Global instructions are always included.

Call this at session start to understand how to use memgram and what behavioral rules to follow.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project (includes project-scoped + global) |
| `branch` | string | no | — | Filter by branch (includes branch + project + global) |
| `section` | string | no | — | Get a specific section only (by slug) |
| `include_global` | boolean | no | `true` | Include global instructions |

### Scope Resolution

Instructions are returned based on scope hierarchy:

- **Global** — always included (unless `include_global` is false)
- **Project** — included when `project` is specified
- **Branch** — included when both `project` and `branch` are specified

### Example Response

```json
{
  "count": 3,
  "instructions": [
    {
      "id": "a1b2c3d4e5f6",
      "section": "session-lifecycle",
      "title": "Session Lifecycle",
      "content": "### Starting Work\n\nAt the very beginning...",
      "position": 0,
      "scope": "global",
      "active": 1
    },
    {
      "id": "b2c3d4e5f6a1",
      "section": "auth-rules",
      "title": "Auth Rules",
      "content": "Always use PKCE for OAuth...",
      "position": 0,
      "scope": "project",
      "project": "myapp"
    }
  ]
}
```

## `create_instruction`

Create a new instruction section.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `section` | string | **yes** | — | Section slug (e.g. `session-lifecycle`) |
| `title` | string | **yes** | — | Display title (e.g. `Session Lifecycle`) |
| `content` | string | **yes** | — | Markdown instruction content |
| `position` | integer | no | auto | Sort order within same priority |
| `priority` | string | no | `"medium"` | `critical`, `high`, `medium`, or `low` — critical instructions are returned first |
| `scope` | string | no | `"global"` | `global`, `project`, or `branch` |
| `project` | string | no | — | Project tag (required for project/branch scope) |
| `branch` | string | no | — | Branch name (required for branch scope) |
| `tags` | string[] | no | — | Tags for categorization |

### Example Request

```json
{
  "section": "auth-rules",
  "title": "Authentication Rules",
  "content": "Always use PKCE for OAuth flows.\nNever store tokens in localStorage.",
  "scope": "project",
  "project": "myapp",
  "tags": ["auth", "security"]
}
```

## `update_instruction`

Update an instruction section's title, content, position, scope, or active status.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `instruction_id` | string | **yes** | Instruction ID to update |
| `title` | string | no | New title |
| `content` | string | no | New content |
| `section` | string | no | New section slug |
| `position` | integer | no | New sort position |
| `priority` | string | no | `critical`, `high`, `medium`, or `low` |
| `scope` | string | no | `global`, `project`, or `branch` |
| `project` | string | no | Project tag |
| `branch` | string | no | Branch name |
| `active` | boolean | no | Set false to deactivate |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `list_instruction_sections`

List all instruction section names and titles for a given scope, without full content. Useful for seeing what instruction topics exist.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |

## CLI: Seeding Instructions

Import instructions from a markdown file:

```bash
# Seed from INSTRUCTIONS.md (default) as global instructions
memgram seed-instructions

# Seed from a custom file
memgram seed-instructions -f ./my-instructions.md

# Seed as project-scoped instructions
memgram seed-instructions -f ./project-rules.md --scope project --project myapp

# Replace existing instructions before seeding
memgram seed-instructions --replace
```

The seeder splits the markdown on `## ` headings and creates one instruction section per heading.
