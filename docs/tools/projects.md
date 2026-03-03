---
title: Project Tools
layout: default
parent: Tools Reference
nav_order: 4
---

# Project Tools

Two tools for managing living project summaries.

---

## `get_project_summary`

Get the living summary for a project — overview, tech stack, patterns, goals, and stats.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | **yes** | — | Project tag |

### Example Request

```json
{
  "project": "myapp"
}
```

### Example Response

```json
{
  "id": "p1a2b3c4",
  "project": "myapp",
  "summary": "REST API for user management with JWT auth",
  "tech_stack": "[\"python\", \"fastapi\", \"sqlalchemy\", \"jwt\"]",
  "key_patterns": "[\"Repository pattern for DB access\", \"Pydantic models for validation\"]",
  "active_goals": "[\"Add role-based access control\", \"Improve test coverage\"]",
  "total_sessions": 12,
  "total_thoughts": 45,
  "total_rules": 8,
  "created_at": "2025-01-10T08:00:00+00:00",
  "updated_at": "2025-01-15T14:30:00+00:00"
}
```

Returns an error if no summary exists for the project.

---

## `update_project_summary`

Update a project's living summary. Creates it if it doesn't exist. Also recalculates session/thought/rule counts.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | **yes** | — | Project tag |
| `summary` | string | no | `null` | Updated project overview |
| `tech_stack` | string[] | no | `null` | Technology stack |
| `key_patterns` | string[] | no | `null` | Coding patterns/conventions |
| `active_goals` | string[] | no | `null` | Current project goals |

Only provided fields are updated. Omitted fields retain their current values.

### Example Request

```json
{
  "project": "myapp",
  "summary": "REST API with JWT auth and OAuth integration",
  "tech_stack": ["python", "fastapi", "sqlalchemy", "jwt", "oauth"],
  "key_patterns": ["Repository pattern", "Pydantic validation", "PKCE flow for OAuth"],
  "active_goals": ["Add GitHub OAuth provider", "Add rate limiting"]
}
```

### Example Response

```json
{
  "id": "p1a2b3c4",
  "project": "myapp",
  "summary": "REST API with JWT auth and OAuth integration",
  "tech_stack": "[\"python\", \"fastapi\", \"sqlalchemy\", \"jwt\", \"oauth\"]",
  "key_patterns": "[\"Repository pattern\", \"Pydantic validation\", \"PKCE flow for OAuth\"]",
  "active_goals": "[\"Add GitHub OAuth provider\", \"Add rate limiting\"]",
  "total_sessions": 13,
  "total_thoughts": 48,
  "total_rules": 9,
  "created_at": "2025-01-10T08:00:00+00:00",
  "updated_at": "2025-01-15T16:00:00+00:00"
}
```
