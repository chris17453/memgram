# Memgram — AI Instructions

You have access to **memgram**, a persistent memory system via MCP tools. Memgram is your long-term memory — it survives across sessions, compactions, and context resets. USE IT ACTIVELY.

## Core Principle

**Record everything worth remembering. Search before deciding. Resume where you left off.**

You are not just a consumer of memgram — you are its curator. The quality of your future context depends on what you store now.

---

## Session Lifecycle

### Starting Work

At the **very beginning** of every conversation:

```
1. Call start_session with your agent_type, model, project, and goal
2. Read the resume_context that comes back — it contains:
   - Last session summary and where it left off
   - Last compaction snapshot (goal, progress, blockers, next steps)
   - All pinned thoughts (always-relevant knowledge)
   - All critical/pinned rules (things you must follow)
   - Project summary (overview, tech stack, patterns)
3. Call get_rules for the project to load all active rules
4. If resuming previous work, review the last snapshot's next_steps
```

### During Work

As you work, record knowledge in real-time:

```
- Made a design decision? → add_thought(type="decision")
- Noticed a pattern? → add_thought(type="pattern")
- Learned something generalizable? → add_rule
- Hit an error and fixed it? → add_error_pattern
- Found two related items? → link_items
- Something should always be in context? → pin_item
```

### Before Compaction

When you're about to compact or your context is getting long:

```
Call save_snapshot with:
  - current_goal: what you're working on right now
  - progress_summary: what's been done so far this session
  - open_questions: anything unresolved
  - blockers: anything blocking progress
  - next_steps: what should happen next (ordered)
  - active_files: files you're currently editing
  - key_decisions: decisions made since last snapshot
```

This snapshot is what your next context will load. **Be thorough.**

### Ending Work

When the task is done or the conversation is ending:

```
Call end_session with:
  - summary: what was accomplished
  - outcome: the actual result
  - decisions_made: list of key decisions
  - files_modified: files that were changed
  - unresolved_items: anything left open
  - next_session_hints: what the next AI should know/do
```

---

## What to Record

### Thoughts (add_thought)

| Type | When to Use | Example |
|------|-------------|---------|
| `decision` | Chose one approach over another | "Using JWT over session cookies for stateless API" |
| `observation` | Noticed something important about the codebase | "The auth module has no test coverage" |
| `pattern` | Identified a recurring pattern | "All API endpoints follow the same error handling pattern" |
| `idea` | Something to consider later | "Could refactor the DB layer to use connection pooling" |
| `note` | General knowledge worth preserving | "The CI pipeline takes ~3 minutes to run" |
| `error` | Something that went wrong (use add_error_pattern for structured version) | "Build failed due to missing type stub" |

**Always include**: summary (searchable), keywords (for retrieval), project tag, associated_files (if relevant).

### Rules (add_rule)

Rules are your most powerful tool. They encode learned behavior that persists forever.

| Type | Severity | Example |
|------|----------|---------|
| `do` + `critical` | Must always follow | "Always run tests before committing" |
| `dont` + `critical` | Must never do | "Never store secrets in source code" |
| `do` + `preference` | Should follow when possible | "Prefer composition over inheritance" |
| `dont` + `preference` | Should avoid when possible | "Avoid deeply nested callbacks" |
| `context_dependent` + `context_dependent` | Depends on situation | "Use async in IO-heavy code, sync for CPU-bound" |

**Always include**: condition (when does this apply?), keywords, project (null = global rule).

When you encounter a situation that confirms an existing rule, call **reinforce_rule** to bump its confidence.

### Error Patterns (add_error_pattern)

When something breaks and you fix it:

```
add_error_pattern(
  error_description: "Build failed with 'Module not found: xyz'"
  cause: "Missing dependency — xyz wasn't in pyproject.toml"  
  fix: "Added xyz to dependencies and ran uv sync"
  keywords: ["build", "dependencies", "uv"]
  associated_files: ["pyproject.toml"]
)
```

If you create a rule to prevent it from happening again, link them with `prevention_rule_id`.

---

## How to Search

### Before Making Decisions

**Always search memgram before making significant decisions.** Previous sessions may have already solved this problem or established a rule about it.

```
search(query="authentication approach", project="myapp")
```

### Search Strategies

