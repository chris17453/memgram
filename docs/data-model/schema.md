# Schema Reference

Full column-level schema for all memgram tables.

## `sessions`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex (12 chars) |
| `agent_type` | TEXT | NOT NULL | — | AI agent type |
| `model` | TEXT | NOT NULL | — | Model name |
| `project` | TEXT | yes | `NULL` | Project tag (normalized) |
| `branch` | TEXT | yes | `NULL` | Branch name (normalized) |
| `goal` | TEXT | yes | `NULL` | Session goal |
| `status` | TEXT | NOT NULL | `'active'` | `active` or `completed` |
| `summary` | TEXT | yes | `NULL` | Session summary (set on end) |
| `compaction_count` | INTEGER | NOT NULL | `0` | Number of snapshots saved |
| `started_at` | TEXT | NOT NULL | — | ISO 8601 UTC timestamp |
| `ended_at` | TEXT | yes | `NULL` | ISO 8601 UTC timestamp |
| `metadata` | TEXT | yes | `NULL` | JSON blob |

**Indexes:** `project`, `branch`, `status`, `(project, branch)`

## `thoughts`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex (12 chars) |
| `session_id` | TEXT | yes | `NULL` | FK -> sessions(id) |
| `type` | TEXT | NOT NULL | `'note'` | `observation`, `decision`, `idea`, `error`, `pattern`, `note` |
| `summary` | TEXT | NOT NULL | — | Short searchable summary |
| `content` | TEXT | NOT NULL | `''` | Full content |
| `project` | TEXT | yes | `NULL` | Project tag (normalized) |
| `branch` | TEXT | yes | `NULL` | Branch name (normalized) |
| `agent_type` | TEXT | yes | `NULL` | AI agent type (auto-resolved from session) |
| `agent_model` | TEXT | yes | `NULL` | Model identifier (auto-resolved from session) |
| `keywords` | TEXT | NOT NULL | `'[]'` | JSON array of strings |
| `associated_files` | TEXT | NOT NULL | `'[]'` | JSON array of file paths |
| `pinned` | INTEGER | NOT NULL | `0` | 1 = pinned |
| `archived` | INTEGER | NOT NULL | `0` | 1 = archived |
| `access_count` | INTEGER | NOT NULL | `0` | Read count |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |
| `updated_at` | TEXT | NOT NULL | — | ISO 8601 UTC |
| `last_accessed` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `project`, `branch`, `session_id`, `pinned` (partial), `(project, branch)`, `(agent_type, agent_model)`

## `rules`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex (12 chars) |
| `session_id` | TEXT | yes | `NULL` | FK -> sessions(id) |
| `type` | TEXT | NOT NULL | `'do'` | `do`, `dont`, `context_dependent` |
| `severity` | TEXT | NOT NULL | `'preference'` | `critical`, `preference`, `context_dependent` |
| `summary` | TEXT | NOT NULL | — | Short rule description |
| `content` | TEXT | NOT NULL | `''` | Full explanation |
| `condition` | TEXT | yes | `NULL` | When the rule applies |
| `project` | TEXT | yes | `NULL` | Project tag (normalized) |
| `branch` | TEXT | yes | `NULL` | Branch name (normalized) |
| `agent_type` | TEXT | yes | `NULL` | AI agent type (auto-resolved from session) |
| `agent_model` | TEXT | yes | `NULL` | Model identifier (auto-resolved from session) |
| `keywords` | TEXT | NOT NULL | `'[]'` | JSON array |
| `associated_files` | TEXT | NOT NULL | `'[]'` | JSON array |
| `pinned` | INTEGER | NOT NULL | `0` | 1 = pinned |
| `archived` | INTEGER | NOT NULL | `0` | 1 = archived |
| `reinforcement_count` | INTEGER | NOT NULL | `1` | Times reinforced |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |
| `updated_at` | TEXT | NOT NULL | — | ISO 8601 UTC |
| `last_accessed` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `project`, `branch`, `session_id`, `severity`, `pinned` (partial), `(project, branch)`, `(agent_type, agent_model)`

## `compaction_snapshots`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex |
| `session_id` | TEXT | NOT NULL | — | FK -> sessions(id) |
| `sequence_num` | INTEGER | NOT NULL | `1` | Auto-incrementing per session |
| `current_goal` | TEXT | yes | `NULL` | Current work goal |
| `progress_summary` | TEXT | yes | `NULL` | What's done so far |
| `open_questions` | TEXT | NOT NULL | `'[]'` | JSON array |
| `blockers` | TEXT | NOT NULL | `'[]'` | JSON array |
| `next_steps` | TEXT | NOT NULL | `'[]'` | JSON array |
| `active_files` | TEXT | NOT NULL | `'[]'` | JSON array |
| `key_decisions` | TEXT | NOT NULL | `'[]'` | JSON array |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `session_id`

## `thought_links`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex |
| `from_id` | TEXT | NOT NULL | — | Source item ID |
| `from_type` | TEXT | NOT NULL | — | `thought`, `rule` |
| `to_id` | TEXT | NOT NULL | — | Target item ID |
| `to_type` | TEXT | NOT NULL | — | `thought`, `rule` |
| `link_type` | TEXT | NOT NULL | `'related'` | `informs`, `contradicts`, `supersedes`, `related`, `caused_by` |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `from_id`, `to_id`

