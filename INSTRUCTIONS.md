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
1. Call start_session with your agent_type, model, project, branch, and goal
   - project: the codebase/repo name (e.g., "myapp")
   - branch: the git branch you're working on (e.g., "feature/auth" → normalized to "featureauth")
   - Both are optional; use them when working in a scoped context
2. Read the resume_context that comes back — it contains:
   - Last session summary and where it left off
   - Last compaction snapshot (goal, progress, blockers, next steps)
   - All pinned thoughts (always-relevant knowledge, branch-scoped + global)
   - All critical/pinned rules (things you must follow, branch-scoped + global)
   - Project summary (overview, tech stack, patterns)
3. Call get_rules for the project/branch to load all active rules
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

## Branch Scoping

Memgram supports two-dimensional scoping: **project** + **branch**. This lets you track branch-specific context that doesn't pollute other branches.

### When to Use Branch

| Scenario | Use `branch`? |
|----------|---------------|
| Working on a feature branch | Yes — pass the branch name |
| Recording a project-wide coding standard | No — omit branch so it's visible everywhere |
| Logging a workaround specific to your feature | Yes — it shouldn't leak to main |
| Adding a rule that applies to all branches | No — omit branch |
| Debugging an issue on a specific branch | Yes — scope errors/thoughts to the branch |

### How Branch Filtering Works

- **`get_rules`** and **`get_resume_context`** return branch-scoped items **plus** branch-global items (`branch IS NULL`). This means project-wide rules always surface.
- **`search`**, **`list_sessions`**, and other search tools use exact branch matching — only items with the specified branch are returned.
- Names are normalized: `feature/auth-flow` → `featureauthflow`. You don't need to pre-normalize.

### Example: Branch-Aware Session Flow

```
→ start_session(agent_type="copilot", model="claude-sonnet-4",
                project="myapp", branch="feature/auth", goal="Add OAuth login")
← Resume context includes:
   - Last session on this branch
   - Pinned thoughts from this branch + project-global pinned thoughts
   - Critical rules from this branch + project-global critical rules

→ add_thought(summary="Using PKCE flow for OAuth", type="decision",
              project="myapp", branch="feature/auth",
              keywords=["auth", "oauth", "pkce"])

→ add_rule(summary="Always use state param in OAuth redirects", type="do", severity="critical",
           project="myapp",   ← no branch = applies to all branches
           keywords=["auth", "oauth", "security"])

→ add_error_pattern(error_description="OAuth callback failed with CSRF error",
                    cause="Missing state parameter in redirect URL",
                    fix="Added state param generation and validation",
                    project="myapp", branch="feature/auth",
                    keywords=["auth", "oauth", "csrf"])
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

**Always include**: summary (searchable), keywords (for retrieval), project tag, branch (if branch-specific), associated_files (if relevant).

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

**Branch guidance**: Omit `branch` for rules that should apply project-wide. Only set `branch` for rules that are specific to a feature branch and shouldn't persist after merge.

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
  project: "myapp"
  branch: "feature/auth"  ← optional, use if branch-specific
)
```

If you create a rule to prevent it from happening again, link them with `prevention_rule_id`.

---

## How to Search

### Before Making Decisions

**Always search memgram before making significant decisions.** Previous sessions may have already solved this problem or established a rule about it.

```
search(query="authentication approach", project="myapp", branch="feature/auth")
```

### Search Strategies

| Goal | Tool | Example |
|------|------|---------|
| General lookup | `search` | `search(query="database migration", project="myapp")` |
| Branch-scoped lookup | `search` | `search(query="auth", project="myapp", branch="feature/auth")` |
| Find rules for current work | `get_rules` | `get_rules(project="myapp", branch="feature/auth", keywords=["auth"])` |
| Check previous sessions | `get_session_history` | `get_session_history(project="myapp", branch="feature/auth", limit=5)` |
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
| Conversation starts | `start_session` (with project + branch) → read resume context → `get_rules` |
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
→ start_session(agent_type="copilot", model="claude-sonnet-4",
                project="myapp", branch="feature/reset", goal="Add password reset")
← Resume context: last session worked on login, rule: "always hash passwords with bcrypt"

→ search(query="password reset email", project="myapp")
← No existing knowledge

→ get_rules(project="myapp", branch="feature/reset", keywords=["auth", "password", "security"])
← Rule: "Always hash passwords with bcrypt" (critical, reinforced 3x, branch-global)

... do the work ...

→ add_thought(summary="Password reset uses time-limited JWT tokens", type="decision",
              keywords=["auth", "password", "reset", "jwt"],
              project="myapp", branch="feature/reset")

→ add_rule(summary="Reset tokens must expire within 1 hour", type="do", severity="critical",
           condition="When implementing password/email reset flows",
           keywords=["auth", "reset", "security", "tokens"],
           project="myapp")  ← no branch = project-wide rule

→ add_error_pattern(error_description="Reset token was accepted after expiry",
                    cause="Token expiry check was using local time instead of UTC",
                    fix="Changed to datetime.now(timezone.utc) for comparison",
                    keywords=["auth", "tokens", "timezone", "utc"],
                    project="myapp", branch="feature/reset")

→ save_snapshot(session_id="...", current_goal="Password reset feature",
                progress_summary="Reset endpoint done, email sending done, token validation done",
                next_steps=["Write tests", "Add rate limiting to reset endpoint"],
                active_files=["src/auth/reset.py", "src/email/templates.py"])

→ end_session(session_id="...", summary="Implemented password reset with email verification",
              files_modified=["src/auth/reset.py", "src/email/templates.py", "src/routes/auth.py"],
              next_session_hints="Tests needed for reset flow. Consider rate limiting.")
```
