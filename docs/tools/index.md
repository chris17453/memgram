# Tools Reference

Memgram provides 26 MCP tools organized into five categories.

## Overview

| # | Tool | Category | Branch | Description |
|---|------|----------|--------|-------------|
| 1 | [`start_session`](sessions.md#start_session) | Session | yes | Begin a session, get resume context |
| 2 | [`end_session`](sessions.md#end_session) | Session | — | Close with structured summary |
| 3 | [`save_snapshot`](sessions.md#save_snapshot) | Session | — | Compaction checkpoint |
| 4 | [`get_resume_context`](sessions.md#get_resume_context) | Session | yes | Everything needed to resume |
| 5 | [`add_thought`](knowledge.md#add_thought) | Knowledge | yes | Store a thought/decision/observation |
| 6 | [`update_thought`](knowledge.md#update_thought) | Knowledge | yes | Modify an existing thought |
| 7 | [`add_rule`](knowledge.md#add_rule) | Knowledge | yes | Store a learned do/don't pattern |
| 8 | [`reinforce_rule`](knowledge.md#reinforce_rule) | Knowledge | — | Bump rule confidence |
| 9 | [`add_error_pattern`](knowledge.md#add_error_pattern) | Knowledge | yes | Log failure with cause and fix |
| 10 | [`link_items`](knowledge.md#link_items) | Knowledge | — | Connect items in the graph |
| 11 | [`search`](search.md#search) | Search | yes | FTS5 full-text search |
| 12 | [`search_by_embedding`](search.md#search_by_embedding) | Search | yes | Vector similarity search (RAG) |
| 13 | [`store_embedding`](search.md#store_embedding) | Search | — | Store a vector embedding |
| 14 | [`get_rules`](search.md#get_rules) | Search | yes | Get active rules for context |
| 15 | [`get_session_history`](search.md#get_session_history) | Search | yes | List past sessions |
| 16 | [`get_related`](search.md#get_related) | Search | — | Items linked via graph |
| 17 | [`get_project_summary`](projects.md#get_project_summary) | Projects | — | Get living project overview |
| 18 | [`update_project_summary`](projects.md#update_project_summary) | Projects | — | Update project overview |
| 19 | [`merge_projects`](projects.md#merge_projects) | Projects | — | Merge one project into another (typo cleanup) |
| 20 | [`create_group`](groups.md#create_group) | Groups | yes | Create a named cluster |
| 21 | [`add_to_group`](groups.md#add_to_group) | Groups | — | Add item to group |
| 22 | [`remove_from_group`](groups.md#remove_from_group) | Groups | — | Remove item from group |
| 23 | [`get_group`](groups.md#get_group) | Groups | yes | Get group with members |
| 24 | [`pin_item`](maintenance.md#pin_item) | Maintenance | — | Pin/unpin for resume context |
| 25 | [`archive_item`](maintenance.md#archive_item) | Maintenance | — | Archive (exclude from search) |
| 26 | [`get_health`](maintenance.md#get_health) | Maintenance | — | Database health/diagnostics |

**Branch column**: "yes" means the tool accepts a `branch` parameter for scoped operations.

## Detailed Pages

- [Session Tools](sessions.md) — `start_session`, `end_session`, `save_snapshot`, `get_resume_context`
- [Knowledge Tools](knowledge.md) — `add_thought`, `update_thought`, `add_rule`, `reinforce_rule`, `add_error_pattern`, `link_items`
- [Search Tools](search.md) — `search`, `search_by_embedding`, `store_embedding`, `get_rules`, `get_session_history`, `get_related`
- [Project Tools](projects.md) — `get_project_summary`, `update_project_summary`, `merge_projects`
- [Group Tools](groups.md) — `create_group`, `add_to_group`, `remove_from_group`, `get_group`
- [Maintenance & Health](maintenance.md) — `pin_item`, `archive_item`, `get_health`