| Goal | Tool | Example |
|------|------|---------|
| General lookup | `search` | `search(query="database migration")` |
| Find rules for current work | `get_rules` | `get_rules(project="myapp", keywords=["auth"])` |
| Check previous sessions | `get_session_history` | `get_session_history(project="myapp", limit=5)` |
| Find related items | `get_related` | `get_related(item_id="abc123")` |
| Get clustered knowledge | `get_group` | `get_group(name="auth-system", project="myapp")` |
| Project overview | `get_project_summary` | `get_project_summary(project="myapp")` |
| Semantic similarity (RAG) | `search_by_embedding` | Pass embedding vector for nearest-neighbor search |

### Search Result Ranking

Results are scored by:
- **Text relevance** (40%) — how well the query matches
- **Recency** (20%) — newer items rank higher (decays over 30 days)
- **Pinned status** (20%) — pinned items get a major boost
- **Access frequency** (10%) — frequently retrieved items rank higher
- **Severity** (10%) — critical rules always surface

---

## Organizing Knowledge

### Groups

Cluster related items together for easy retrieval:

```
# Create a group
create_group(name="auth-system", description="Everything about authentication", project="myapp")

# Add items to it
add_to_group(group_id="...", item_id="thought-id", item_type="thought")
add_to_group(group_id="...", item_id="rule-id", item_type="rule")

# Later, retrieve the whole cluster
get_group(name="auth-system", project="myapp")
```

### Linking

Connect related items to build a knowledge graph:

```
link_items(from_id="error-id", from_type="error_pattern", 
           to_id="rule-id", to_type="rule", link_type="caused_by")
```

Link types: `informs`, `contradicts`, `supersedes`, `related`, `caused_by`

### Pinning

Pin items that should **always** be loaded into context for a project:

```
pin_item(item_id="rule-id")  # Now included in every get_resume_context
```

Use sparingly — only for truly critical, always-relevant knowledge.

---

## Project Summaries

Keep a living overview of each project:

```
update_project_summary(
  project="myapp",
  summary="REST API for user management with JWT auth",
  tech_stack=["python", "fastapi", "sqlalchemy", "jwt"],
  key_patterns=["Repository pattern for DB access", "Pydantic models for validation"],
  active_goals=["Add role-based access control", "Improve test coverage"]
)
```

Update this periodically — especially when goals change or the tech stack evolves.

---

## Quick Reference

### Most Important Tools

| When | Call |
|------|------|
| Conversation starts | `start_session` → read resume context → `get_rules` |
| Made a decision | `add_thought(type="decision")` |
| Learned a do/don't | `add_rule` |
| Something broke & was fixed | `add_error_pattern` |
| About to compact | `save_snapshot` |
| Need prior knowledge | `search` or `get_rules` |
| Conversation ends | `end_session` with full summary |

### Keywords Matter

Good keywords make knowledge findable. Always include:
- **Domain terms**: auth, database, api, testing, deployment
- **Technology terms**: python, jwt, sqlalchemy, react
- **Action terms**: migration, refactor, debug, optimize
- **Specific identifiers**: function names, file names, error codes

---

## Example Session Flow

```
→ start_session(agent_type="copilot", model="claude-sonnet-4", project="myapp", goal="Add password reset")
← Resume context: last session worked on login, rule: "always hash passwords with bcrypt"

→ search(query="password reset email")
← No existing knowledge

→ get_rules(project="myapp", keywords=["auth", "password", "security"])
← Rule: "Always hash passwords with bcrypt" (critical, reinforced 3x)

... do the work ...

→ add_thought(summary="Password reset uses time-limited JWT tokens", type="decision", 
              keywords=["auth", "password", "reset", "jwt"], project="myapp")

→ add_rule(summary="Reset tokens must expire within 1 hour", type="do", severity="critical",
           condition="When implementing password/email reset flows", 
           keywords=["auth", "reset", "security", "tokens"], project="myapp")

→ add_error_pattern(error_description="Reset token was accepted after expiry",
                    cause="Token expiry check was using local time instead of UTC",
                    fix="Changed to datetime.now(timezone.utc) for comparison",
                    keywords=["auth", "tokens", "timezone", "utc"])

→ save_snapshot(session_id="...", current_goal="Password reset feature",
                progress_summary="Reset endpoint done, email sending done, token validation done",
                next_steps=["Write tests", "Add rate limiting to reset endpoint"],
                active_files=["src/auth/reset.py", "src/email/templates.py"])

→ end_session(session_id="...", summary="Implemented password reset with email verification",
              files_modified=["src/auth/reset.py", "src/email/templates.py", "src/routes/auth.py"],
              next_session_hints="Tests needed for reset flow. Consider rate limiting.")
```
