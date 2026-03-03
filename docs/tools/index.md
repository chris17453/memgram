---
title: Tools Reference
layout: default
nav_order: 5
has_children: true
---

# Tools Reference

Memgram provides 24 MCP tools organized into five categories.

---

## Overview

| # | Tool | Category | Branch | Description |
|---|------|----------|--------|-------------|
| 1 | [`start_session`](sessions#start_session) | Session | yes | Begin a session, get resume context |
| 2 | [`end_session`](sessions#end_session) | Session | — | Close with structured summary |
| 3 | [`save_snapshot`](sessions#save_snapshot) | Session | — | Compaction checkpoint |
| 4 | [`get_resume_context`](sessions#get_resume_context) | Session | yes | Everything needed to resume |
| 5 | [`add_thought`](knowledge#add_thought) | Knowledge | yes | Store a thought/decision/observation |
| 6 | [`update_thought`](knowledge#update_thought) | Knowledge | yes | Modify an existing thought |
| 7 | [`add_rule`](knowledge#add_rule) | Knowledge | yes | Store a learned do/don't pattern |
| 8 | [`reinforce_rule`](knowledge#reinforce_rule) | Knowledge | — | Bump rule confidence |
| 9 | [`add_error_pattern`](knowledge#add_error_pattern) | Knowledge | yes | Log failure with cause and fix |
| 10 | [`link_items`](knowledge#link_items) | Knowledge | — | Connect items in the graph |
| 11 | [`search`](search#search) | Search | yes | FTS5 full-text search |
| 12 | [`search_by_embedding`](search#search_by_embedding) | Search | yes | Vector similarity search (RAG) |
| 13 | [`store_embedding`](search#store_embedding) | Search | — | Store a vector embedding |
| 14 | [`get_rules`](search#get_rules) | Search | yes | Get active rules for context |
| 15 | [`get_session_history`](search#get_session_history) | Search | yes | List past sessions |
| 16 | [`get_related`](search#get_related) | Search | — | Items linked via graph |
| 17 | [`get_project_summary`](projects#get_project_summary) | Projects | — | Get living project overview |
| 18 | [`update_project_summary`](projects#update_project_summary) | Projects | — | Update project overview |
| 19 | [`create_group`](groups#create_group) | Groups | yes | Create a named cluster |
| 20 | [`add_to_group`](groups#add_to_group) | Groups | — | Add item to group |
| 21 | [`remove_from_group`](groups#remove_from_group) | Groups | — | Remove item from group |
| 22 | [`get_group`](groups#get_group) | Groups | yes | Get group with members |
| 23 | [`pin_item`](maintenance#pin_item) | Maintenance | — | Pin/unpin for resume context |
| 24 | [`archive_item`](maintenance#archive_item) | Maintenance | — | Archive (exclude from search) |

**Branch column**: "yes" means the tool accepts a `branch` parameter for scoped operations.

---

## Detailed Pages

- [Session Tools](sessions) — `start_session`, `end_session`, `save_snapshot`, `get_resume_context`
- [Knowledge Tools](knowledge) — `add_thought`, `update_thought`, `add_rule`, `reinforce_rule`, `add_error_pattern`, `link_items`
- [Search Tools](search) — `search`, `search_by_embedding`, `store_embedding`, `get_rules`, `get_session_history`, `get_related`
- [Project Tools](projects) — `get_project_summary`, `update_project_summary`
- [Group Tools](groups) — `create_group`, `add_to_group`, `remove_from_group`, `get_group`
- [Maintenance Tools](maintenance) — `pin_item`, `archive_item`
