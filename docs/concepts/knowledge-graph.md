---
title: Knowledge Graph
layout: default
parent: Concepts
nav_order: 4
---

# Knowledge Graph

Memgram builds a knowledge graph through three mechanisms: **links**, **groups**, and **pinning**. Together, they let you structure and retrieve related knowledge.

---

## Links

Links create directional connections between items (thoughts, rules, error patterns) via the `thought_links` table.

### Link Types

| Type | Direction | Meaning |
|------|-----------|---------|
| `informs` | A → B | A provides context for B |
| `contradicts` | A → B | A conflicts with B |
| `supersedes` | A → B | A replaces B |
| `related` | A ↔ B | General relationship |
| `caused_by` | A → B | A was caused by B |

### Creating Links

```json
{
  "tool": "link_items",
  "from_id": "error-id",
  "from_type": "error_pattern",
  "to_id": "rule-id",
  "to_type": "rule",
  "link_type": "caused_by"
}
```

### Retrieving Links

`get_related(item_id)` returns all links where the item appears as either `from_id` or `to_id`.

---

## Groups

Groups cluster related items under a named label. A group can contain thoughts, rules, and error patterns.

### Use Cases

- Cluster everything about a subsystem: `"authentication"`, `"payment-processing"`
- Track a feature's knowledge: `"oauth-integration"`
- Organize by concern: `"performance-issues"`, `"security-rules"`

### Operations

| Tool | Description |
|------|-------------|
| `create_group` | Create a named group with optional project/branch scope |
| `add_to_group` | Add a thought, rule, or error pattern to a group |
| `remove_from_group` | Remove an item from a group |
| `get_group` | Retrieve a group with all member details |

### Example

```json
// Create
{ "tool": "create_group", "name": "auth-system", "description": "Authentication subsystem", "project": "myapp" }

// Add items
{ "tool": "add_to_group", "group_id": "abc123", "item_id": "thought-1", "item_type": "thought" }
{ "tool": "add_to_group", "group_id": "abc123", "item_id": "rule-1", "item_type": "rule" }

// Retrieve
{ "tool": "get_group", "name": "auth-system", "project": "myapp" }
```

Group names are [normalized](normalization), so `"Auth System"` and `"auth-system"` resolve to the same group.

---

## Pinning

Pinning marks an item as always-relevant. Pinned items are automatically included in `get_resume_context()`, ensuring they're loaded at the start of every session.

### What Gets Pinned

Pinning applies to **thoughts** and **rules** only.

```json
{ "tool": "pin_item", "item_id": "rule-123", "pinned": true }
```

### Pinned Items in Resume Context

When `get_resume_context()` is called, it returns:
- All pinned thoughts (matching project/branch scope, plus `branch IS NULL`)
- All pinned or critical rules (matching project/branch scope, plus `branch IS NULL`)

### Pinning Strategy

Use pinning sparingly — only for truly critical, always-relevant knowledge:
- Architecture decisions that affect every session
- Critical security rules
- Key project conventions

Too many pinned items dilute the resume context and waste token budget.

---

## How They Work Together

```
┌─────────────┐    link: caused_by    ┌─────────────┐
│ Error Pattern│───────────────────────▶│    Rule      │
│ "CSRF error" │                       │ "Use state   │
└─────────────┘                       │  param"  📌  │
       │                              └─────────────┘
       │ member of                           │ member of
       ▼                                     ▼
┌─────────────────────────────────────────────────┐
│              Group: "auth-system"                │
│  Also contains: 3 thoughts, 2 other rules       │
└─────────────────────────────────────────────────┘
```

- The error pattern is **linked** to the rule that prevents it
- Both are **members** of the "auth-system" group
- The rule is **pinned** so it always loads in context
- Retrieving the group gives you the full cluster of auth knowledge
