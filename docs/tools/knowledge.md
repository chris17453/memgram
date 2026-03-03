# Knowledge Tools

Six tools for storing and connecting knowledge: thoughts, rules, error patterns, and links.

## `add_thought`

Store a thought, observation, decision, idea, or note. Use this to record anything worth remembering across sessions.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `summary` | string | **yes** | — | Short searchable summary |
| `content` | string | no | `""` | Full detailed content |
| `type` | string | no | `"note"` | One of: `observation`, `decision`, `idea`, `error`, `pattern`, `note` |
| `session_id` | string | no | `null` | Current session ID |
| `project` | string | no | `null` | Project tag |
| `branch` | string | no | `null` | Git branch name |
| `keywords` | string[] | no | `[]` | Keywords for search |
| `associated_files` | string[] | no | `[]` | Related file paths |
| `pinned` | boolean | no | `false` | Pin to always load in context |

**Branch support:** Yes

### Thought Types

| Type | When to Use | Example |
|------|-------------|---------|
| `decision` | Chose one approach over another | "Using JWT over session cookies" |
| `observation` | Noticed something about the codebase | "Auth module has no test coverage" |
| `pattern` | Identified a recurring pattern | "All endpoints use same error format" |
| `idea` | Something to consider later | "Could add connection pooling" |
| `note` | General knowledge | "CI pipeline takes ~3 minutes" |
| `error` | Something went wrong (prefer `add_error_pattern` for structured version) | "Build failed due to missing stub" |

### Example Request

```json
{
  "summary": "Using PKCE flow for OAuth",
  "content": "Chose PKCE over implicit flow for better security in SPA",
  "type": "decision",
  "session_id": "a1b2c3d4e5f6",
  "project": "myapp",
  "branch": "feature/auth",
  "keywords": ["auth", "oauth", "pkce"],
  "associated_files": ["src/auth/oauth.py"]
}
```

## `update_thought`

Update an existing thought's fields.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `thought_id` | string | **yes** | — | ID of thought to update |
| `summary` | string | no | — | New summary |
| `content` | string | no | — | New content |
| `type` | string | no | — | New type |
| `project` | string | no | — | New project tag |
| `branch` | string | no | — | New branch |
| `keywords` | string[] | no | — | New keywords |
| `associated_files` | string[] | no | — | New file list |
| `pinned` | boolean | no | — | Set pin status |
| `archived` | boolean | no | — | Set archive status |

Only provided fields are updated. Omitted fields remain unchanged.

## `add_rule`

Store a learned rule — something to always do, never do, or do in specific contexts. Rules persist across sessions and are automatically surfaced when relevant.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `summary` | string | **yes** | — | Short rule description |
| `content` | string | no | `""` | Full explanation and reasoning |
| `type` | string | **yes** | — | `do`, `dont`, or `context_dependent` |
| `severity` | string | **yes** | — | `critical`, `preference`, or `context_dependent` |
| `condition` | string | no | `null` | When does this rule apply? |
| `session_id` | string | no | `null` | Current session ID |
| `project` | string | no | `null` | Project tag (`null` = global rule) |
| `branch` | string | no | `null` | Git branch (`null` = applies to all branches) |
| `keywords` | string[] | no | `[]` | Keywords for retrieval |
| `associated_files` | string[] | no | `[]` | Related files |
| `pinned` | boolean | no | `false` | Pin to always load |

**Branch support:** Yes

### Rule Type Matrix

| Type | Severity | Meaning | Example |
|------|----------|---------|---------|
| `do` | `critical` | Must always follow | "Always run tests before committing" |
| `dont` | `critical` | Must never do | "Never store secrets in source code" |
| `do` | `preference` | Should follow when possible | "Prefer composition over inheritance" |
| `dont` | `preference` | Should avoid | "Avoid deeply nested callbacks" |
| `context_dependent` | `context_dependent` | Depends on situation | "Use async for IO, sync for CPU" |

### Example Request

```json
{
  "summary": "Always use state param in OAuth redirects",
  "content": "Prevents CSRF attacks during OAuth callback",
  "type": "do",
  "severity": "critical",
  "condition": "When implementing OAuth redirect flows",
  "project": "myapp",
  "keywords": ["auth", "oauth", "security"]
}
```

## `reinforce_rule`

Reinforce a rule — bump its confidence when you encounter another case that confirms it. Higher reinforcement count means higher priority in search results.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `rule_id` | string | **yes** | — | ID of the rule to reinforce |
| `note` | string | no | `null` | Note about why this was reinforced |

### Example Request

```json
{
  "rule_id": "r1b2c3d4e5f6",
  "note": "Confirmed again: missing state param caused CSRF in GitHub OAuth"
}
```

The note is appended to the rule's `content` with a timestamp.

## `add_error_pattern`

Log a failure pattern: what went wrong, why, how it was fixed. Optionally link to a prevention rule so the AI never repeats the mistake.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `error_description` | string | **yes** | — | What went wrong |
| `cause` | string | no | `null` | Root cause |
| `fix` | string | no | `null` | How it was fixed |
| `prevention_rule_id` | string | no | `null` | ID of rule to prevent recurrence |
| `session_id` | string | no | `null` | Current session ID |
| `project` | string | no | `null` | Project tag |
| `branch` | string | no | `null` | Git branch name |
| `keywords` | string[] | no | `[]` | Keywords |
| `associated_files` | string[] | no | `[]` | Related files |

**Branch support:** Yes

### Example Request

```json
{
  "error_description": "OAuth callback failed with CSRF error",
  "cause": "Missing state parameter in redirect URL",
  "fix": "Added state param generation and validation",
  "project": "myapp",
  "branch": "feature/auth",
  "keywords": ["auth", "oauth", "csrf"]
}
```

## `link_items`

Create a directional link between two items (thoughts, rules, error patterns). Builds the knowledge graph.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `from_id` | string | **yes** | — | Source item ID |
| `from_type` | string | **yes** | — | `thought`, `rule`, or `error_pattern` |
| `to_id` | string | **yes** | — | Target item ID |
| `to_type` | string | **yes** | — | `thought`, `rule`, or `error_pattern` |
| `link_type` | string | no | `"related"` | `informs`, `contradicts`, `supersedes`, `related`, `caused_by` |

### Example Request

```json
{
  "from_id": "e1b2c3d4e5f6",
  "from_type": "error_pattern",
  "to_id": "r1b2c3d4e5f6",
  "to_type": "rule",
  "link_type": "caused_by"
}
```
