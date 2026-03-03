---
title: Branch Workflow
layout: default
parent: Guides
nav_order: 3
---

# Branch Workflow

Patterns for using memgram's branch scoping in feature-branch development.

---

## The Concept

Branch scoping lets you isolate knowledge per git branch while keeping project-wide knowledge accessible. When you pass `branch="feature/auth"`, it's normalized to `"featureauth"` and used to scope items.

```
Project: "myapp"
├── branch: NULL (project-wide)
│   ├── Rule: "Always use type hints" (critical)
│   ├── Rule: "Prefer composition over inheritance"
│   └── Thought: "Using FastAPI for REST API" (decision)
├── branch: "featureauth"
│   ├── Thought: "Using PKCE flow for OAuth" (decision)
│   ├── Error: "CSRF error from missing state param"
│   └── Rule: "Reset tokens expire in 1 hour" (critical)
└── branch: "fixloginbug"
    ├── Thought: "Bug was in session validation logic"
    └── Error: "Session cookie not set with SameSite"
```

---

## Starting a Branch Session

Always pass both `project` and `branch` when starting work on a feature:

```json
{
  "tool": "start_session",
  "agent_type": "copilot",
  "model": "claude-sonnet-4",
  "project": "myapp",
  "branch": "feature/auth",
  "goal": "Add OAuth login"
}
```

The resume context will include:
- Last session on this **specific branch**
- Pinned thoughts from this branch **plus** project-global pinned thoughts
- Critical rules from this branch **plus** project-global critical rules
- Project summary (always project-level)

---

## Deciding Scope for New Items

### Branch-Scoped (include `branch`)

Use for knowledge that only matters on this branch:

```json
{
  "tool": "add_thought",
  "summary": "Temporary workaround: hardcoded callback URL",
  "type": "note",
  "project": "myapp",
  "branch": "feature/auth",
  "keywords": ["auth", "workaround"]
}
```

Good candidates for branch scoping:
- Branch-specific decisions and workarounds
- Debugging notes for branch-specific issues
- Error patterns unique to the branch's changes
- Temporary rules that shouldn't persist after merge

### Project-Scoped (omit `branch`)

Use for knowledge that applies to all branches:

```json
{
  "tool": "add_rule",
  "summary": "Always validate OAuth state parameter",
  "type": "do",
  "severity": "critical",
  "project": "myapp",
  "keywords": ["auth", "security", "oauth"]
}
```

Good candidates for project scope:
- Coding standards and conventions
- Architecture decisions
- Security rules
- Technology choices

---

## Search Behavior by Branch

### NULL-Inclusive (rules and resume context)

`get_rules` and `get_resume_context` return branch-scoped items **plus** items where `branch IS NULL`:

```json
// Returns rules for "featureauth" AND rules with branch=NULL
{ "tool": "get_rules", "project": "myapp", "branch": "feature/auth" }
```

This ensures project-wide rules always surface.

### Exact Match (search and history)

`search` and `get_session_history` use exact branch matching:

```json
// Only returns items where branch="featureauth"
{ "tool": "search", "query": "oauth", "project": "myapp", "branch": "feature/auth" }

// To search project-wide, omit branch
{ "tool": "search", "query": "oauth", "project": "myapp" }
```

---

## After Branch Merge

When a branch merges into main:

1. **Branch knowledge stays in the database** — it doesn't get deleted
2. **It stops surfacing** — since no one queries that branch name anymore
3. **It remains searchable** — you can still find it by searching with the old branch name

### Promoting Knowledge After Merge

If a branch-scoped rule should become project-wide:

```json
// Create a new project-wide rule (no branch)
{
  "tool": "add_rule",
  "summary": "Always validate OAuth state parameter",
  "type": "do",
  "severity": "critical",
  "project": "myapp",
  "keywords": ["auth", "security"]
}

// Optionally archive the old branch-scoped version
{ "tool": "archive_item", "item_id": "old-branch-rule-id" }
```

---

## Example: Full Branch Lifecycle

```
1. Create feature branch: feature/payment
2. Start session with branch="feature/payment"
3. Resume context loads:
   - Project-wide rules (branch=NULL)
   - No branch-specific items yet (new branch)
4. Work on the feature:
   - add_thought("Using Stripe API", branch="feature/payment")
   - add_rule("Always use idempotency keys", branch="feature/payment")
   - add_error_pattern("Webhook signature invalid", branch="feature/payment")
5. End session

6. Next day, start new session with branch="feature/payment"
7. Resume context now includes:
   - Project-wide rules (branch=NULL)
   - Yesterday's thoughts, rules from this branch
   - Last session summary with next_session_hints
8. Continue working...

9. Branch merges to main
10. Promote important rules to project scope:
    - add_rule("Always use idempotency keys for Stripe", project="myapp")
    ← no branch = visible on all branches now
```
