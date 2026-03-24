# Memgram — AI Instructions

You have access to **memgram**, a persistent memory and project knowledge system via MCP tools (110 tools). Memgram is your long-term memory — it survives across sessions, compactions, and context resets. USE IT ACTIVELY.

## Core Principle

**Record everything worth remembering. Search before deciding. Resume where you left off.**

You are not just a consumer of memgram — you are its curator. The quality of your future context depends on what you store now. Everything is project-scoped — always pass `project` when creating items.

---

## Session Lifecycle

### Starting Work

At the **very beginning** of every conversation:

```
1. Call start_session with your agent_type, model, project, branch, and goal
   - project is REQUIRED (e.g., "myapp")
   - branch: the git branch you're working on (normalized automatically)
2. Read the resume_context that comes back — it contains:
   - Last session summary and where it left off
   - Last compaction snapshot (goal, progress, blockers, next steps)
   - All pinned thoughts (always-relevant knowledge, branch-scoped + global)
   - All critical/pinned rules (things you must follow, branch-scoped + global)
   - Project summary (overview, tech stack, patterns)
3. Call get_instructions to load behavioral rules for this project
4. Call get_rules for the project/branch to load all active rules
5. If resuming previous work, review the last snapshot's next_steps
```

### During Work

As you work, record knowledge in real-time. **Always pass your session_id** (from `start_session`) to every knowledge tool:

```
- Made a design decision? → add_thought(session_id="...", type="decision")
- Noticed a pattern? → add_thought(session_id="...", type="pattern")
- Learned something generalizable? → add_rule(session_id="...")
- Hit an error and fixed it? → add_error_pattern(session_id="...")
- Found two related items? → link_items
- Something should always be in context? → pin_item
```

**session_id is REQUIRED** for add_thought, add_rule, and add_error_pattern. Without it, items lose agent attribution and session linkage. Always call start_session first and save the returned session ID.

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

## All Tool Categories

Memgram has 110 tools across 25 categories. Here's when to use each:

### Knowledge & Memory (Core)

| When | Call |
|------|------|
| Record a decision, observation, pattern, idea | `add_thought(type="decision"/"observation"/"pattern"/"idea"/"note")` |
| Encode a learned do/don't | `add_rule(type="do"/"dont", severity="critical"/"preference")` |
| Log an error you fixed | `add_error_pattern(error_description, cause, fix)` |
| Confirm an existing rule | `reinforce_rule(rule_id)` |
| Connect two related items | `link_items(from_id, to_id, link_type)` |
| Pin something to always load | `pin_item(item_id)` |
| Remove from search results | `archive_item(item_id)` |

### Search & Retrieval

| When | Call |
|------|------|
| General lookup | `search(query, project)` |
| Find rules for current work | `get_rules(project, branch, keywords)` |
| Check previous sessions | `get_session_history(project, branch)` |
| Find linked items | `get_related(item_id)` |
| Get a knowledge cluster | `get_group(name, project)` |
| Project overview | `get_project_summary(project)` |
| Semantic/vector search | `search_by_embedding(embedding, project)` |

### Project Management

| When | Call |
|------|------|
| Track work with tasks | `create_plan` → `add_plan_task` → `update_plan_task` |
| Define what to build | `create_spec(title, acceptance_criteria, project)` |
| Track a capability | `create_feature(name, spec_id, project)` |
| Define a system component | `create_component(name, type, project, tech_stack)` |
| File a bug/task/feature request | `create_ticket(title, type, project)` — auto-numbered (e.g., MYAPP-42) |
| Record an architecture decision | `create_decision(title, context, options, outcome, project)` |

### People & Teams

| When | Call |
|------|------|
| Add a person | `add_person(name, role, skills)` |
| Create a team | `create_team(name, project)` → `add_team_member(team_id, person_id)` |

### Infrastructure & DevOps

| When | Call |
|------|------|
| Document an API endpoint | `create_endpoint(method, path, auth_type, project)` |
| Register a secret reference | `create_credential(name, type, vault_path/env_var, project)` — **never store actual secrets** |
| Define an environment | `create_environment(name, type, url, project)` |
| Record a deployment | `create_deployment(version, environment_id, strategy, project)` |
| Track a CI/CD build | `create_build(name, pipeline, commit_sha, project)` |

### Operations

| When | Call |
|------|------|
| Report an incident | `create_incident(title, severity, project)` — severity p0-p4 |
| Track a dependency | `create_dependency(name, version, type, project)` |
| Document a procedure | `create_runbook(title, steps, project)` |

### Cross-Cutting (Any Entity)

| When | Call |
|------|------|
| Add a comment to anything | `add_comment(entity_id, entity_type, content)` |
| Attach a file/URL to anything | `add_attachment(entity_id, entity_type, url, type)` — images, docs, audio, video |
| Log a change for audit | `log_audit(entity_id, entity_type, action)` |
| Query change history | `get_audit_log(entity_id)` |

### Agent Instructions

| When | Call |
|------|------|
| Get instructions for this project | `get_instructions(project)` — sorted by priority |
| Create a new instruction | `create_instruction(section, title, content, priority, scope)` |

### Health & Stats

| When | Call |
|------|------|
| Check database health | `get_health` |
| Agent contribution stats | `get_agent_stats(project)` |

---

## Branch Scoping

Memgram supports two-dimensional scoping: **project** + **branch**. This lets you track branch-specific context that doesn't pollute other branches.

