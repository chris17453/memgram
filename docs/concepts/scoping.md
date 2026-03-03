# Two-Dimensional Scoping

Memgram uses a two-dimensional scoping system: **project** + **branch**. Both dimensions are optional and independently applied.

## Dimensions

| Dimension | Purpose | Example |
|-----------|---------|---------|
| `project` | Isolates knowledge per codebase/repo | `"myapp"`, `"oxideos"` |
| `branch` | Isolates knowledge per feature branch | `"featureauth"`, `"fixloginbug"` |

Both values are [normalized](normalization.md) before storage — lowercased with non-alphanumeric characters stripped.

## Scoping Levels

| Project | Branch | Scope | Use Case |
|---------|--------|-------|----------|
| `NULL` | `NULL` | Fully global | Cross-project knowledge |
| Set | `NULL` | Project-wide | Coding standards, architecture decisions |
| Set | Set | Branch-specific | Feature decisions, temporary workarounds |

## Retrieval Behavior

Different tools use different matching strategies:

### NULL-Inclusive Matching

**`get_rules`** and **`get_resume_context`** use NULL-inclusive matching. When you pass `branch="featureauth"`, you get:

- Items where `branch='featureauth'` (branch-specific)
- **Plus** items where `branch IS NULL` (branch-global)

This means project-wide rules always surface regardless of which branch you're on.

```sql
-- Simplified query logic
WHERE (branch = ? OR branch IS NULL)
```

### Exact Matching

**`search`** and **`get_session_history`** use exact matching — only items with the specified branch are returned.

```sql
-- Simplified query logic
WHERE branch = ?
```

## When to Use Each Scope

| Scenario | Use `branch`? | Why |
|----------|---------------|-----|
| Working on a feature branch | Yes | Isolate branch-specific context |
| Recording a project-wide coding standard | No | Should be visible on all branches |
| Logging a workaround specific to a feature | Yes | Shouldn't leak to other branches |
| Adding a rule that applies everywhere | No | Omit branch for project-wide rules |
| Debugging an issue on a specific branch | Yes | Scope errors/thoughts to the branch |

## After Branch Merge

When a branch merges, its branch-scoped knowledge stays in the database but stops surfacing — since no one queries that branch name anymore. This is intentional: the knowledge is preserved for historical reference but doesn't pollute other branches.

If a branch-scoped rule should become project-wide after merge, create a new rule without the `branch` parameter.
