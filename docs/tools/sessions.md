# Session Tools

Four tools for managing the session lifecycle: start, snapshot, resume, and end.

## `start_session`

Begin a new memgram session. Call this at the beginning of every conversation. Returns the session ID plus resume context (last session summary, pinned items, active rules).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `agent_type` | string | **yes** | — | AI agent type: `copilot`, `claude`, `cursor`, etc. |
| `model` | string | **yes** | — | Model name: `gpt-4`, `claude-sonnet`, etc. |
| `project` | string | no | `null` | Project tag for scoped context |
| `branch` | string | no | `null` | Git branch name for branch-scoped context |
| `goal` | string | no | `null` | What this session aims to accomplish |

**Branch support:** Yes — `project` and `branch` are normalized and used to scope resume context.

### Example Request

```json
{
  "agent_type": "copilot",
  "model": "claude-sonnet-4",
  "project": "myapp",
  "branch": "feature/auth",
  "goal": "Add OAuth login"
}
```

### Example Response

```json
{
  "session": {
    "id": "a1b2c3d4e5f6",
    "agent_type": "copilot",
    "model": "claude-sonnet-4",
    "project": "myapp",
    "branch": "featureauth",
    "goal": "Add OAuth login",
    "status": "active",
    "started_at": "2025-01-15T10:30:00+00:00"
  },
  "resume_context": {
    "last_session": { "...": "..." },
    "last_snapshot": { "...": "..." },
    "pinned_thoughts": [],
    "active_rules": [],
    "project_summary": { "...": "..." }
  }
}
```

## `end_session`

End the current session with a summary. Creates a structured session summary record. Call this when finishing work.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `session_id` | string | **yes** | — | Session ID to close |
| `summary` | string | **yes** | — | Summary of what was accomplished |
| `outcome` | string | no | `null` | What actually happened |
| `decisions_made` | string[] | no | `[]` | Key decisions made |
| `rules_learned` | string[] | no | `[]` | Rule IDs created this session |
| `errors_encountered` | string[] | no | `[]` | Error pattern IDs from this session |
| `files_modified` | string[] | no | `[]` | Files touched this session |
| `unresolved_items` | string[] | no | `[]` | Open questions/issues |
| `next_session_hints` | string | no | `null` | What the next session should know |

### Example Request

```json
{
  "session_id": "a1b2c3d4e5f6",
  "summary": "Implemented OAuth login with PKCE flow",
  "outcome": "OAuth working end-to-end with Google provider",
  "decisions_made": ["Using PKCE flow", "Google as first provider"],
  "files_modified": ["src/auth/oauth.py", "src/routes/login.py"],
  "next_session_hints": "Add GitHub provider next. Rate limiting needed."
}
```

## `save_snapshot`

Save a compaction checkpoint. Call this BEFORE context compaction to preserve state. Records current goal, progress, blockers, and next steps so the AI can resume seamlessly.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `session_id` | string | **yes** | — | Current session ID |
| `current_goal` | string | no | `null` | What we're currently working on |
| `progress_summary` | string | no | `null` | What's been done so far |
| `open_questions` | string[] | no | `[]` | Unresolved questions |
| `blockers` | string[] | no | `[]` | Things blocking progress |
| `next_steps` | string[] | no | `[]` | Ordered list of what to do next |
| `active_files` | string[] | no | `[]` | Files currently being edited |
| `key_decisions` | string[] | no | `[]` | Decisions made in this segment |

### Example Request

```json
{
  "session_id": "a1b2c3d4e5f6",
  "current_goal": "OAuth login with PKCE",
  "progress_summary": "Token exchange working, callback route done",
  "next_steps": ["Add session persistence", "Write tests"],
  "active_files": ["src/auth/oauth.py"]
}
```

## `get_resume_context`

Get everything needed to resume work: last session info, latest compaction snapshot, pinned thoughts, active rules, and project summary. Call this after compaction or at session start.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | `null` | Project tag to scope context |
| `branch` | string | no | `null` | Git branch name to scope context |

**Branch support:** Yes — uses NULL-inclusive matching. Returns branch-specific items plus branch-global items.

### Example Request

```json
{
  "project": "myapp",
  "branch": "feature/auth"
}
```

### Response Structure

```json
{
  "last_session": { "id": "...", "goal": "...", "summary": "..." },
  "last_session_summary": { "outcome": "...", "next_session_hints": "..." },
  "last_snapshot": { "current_goal": "...", "next_steps": ["..."] },
  "pinned_thoughts": [ { "summary": "...", "type": "decision" } ],
  "active_rules": [ { "summary": "...", "severity": "critical" } ],
  "project_summary": { "summary": "...", "tech_stack": ["..."] }
}
```
