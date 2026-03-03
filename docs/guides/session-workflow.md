---
title: Session Workflow
layout: default
parent: Guides
nav_order: 2
---

# Session Workflow

The complete lifecycle of a memgram session: start, work, snapshot, and end.

---

## Overview

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  START   │───▶│   WORK   │───▶│ SNAPSHOT │───▶│   END    │
│ Session  │    │ & Record │    │ (repeat) │    │ Session  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
      │               │               │               │
      ▼               ▼               ▼               ▼
  Resume ctx     Thoughts,      Compaction       Session
  loaded         Rules,         checkpoint       summary
                 Errors                          created
```

---

## Step 1: Start Session

Call `start_session` at the very beginning of every conversation.

```json
{
  "agent_type": "copilot",
  "model": "claude-sonnet-4",
  "project": "myapp",
  "branch": "feature/auth",
  "goal": "Add OAuth login"
}
```

**What happens:**
1. A new session record is created (status: `active`)
2. Resume context is assembled and returned:
   - Last session on this project/branch
   - Last compaction snapshot from that session
   - Last session summary with `next_session_hints`
   - All pinned thoughts (branch-scoped + global)
   - All critical/pinned rules (branch-scoped + global)
   - Project summary

**What to do next:**
- Read the entire resume context
- Call `get_rules` for additional rules relevant to your work
- Check `next_steps` from the last snapshot
- Review `next_session_hints` from the last session summary

---

## Step 2: Work & Record

As you work, record knowledge in real-time. Don't batch — record as things happen.

### Decision Made

```json
{
  "tool": "add_thought",
  "summary": "Using PKCE flow for OAuth",
  "content": "Chose PKCE over implicit flow for better security in SPA context",
  "type": "decision",
  "project": "myapp",
  "branch": "feature/auth",
  "keywords": ["auth", "oauth", "pkce"]
}
```

### Rule Learned

```json
{
  "tool": "add_rule",
  "summary": "Always use state param in OAuth redirects",
  "type": "do",
  "severity": "critical",
  "condition": "When implementing OAuth redirect flows",
  "project": "myapp",
  "keywords": ["auth", "oauth", "security"]
}
```

Note: no `branch` — this rule applies project-wide.

### Error Fixed

```json
{
  "tool": "add_error_pattern",
  "error_description": "OAuth callback failed with CSRF error",
  "cause": "Missing state parameter in redirect URL",
  "fix": "Added state param generation and validation",
  "project": "myapp",
  "branch": "feature/auth",
  "keywords": ["auth", "oauth", "csrf"]
}
```

### Searching Before Deciding

Before making significant decisions, search first:

```json
{ "tool": "search", "query": "authentication approach", "project": "myapp" }
{ "tool": "get_rules", "project": "myapp", "keywords": ["auth", "security"] }
```

---

## Step 3: Snapshot (Before Compaction)

When the context window is getting long and compaction is approaching, save a snapshot:

```json
{
  "tool": "save_snapshot",
  "session_id": "a1b2c3d4e5f6",
  "current_goal": "OAuth login with PKCE",
  "progress_summary": "Token exchange working, callback route done, state validation added",
  "open_questions": ["Should we support multiple OAuth providers from the start?"],
  "blockers": [],
  "next_steps": [
    "Add session persistence after OAuth",
    "Write integration tests for OAuth flow",
    "Add GitHub as second provider"
  ],
  "active_files": ["src/auth/oauth.py", "src/routes/login.py"],
  "key_decisions": ["Using PKCE flow", "State param for CSRF protection"]
}
```

**Key points:**
- Snapshots auto-increment `sequence_num` within a session
- The session's `compaction_count` is incremented
- Be thorough — this snapshot is what the next context loads
- Order `next_steps` by priority

You can save multiple snapshots per session. Each one captures the state at that point.

---

## Step 4: End Session

When the task is done or the conversation is ending:

```json
{
  "tool": "end_session",
  "session_id": "a1b2c3d4e5f6",
  "summary": "Implemented OAuth login with PKCE flow and CSRF protection",
  "outcome": "OAuth working end-to-end with Google provider",
  "decisions_made": [
    "Using PKCE flow for OAuth",
    "State param for CSRF protection",
    "Google as first provider"
  ],
  "files_modified": [
    "src/auth/oauth.py",
    "src/routes/login.py",
    "src/config.py"
  ],
  "unresolved_items": [
    "Multiple provider support not started",
    "No integration tests yet"
  ],
  "next_session_hints": "Add GitHub provider next. Integration tests needed for OAuth flow. Consider rate limiting on callback endpoint."
}
```

**What happens:**
1. Session status changes to `completed`
2. A structured `session_summary` record is created
3. If a project is set, project summary counts are updated

---

## Putting It All Together

```
Session #1: "Add OAuth login"
├── start_session → gets empty resume (first session)
├── add_thought: "Using PKCE flow" (decision)
├── add_rule: "Always use state param" (critical)
├── add_error_pattern: "CSRF error → missing state"
├── save_snapshot: progress + next steps
└── end_session: summary + hints for next session

Session #2: "Add GitHub OAuth provider"
├── start_session → gets resume from session #1
│   ├── Sees: "OAuth working with Google"
│   ├── Sees: "Always use state param" (rule)
│   └── Sees: next_steps from snapshot
├── get_rules → loads all auth rules
├── search("oauth provider") → finds session #1 decisions
├── ... work ...
├── save_snapshot
└── end_session
```

Each session builds on the previous one. Knowledge accumulates and surfaces automatically.