| Scenario | Use `branch`? |
|----------|---------------|
| Working on a feature branch | Yes — pass the branch name |
| Recording a project-wide coding standard | No — omit branch so it's visible everywhere |
| Logging a workaround specific to your feature | Yes — it shouldn't leak to main |
| Adding a rule that applies to all branches | No — omit branch |
| Debugging an issue on a specific branch | Yes — scope errors/thoughts to the branch |

Branch filtering: `get_rules` and `get_resume_context` return branch-scoped items **plus** project-global items. Names are normalized: `feature/auth-flow` → `featureauthflow`.

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

### Rules (add_rule)

Rules encode learned behavior that persists forever.

| Type | Severity | Example |
|------|----------|---------|
| `do` + `critical` | Must always follow | "Always run tests before committing" |
| `dont` + `critical` | Must never do | "Never store secrets in source code" |
| `do` + `preference` | Should follow when possible | "Prefer composition over inheritance" |
| `dont` + `preference` | Should avoid when possible | "Avoid deeply nested callbacks" |
| `context_dependent` | Depends on situation | "Use async in IO-heavy code, sync for CPU-bound" |

When you encounter a situation that confirms an existing rule, call **reinforce_rule** to bump its confidence.

### Error Patterns (add_error_pattern)

When something breaks and you fix it — record the description, cause, fix, and keywords. If you create a rule to prevent it from happening again, link them with `prevention_rule_id`.

---

## When to Use Project Management Tools

### Tickets

Use `create_ticket` for trackable work items — bugs, tasks, features, improvements, questions. Tickets are auto-numbered per project (e.g., `MYAPP-1`). They support sub-tickets via `parent_id`, assignees, and status flow: `open → in_progress → review → resolved → closed`.

### Plans

Use `create_plan` for multi-step work that spans tasks. Plans have scope (project/sprint/session/milestone), priority, due dates, and ordered tasks. Add tasks with `add_plan_task`, track progress with `update_plan_task`.

### Specs & Features

Use `create_spec` to formally define what needs to be built (with acceptance criteria). Use `create_feature` to track a capability being built, optionally linked to a spec.

### Decisions (ADRs)

Use `create_decision` for Architecture Decision Records. Record the context, options considered, outcome chosen, and consequences. Decisions can be superseded: `update_decision(status="superseded", superseded_by=new_id)`.

---

## When to Use Infrastructure Tools

### Endpoints

Use `create_endpoint` whenever you discover or create an API endpoint. Record the method, path, auth type, rate limits, and request/response schemas. This builds an API catalog for the project.

### Credentials

Use `create_credential` to register **references** to secrets — vault paths, environment variable names, provider info. **NEVER store actual secret values.** Track rotation dates and expiry.

### Environments & Deployments

Use `create_environment` to define deployment targets (dev/staging/prod with URLs). Use `create_deployment` to record each release — version, environment, strategy (rolling/canary/blue_green), and who deployed.

### Builds

Use `create_build` to track CI/CD runs — pipeline name, trigger type, commit SHA, pass/fail status, artifacts.

### Dependencies

Use `create_dependency` to catalog external dependencies — libraries, services, databases, APIs. Track versions, licenses, and whether versions are pinned.

---

## When to Use Operations Tools

### Incidents

Use `create_incident` for outages and issues. Severity levels: p0 (critical) through p4 (minor). Track timeline events, root cause, and resolution. Status flow: `investigating → identified → monitoring → resolved → postmortem`.

### Runbooks

Use `create_runbook` to document operational procedures — step-by-step instructions for common tasks like rollbacks, credential rotation, or incident response. Include trigger conditions so agents know when to suggest them.

---

## Comments, Attachments, and Audit

### Comments

Use `add_comment` to add notes to **any** entity — tickets, incidents, decisions, people, etc. Comments support threading via `parent_id`.

### Attachments

Use `add_attachment` to link files, images, audio, video, or documents to any entity. Only URLs/paths are stored — not the actual files. Examples: profile photos on people, architecture diagrams on components, screenshots on tickets.

### Audit Log

Use `log_audit` to record changes for traceability — who changed what field, from what value to what value. Use `get_audit_log` to review change history for any entity.

---

## Search Result Ranking

Results are scored by:
- **Text relevance** (40%) — how well the query matches
- **Recency** (20%) — newer items rank higher (decays over 30 days)
- **Pinned status** (20%) — pinned items get a major boost
- **Access frequency** (10%) — frequently retrieved items rank higher
- **Severity** (10%) — critical rules always surface

---

## Keywords Matter

Good keywords make knowledge findable. Always include:
- **Domain terms**: auth, database, api, testing, deployment
- **Technology terms**: python, jwt, sqlalchemy, react
- **Action terms**: migration, refactor, debug, optimize
- **Specific identifiers**: function names, file names, error codes

---

## Quick Reference

| When | Call |
|------|------|
| Conversation starts | `start_session` → read resume → `get_instructions` → `get_rules` |
| Made a decision | `add_thought(type="decision")` |
| Learned a do/don't | `add_rule` |
| Something broke & was fixed | `add_error_pattern` |
| Found a bug | `create_ticket(type="bug")` |
| Planning work | `create_plan` → `add_plan_task` |
| Defining what to build | `create_spec` → `create_feature` |
| Architecture decision | `create_decision` |
| API endpoint discovered | `create_endpoint` |
| New dependency added | `create_dependency` |
| Secret registered | `create_credential` |
| Deploy happening | `create_deployment` |
| Incident reported | `create_incident` |
| Operational procedure | `create_runbook` |
| Comment on anything | `add_comment` |
| Attach a file/URL | `add_attachment` |
| About to compact | `save_snapshot` |
| Want agent stats | `get_agent_stats` |
| Conversation ends | `end_session` with full summary |
