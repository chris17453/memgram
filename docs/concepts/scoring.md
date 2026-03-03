---
title: Scoring
layout: default
parent: Concepts
nav_order: 3
---

# Search Result Scoring

Memgram uses a 5-factor scoring formula to rank search results. The formula combines text relevance with contextual signals to surface the most useful results.

---

## Formula

```
score = (fts_rank × 0.4) + (recency × 0.2) + (access × 0.1) + (pinned × 0.2) + (severity × 0.1)
```

Total maximum score: **1.0**

---

## Factors

### 1. Text Relevance (40%)

**Weight: 0.4**

The FTS5 rank score, which measures how well the search query matches the item's text content. FTS5 considers term frequency, position, and field weights across `summary`, `content`, and `keywords` columns.

FTS5 returns negative rank values (more negative = better match). Memgram takes the absolute value before applying the weight.

### 2. Recency (20%)

**Weight: 0.2**

A linear decay over 30 days:

```
recency = max(0.0, 1.0 - (age_days / 30.0))
```

| Age | Recency Score |
|-----|--------------|
| Today | 1.0 |
| 7 days | 0.77 |
| 15 days | 0.50 |
| 30 days | 0.0 |
| 30+ days | 0.0 |

Items older than 30 days get no recency bonus but can still rank high through other factors.

### 3. Pinned Status (20%)

**Weight: 0.2**

Binary — pinned items get a flat `+0.2` bonus. This ensures pinned items always appear near the top of search results regardless of age.

### 4. Access Frequency (10%)

**Weight: 0.1**

Based on `access_count`, capped at 100:

```
access = min(access_count, 100) / 100.0
```

Frequently accessed items get a small ranking boost. The cap prevents runaway scores from heavily-accessed items.

### 5. Severity (10%)

**Weight: 0.1**

Only applies to rules:

| Severity | Bonus |
|----------|-------|
| `critical` | +0.1 |
| `preference` | +0.03 |
| `context_dependent` | +0.0 |
| (no severity) | +0.0 |

Critical rules always surface when relevant.

---

## Which Items Use Scoring

| Type | Scored? | Notes |
|------|---------|-------|
| Thoughts | Yes | Full 5-factor formula |
| Rules | Yes | Full 5-factor formula (severity applies) |
| Error patterns | Partial | FTS rank only (no access_count/pinned fields) |
| Session summaries | Partial | FTS rank only |

---

## Scoring in Context

The `search()` method aggregates results from all four FTS tables, applies scoring, sorts by score descending, and returns the top `limit` results. Each result includes a `_score` field so clients can see the ranking value.

Results from `search_by_embedding()` (vector search) use cosine distance instead: `score = max(0, 1.0 - distance)`.
