# Data Model

Memgram uses 33 core tables, 21 FTS5 virtual tables, and 1 sqlite-vec virtual table.

## Tables Overview

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `sessions` | Active and completed sessions | agent_type, model, project, branch, goal, status |
| `thoughts` | Observations, decisions, ideas, notes | summary, content, type, project, branch, agent_type, agent_model, keywords |
| `rules` | Learned do/don't patterns | summary, type, severity, project, branch, agent_type, agent_model, reinforcement_count |
| `compaction_snapshots` | Context window checkpoints | session_id, current_goal, progress_summary, next_steps |
| `thought_links` | Knowledge graph edges | from_id, from_type, to_id, to_type, link_type |
| `error_patterns` | Failure records with fixes | error_description, cause, fix, prevention_rule_id, agent_type, agent_model |
| `project_summaries` | Living project overviews | project, summary, tech_stack, key_patterns, active_goals |
| `session_summaries` | Structured session wrap-ups | session_id, outcome, decisions_made, files_modified |
| `thought_groups` | Named item clusters | name, description, project, branch |
| `group_members` | Group membership (junction) | group_id, item_id, item_type |
| `embedding_meta` | Vector embedding metadata | item_id, item_type, text_content, model_name |
| `plans` | Work tracking plans | title, scope, priority, status, project, branch, due_date |
| `plan_tasks` | Individual tasks within plans | plan_id, title, status, assignee, depends_on, position |
| `specs` | Formal specifications | title, description, status, priority, acceptance_criteria, author_id |
| `features` | User-facing capabilities | name, description, status, priority, spec_id, lead_id |
| `components` | System components | name, description, type, owner_id, tech_stack |
| `people` | Team members and contacts | name, type, role, email, github, skills |
| `teams` | Groups of people | name, description, project, lead_id |
| `team_members` | Team membership (junction) | team_id, person_id, role |
| `tickets` | Bug/task/feature tracking with ticket numbers | ticket_number, title, status, priority, type, assignee_id, project |
| `instructions` | Agent behavioral instructions (scoped, ordered) | section, title, content, scope, project, branch, active |
| `attachments` | URL/file references on any entity | entity_id, entity_type, url, type, label |
| `endpoints` | API endpoint definitions | method, path, base_url, auth_type, status, project |
| `credentials` | Secret references (not actual secrets) | name, type, provider, vault_path, env_var, project |
| `environments` | Dev/staging/prod environments | name, type, url, config, project |
| `deployments` | Deployment records | version, environment_id, status, strategy, project |
| `builds` | CI/CD build records | name, pipeline, status, trigger_type, commit_sha, project |
| `incidents` | Incident tracking | title, severity, status, root_cause, resolution, project |
| `dependencies` | External dependencies | name, version, type, source, license, project |
| `runbooks` | Operational procedures | title, steps, trigger_conditions, project |
| `decisions` | Architecture Decision Records | title, status, context, options, outcome, project |
| `comments` | Threaded comments on any entity | entity_id, entity_type, author, content, parent_id |
| `audit_log` | Immutable change tracking | entity_id, entity_type, action, actor, project |

### Virtual Tables

| Table | Type | Purpose |
|-------|------|---------|
| `thoughts_fts` | FTS5 | Full-text search on thoughts (summary, content, keywords) |
| `rules_fts` | FTS5 | Full-text search on rules (summary, content, keywords) |
| `error_patterns_fts` | FTS5 | Full-text search on errors (description, cause, fix, keywords) |
| `session_summaries_fts` | FTS5 | Full-text search on session summaries (goal, outcome, hints) |
| `plans_fts` | FTS5 | Full-text search on plans (title, description, tags) |
| `specs_fts` | FTS5 | Full-text search on specs (title, description, tags) |
| `features_fts` | FTS5 | Full-text search on features (name, description, tags) |
| `components_fts` | FTS5 | Full-text search on components (name, description, tags) |
| `tickets_fts` | FTS5 | Full-text search on tickets (ticket_number, title, description, tags) |
| `instructions_fts` | FTS5 | Full-text search on instructions (section, title, content, tags) |
| `endpoints_fts` | FTS5 | Full-text search on endpoints (method, path, description, tags) |
| `credentials_fts` | FTS5 | Full-text search on credentials (name, provider, description, tags) |
| `environments_fts` | FTS5 | Full-text search on environments (name, description, tags) |
| `deployments_fts` | FTS5 | Full-text search on deployments (version, description, tags) |
| `builds_fts` | FTS5 | Full-text search on builds (name, pipeline, tags) |
| `incidents_fts` | FTS5 | Full-text search on incidents (title, description, root_cause, resolution, tags) |
| `dependencies_fts` | FTS5 | Full-text search on dependencies (name, description, tags) |
| `runbooks_fts` | FTS5 | Full-text search on runbooks (title, description, trigger_conditions, tags) |
| `decisions_fts` | FTS5 | Full-text search on decisions (title, context, outcome, consequences, tags) |
| `comments_fts` | FTS5 | Full-text search on comments (author, content, tags) |
| `embeddings_vec` | sqlite-vec | Vector similarity search (cosine distance) |

