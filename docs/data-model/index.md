---
title: Data Model
layout: default
nav_order: 6
has_children: true
---

# Data Model

Memgram uses 12 core tables, 4 FTS5 virtual tables, and 1 sqlite-vec virtual table.

---

## Tables Overview

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `sessions` | Active and completed sessions | agent_type, model, project, branch, goal, status |
| `thoughts` | Observations, decisions, ideas, notes | summary, content, type, project, branch, keywords |
| `rules` | Learned do/don't patterns | summary, type, severity, project, branch, reinforcement_count |
| `compaction_snapshots` | Context window checkpoints | session_id, current_goal, progress_summary, next_steps |
| `thought_links` | Knowledge graph edges | from_id, from_type, to_id, to_type, link_type |
| `error_patterns` | Failure records with fixes | error_description, cause, fix, prevention_rule_id |
| `project_summaries` | Living project overviews | project, summary, tech_stack, key_patterns, active_goals |
| `session_summaries` | Structured session wrap-ups | session_id, outcome, decisions_made, files_modified |
| `thought_groups` | Named item clusters | name, description, project, branch |
| `group_members` | Group membership (junction) | group_id, item_id, item_type |
| `embedding_meta` | Vector embedding metadata | item_id, item_type, text_content, model_name |

### Virtual Tables

| Table | Type | Purpose |
|-------|------|---------|
| `thoughts_fts` | FTS5 | Full-text search on thoughts (summary, content, keywords) |
| `rules_fts` | FTS5 | Full-text search on rules (summary, content, keywords) |
| `error_patterns_fts` | FTS5 | Full-text search on errors (description, cause, fix, keywords) |
| `session_summaries_fts` | FTS5 | Full-text search on session summaries (goal, outcome, hints) |
| `embeddings_vec` | sqlite-vec | Vector similarity search (cosine distance) |

---

## Relationships

```
sessions ──< thoughts          (session_id FK)
sessions ──< rules             (session_id FK)
sessions ──< compaction_snapshots (session_id FK)
sessions ──< error_patterns    (session_id FK)
sessions ──< session_summaries (session_id FK, UNIQUE)

rules ──< error_patterns       (prevention_rule_id FK)

thought_groups ──< group_members (group_id FK)
group_members ──> thoughts | rules | error_patterns (item_id, polymorphic)

thought_links ──> thoughts | rules (from_id/to_id, polymorphic)

embedding_meta ──> thoughts | rules | error_patterns | session_summaries (item_id, polymorphic)
embeddings_vec ──> embedding_meta (item_id)
```

---

## Scoped Tables

Seven tables have the `branch` column for two-dimensional scoping:

| Table | `project` | `branch` |
|-------|-----------|----------|
| `sessions` | yes | yes |
| `thoughts` | yes | yes |
| `rules` | yes | yes |
| `error_patterns` | yes | yes |
| `session_summaries` | yes | yes |
| `thought_groups` | yes | yes |
| `embedding_meta` | yes | yes |

See [Scoping](../concepts/scoping) for how these columns affect retrieval.

---

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

See the [full schema reference](schema) for column-level details.
