---
title: Search Tools
layout: default
parent: Tools Reference
nav_order: 3
---

# Search & Retrieval Tools

Six tools for finding and retrieving knowledge: full-text search, vector search, rule lookup, session history, and graph traversal.

---

## `search`

Unified full-text search across thoughts, rules, error patterns, and session summaries. Results are ranked by the [scoring formula](../concepts/scoring).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | **yes** | — | Search query (natural language or keywords) |
| `project` | string | no | `null` | Filter by project tag |
| `branch` | string | no | `null` | Filter by git branch (exact match) |
| `type_filter` | string | no | `null` | `thought`, `rule`, `error_pattern`, or `session_summary` |
| `include_archived` | boolean | no | `false` | Include archived items |
| `limit` | integer | no | `20` | Max results |

**Branch support:** Yes (exact match)

### Example Request

```json
{
  "query": "authentication approach",
  "project": "myapp",
  "branch": "feature/auth",
  "limit": 10
}
```

### Example Response

```json
{
  "count": 2,
  "results": [
    {
      "id": "t1b2c3",
      "_type": "thought",
      "_score": 0.7234,
      "summary": "Using PKCE flow for OAuth",
      "type": "decision",
      "project": "myapp",
      "branch": "featureauth"
    },
    {
      "id": "r4d5e6",
      "_type": "rule",
      "_score": 0.6891,
      "summary": "Always use state param in OAuth redirects",
      "severity": "critical"
    }
  ]
}
```

---

## `search_by_embedding`

RAG-style semantic search using vector similarity. Requires embeddings to have been stored via `store_embedding`. Returns items ranked by cosine distance.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `embedding` | number[] | **yes** | — | Embedding vector |
| `project` | string | no | `null` | Filter by project |
| `branch` | string | no | `null` | Filter by branch |
| `type_filter` | string | no | `null` | `thought`, `rule`, `error_pattern`, or `session_summary` |
| `limit` | integer | no | `20` | Max results |

**Branch support:** Yes (exact match on embedding metadata)

Returns items with `_distance` (cosine distance) and `_score` (`1.0 - distance`).

---

## `store_embedding`

Store a vector embedding for an item (thought, rule, error pattern, session summary). Enables semantic/RAG search for that item.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `item_id` | string | **yes** | — | ID of the item to embed |
| `item_type` | string | **yes** | — | `thought`, `rule`, `error_pattern`, or `session_summary` |
| `text_content` | string | **yes** | — | The text that was embedded |
| `embedding` | number[] | **yes** | — | Embedding vector |
| `model_name` | string | **yes** | — | Embedding model name |

### Example Request

```json
{
  "item_id": "t1b2c3",
  "item_type": "thought",
  "text_content": "Using PKCE flow for OAuth authentication",
  "embedding": [0.123, -0.456, 0.789, "..."],
  "model_name": "all-MiniLM-L6-v2"
}
```

---

## `get_rules`

Get active rules for a project/context. Always includes critical rules. Filter by severity and keywords to get the most relevant rules.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | `null` | Project tag |
| `branch` | string | no | `null` | Git branch (returns branch-specific + branch-global rules) |
| `severity` | string | no | `null` | Filter: `critical`, `preference`, or `context_dependent` |
| `keywords` | string[] | no | `null` | Filter by keyword overlap |
| `include_global` | boolean | no | `true` | Include rules with no project tag |
| `limit` | integer | no | `50` | Max results |

**Branch support:** Yes (NULL-inclusive — returns `branch=X` plus `branch IS NULL`)

### Example Request

```json
{
  "project": "myapp",
  "branch": "feature/auth",
  "keywords": ["auth", "security"],
  "severity": "critical"
}
```

### Example Response

```json
{
  "count": 1,
  "rules": [
    {
      "id": "r4d5e6",
      "summary": "Always use state param in OAuth redirects",
      "type": "do",
      "severity": "critical",
      "project": "myapp",
      "branch": null,
      "reinforcement_count": 3,
      "pinned": 1
    }
  ]
}
```

---

## `get_session_history`

List past sessions with summaries, ordered by most recent.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | `null` | Filter by project |
| `branch` | string | no | `null` | Filter by branch (exact match) |
| `agent_type` | string | no | `null` | Filter by agent type |
| `limit` | integer | no | `20` | Max results |

**Branch support:** Yes (exact match)

### Example Request

```json
{
  "project": "myapp",
  "branch": "feature/auth",
  "limit": 5
}
```

---

## `get_related`

Get all items linked to a given thought or rule via the knowledge graph (`thought_links` table).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `item_id` | string | **yes** | — | ID of the item to find links for |

Returns all links where the item appears as either `from_id` or `to_id`, with link type and direction.

### Example Request

```json
{
  "item_id": "t1b2c3"
}
```

### Example Response

```json
{
  "count": 2,
  "links": [
    {
      "id": "l1a2b3",
      "from_id": "t1b2c3",
      "from_type": "thought",
      "to_id": "r4d5e6",
      "to_type": "rule",
      "link_type": "informs"
    },
    {
      "id": "l7c8d9",
      "from_id": "e9f0a1",
      "from_type": "error_pattern",
      "to_id": "t1b2c3",
      "to_type": "thought",
      "link_type": "caused_by"
    }
  ]
}
```