## Relationships

```
sessions ──< thoughts          (session_id FK)
sessions ──< rules             (session_id FK)
sessions ──< compaction_snapshots (session_id FK)
sessions ──< error_patterns    (session_id FK)
sessions ──< session_summaries (session_id FK, UNIQUE)
sessions ──< plans             (session_id FK)

rules ──< error_patterns       (prevention_rule_id FK)

thought_groups ──< group_members (group_id FK)
group_members ──> thoughts | rules | error_patterns (item_id, polymorphic)

thought_links ──> thoughts | rules (from_id/to_id, polymorphic)

embedding_meta ──> thoughts | rules | error_patterns | session_summaries (item_id, polymorphic)
embeddings_vec ──> embedding_meta (item_id)

plans ──< plan_tasks           (plan_id FK)
plan_tasks ──> plan_tasks      (depends_on FK, self-referential)

specs ──< features             (spec_id FK)
people ──< specs               (author_id FK)
people ──< features            (lead_id FK)
people ──< components          (owner_id FK)
people ──< teams               (lead_id FK)
teams ──< team_members         (team_id FK)
people ──< team_members        (person_id FK)

people ──< tickets             (assignee_id, reporter_id FKs)
tickets ──< tickets            (parent_id FK, self-referential sub-tickets)

attachments ──> any entity     (entity_id + entity_type, polymorphic)
comments ──> any entity        (entity_id + entity_type, polymorphic)
comments ──< comments          (parent_id FK, self-referential threading)
audit_log ──> any entity       (entity_id + entity_type, polymorphic)

environments ──< deployments   (environment_id FK)
deployments ──> deployments    (rollback_to FK, self-referential)
decisions ──> decisions        (superseded_by FK, self-referential)
people ──< incidents           (lead_id FK)
people ──< decisions           (author_id FK)
```

## Scoped Tables

Multiple tables have the `branch` column for two-dimensional scoping:

| Table | `project` | `branch` |
|-------|-----------|----------|
| `sessions` | yes | yes |
| `thoughts` | yes | yes |
| `rules` | yes | yes |
| `error_patterns` | yes | yes |
| `session_summaries` | yes | yes |
| `thought_groups` | yes | yes |
| `embedding_meta` | yes | yes |
| `plans` | yes | yes |
| `specs` | yes | yes |
| `features` | yes | yes |
| `components` | yes | yes |
| `teams` | yes | — |
| `tickets` | yes | yes |
| `instructions` | yes | yes |
| `endpoints` | yes | yes |
| `credentials` | yes | — |
| `environments` | yes | — |
| `deployments` | yes | yes |
| `builds` | yes | yes |
| `incidents` | yes | — |
| `dependencies` | yes | — |
| `runbooks` | yes | — |
| `decisions` | yes | yes |
| `comments` | yes | — |
| `audit_log` | yes | — |

See [Scoping](../concepts/scoping.md) for how these columns affect retrieval.

## Indexes

The database has indexes for:

- `project` and `branch` columns (single and composite)
- `pinned` columns (partial index where `pinned=1`)
- `session_id` foreign keys
- `severity` on rules
- `status` on sessions
- `from_id` and `to_id` on thought_links
- `item_id` on group_members
- `item_type` on embedding_meta

See the [full schema reference](schema.md) for column-level details.
