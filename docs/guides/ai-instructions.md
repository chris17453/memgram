# AI Agent Usage Guide

This is the complete guide for AI assistants using memgram. Add this to your AI's system prompt or instructions file.

!!! note
    This guide is the formatted version of `INSTRUCTIONS.md` from the repository root.

## Core Principle

**Record everything worth remembering. Search before deciding. Resume where you left off.**

You are not just a consumer of memgram — you are its curator. The quality of your future context depends on what you store now.

## Session Lifecycle

### Starting Work

At the **very beginning** of every conversation:

1. Call `start_session` with your `agent_type`, `model`, `project`, `branch`, and `goal`
   - `project`: the codebase/repo name (e.g., `"myapp"`)
   - `branch`: the git branch you're working on (e.g., `"feature/auth"` — normalized to `"featureauth"`)
   - Both are optional; use them when working in a scoped context
2. Read the `resume_context` that comes back — it contains:
   - Last session summary and where it left off
   - Last compaction snapshot (goal, progress, blockers, next steps)
   - All pinned thoughts (always-relevant knowledge, branch-scoped + global)
   - All critical/pinned rules (things you must follow, branch-scoped + global)
   - Project summary (overview, tech stack, patterns)
3. Call `get_rules` for the project/branch to load all active rules
4. If resuming previous work, review the last snapshot's `next_steps`

### During Work

As you work, record knowledge in real-time:

| Situation | Action |
|-----------|--------|
| Made a design decision | `add_thought(type="decision")` |
| Noticed a pattern | `add_thought(type="pattern")` |
| Learned something generalizable | `add_rule` |
| Hit an error and fixed it | `add_error_pattern` |
| Found two related items | `link_items` |
| Something should always be in context | `pin_item` |

### Before Compaction

When you're about to compact or your context is getting long, call `save_snapshot` with:

- `current_goal`: what you're working on right now
- `progress_summary`: what's been done so far this session
- `open_questions`: anything unresolved
- `blockers`: anything blocking progress
- `next_steps`: what should happen next (ordered)
- `active_files`: files you're currently editing
- `key_decisions`: decisions made since last snapshot

This snapshot is what your next context will load. **Be thorough.**

### Ending Work

When the task is done or the conversation is ending, call `end_session` with:

- `summary`: what was accomplished
- `outcome`: the actual result
- `decisions_made`: list of key decisions
- `files_modified`: files that were changed
- `unresolved_items`: anything left open
- `next_session_hints`: what the next AI should know/do

## What to Record

### Thoughts

| Type | When to Use | Example |
|------|-------------|---------|
| `decision` | Chose one approach over another | "Using JWT over session cookies for stateless API" |
| `observation` | Noticed something important | "The auth module has no test coverage" |
| `pattern` | Identified a recurring pattern | "All API endpoints follow the same error handling pattern" |
| `idea` | Something to consider later | "Could refactor the DB layer to use connection pooling" |
| `note` | General knowledge worth preserving | "The CI pipeline takes ~3 minutes to run" |
| `error` | Something that went wrong | "Build failed due to missing type stub" |

**Always include**: summary (searchable), keywords (for retrieval), project tag, branch (if branch-specific), associated_files (if relevant).

### Rules

Rules are your most powerful tool. They encode learned behavior that persists forever.

| Type | Severity | Example |
|------|----------|---------|
| `do` + `critical` | Must always follow | "Always run tests before committing" |
| `dont` + `critical` | Must never do | "Never store secrets in source code" |
| `do` + `preference` | Should follow when possible | "Prefer composition over inheritance" |
| `dont` + `preference` | Should avoid when possible | "Avoid deeply nested callbacks" |
| `context_dependent` + `context_dependent` | Depends on situation | "Use async in IO-heavy code, sync for CPU-bound" |

**Always include**: condition (when does this apply?), keywords, project (null = global rule).

**Branch guidance**: Omit `branch` for rules that should apply project-wide. Only set `branch` for rules specific to a feature branch.

When you encounter a situation that confirms an existing rule, call `reinforce_rule` to bump its confidence.

### Error Patterns

When something breaks and you fix it:

```
add_error_pattern(
  error_description: "Build failed with 'Module not found: xyz'"
  cause: "Missing dependency — xyz wasn't in pyproject.toml"
  fix: "Added xyz to dependencies and ran uv sync"
  keywords: ["build", "dependencies", "uv"]
  associated_files: ["pyproject.toml"]
  project: "myapp"
  branch: "feature/auth"
)
```

If you create a rule to prevent recurrence, link them with `prevention_rule_id`.

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
| Semantic similarity | `search_by_embedding` | Pass embedding vector for nearest-neighbor search |

## Organizing Knowledge

### Groups

Cluster related items for easy retrieval:

```
create_group(name="auth-system", description="Everything about authentication", project="myapp")
add_to_group(group_id="...", item_id="thought-id", item_type="thought")
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

Pin items that should **always** be loaded into context:

```
pin_item(item_id="rule-id")  # Now included in every get_resume_context
```

Use sparingly — only for truly critical, always-relevant knowledge.

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

## Keywords Matter

Good keywords make knowledge findable. Always include:

- **Domain terms**: auth, database, api, testing, deployment
- **Technology terms**: python, jwt, sqlalchemy, react
- **Action terms**: migration, refactor, debug, optimize
- **Specific identifiers**: function names, file names, error codes

## Quick Reference

| When | Call |
|------|------|
| Conversation starts | `start_session` -> read resume context -> `get_rules` |
| Made a decision | `add_thought(type="decision")` |
| Learned a do/don't | `add_rule` |
| Something broke & was fixed | `add_error_pattern` |
| About to compact | `save_snapshot` |
| Need prior knowledge | `search` or `get_rules` |
| Conversation ends | `end_session` with full summary |