## `error_patterns`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex |
| `session_id` | TEXT | yes | `NULL` | FK -> sessions(id) |
| `error_description` | TEXT | NOT NULL | — | What went wrong |
| `cause` | TEXT | yes | `NULL` | Root cause |
| `fix` | TEXT | yes | `NULL` | How it was fixed |
| `prevention_rule_id` | TEXT | yes | `NULL` | FK -> rules(id) |
| `project` | TEXT | yes | `NULL` | Project tag (normalized) |
| `branch` | TEXT | yes | `NULL` | Branch name (normalized) |
| `agent_type` | TEXT | yes | `NULL` | AI agent type (auto-resolved from session) |
| `agent_model` | TEXT | yes | `NULL` | Model identifier (auto-resolved from session) |
| `keywords` | TEXT | NOT NULL | `'[]'` | JSON array |
| `associated_files` | TEXT | NOT NULL | `'[]'` | JSON array |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `project`, `branch`, `(agent_type, agent_model)`

## `project_summaries`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex |
| `project` | TEXT | NOT NULL, UNIQUE | — | Project tag |
| `summary` | TEXT | NOT NULL | `''` | Project overview |
| `tech_stack` | TEXT | NOT NULL | `'[]'` | JSON array |
| `key_patterns` | TEXT | NOT NULL | `'[]'` | JSON array |
| `active_goals` | TEXT | NOT NULL | `'[]'` | JSON array |
| `total_sessions` | INTEGER | NOT NULL | `0` | Auto-calculated |
| `total_thoughts` | INTEGER | NOT NULL | `0` | Auto-calculated |
| `total_rules` | INTEGER | NOT NULL | `0` | Auto-calculated |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |
| `updated_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

## `session_summaries`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex |
| `session_id` | TEXT | NOT NULL, UNIQUE | — | FK -> sessions(id) |
| `project` | TEXT | yes | `NULL` | Project tag (normalized) |
| `branch` | TEXT | yes | `NULL` | Branch name (normalized) |
| `goal` | TEXT | yes | `NULL` | Session goal |
| `outcome` | TEXT | yes | `NULL` | What happened |
| `decisions_made` | TEXT | NOT NULL | `'[]'` | JSON array |
| `rules_learned` | TEXT | NOT NULL | `'[]'` | JSON array of rule IDs |
| `errors_encountered` | TEXT | NOT NULL | `'[]'` | JSON array of error IDs |
| `files_modified` | TEXT | NOT NULL | `'[]'` | JSON array |
| `unresolved_items` | TEXT | NOT NULL | `'[]'` | JSON array |
| `next_session_hints` | TEXT | yes | `NULL` | Hints for next session |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `branch`

## `thought_groups`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | TEXT | **PK** | — | UUID hex |
| `name` | TEXT | NOT NULL | — | Group name (normalized) |
| `description` | TEXT | NOT NULL | `''` | Group description |
| `project` | TEXT | yes | `NULL` | Project scope |
| `branch` | TEXT | yes | `NULL` | Branch scope |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |
| `updated_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `branch`

## `group_members`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `group_id` | TEXT | NOT NULL | — | FK -> thought_groups(id) |
| `item_id` | TEXT | NOT NULL | — | Item ID (polymorphic) |
| `item_type` | TEXT | NOT NULL | — | `thought`, `rule`, `error_pattern` |
| `added_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Primary Key:** `(group_id, item_id)`

**Indexes:** `item_id`

## `embedding_meta`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `item_id` | TEXT | **PK** | — | Item ID (matches embeddings_vec) |
| `item_type` | TEXT | NOT NULL | — | `thought`, `rule`, `error_pattern`, `session_summary` |
| `text_content` | TEXT | NOT NULL | — | Text that was embedded |
| `model_name` | TEXT | NOT NULL | — | Embedding model name |
| `project` | TEXT | yes | `NULL` | Project tag |
| `branch` | TEXT | yes | `NULL` | Branch name |
| `created_at` | TEXT | NOT NULL | — | ISO 8601 UTC |

**Indexes:** `item_type`, `branch`

## `embeddings_vec` (sqlite-vec)

| Column | Type | Description |
|--------|------|-------------|
| `item_id` | TEXT | Primary key, matches embedding_meta |
| `embedding` | float[N] | Vector (N = embedding_dim, default 384) |

Created as: `CREATE VIRTUAL TABLE embeddings_vec USING vec0(item_id TEXT PRIMARY KEY, embedding float[384])`

## FTS5 Virtual Tables

### `thoughts_fts`

Columns indexed: `id` (UNINDEXED), `summary`, `content`, `keywords`. Content table: `thoughts`.

### `rules_fts`

Columns indexed: `id` (UNINDEXED), `summary`, `content`, `keywords`. Content table: `rules`.

### `error_patterns_fts`

Columns indexed: `id` (UNINDEXED), `error_description`, `cause`, `fix`, `keywords`. Content table: `error_patterns`.

### `session_summaries_fts`

Columns indexed: `id` (UNINDEXED), `goal`, `outcome`, `next_session_hints`. Content table: `session_summaries`.

All FTS tables use `content='<table>'` and `content_rowid='rowid'` with automatic sync triggers (INSERT, UPDATE, DELETE).
