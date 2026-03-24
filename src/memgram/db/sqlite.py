"""SQLite backend for memgram, with FTS5 and sqlite-vec vector search."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

from .base import DatabaseBackend

DEFAULT_DB_PATH = Path.home() / ".memgram" / "memgram.db"

# Default embedding dimensions (e.g. OpenAI text-embedding-3-small = 1536,
# all-MiniLM-L6-v2 = 384). Configurable at init.
DEFAULT_EMBEDDING_DIM = 384

# ── Schema SQL ──────────────────────────────────────────────────────────────

CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    model TEXT NOT NULL,
    project TEXT,
    branch TEXT,
    goal TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    summary TEXT,
    compaction_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS thoughts (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    type TEXT NOT NULL DEFAULT 'note',
    summary TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    project TEXT,
    branch TEXT,
    agent_type TEXT,
    agent_model TEXT,
    keywords TEXT NOT NULL DEFAULT '[]',
    associated_files TEXT NOT NULL DEFAULT '[]',
    pinned INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    type TEXT NOT NULL DEFAULT 'do',
    severity TEXT NOT NULL DEFAULT 'preference',
    summary TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    condition TEXT,
    project TEXT,
    branch TEXT,
    agent_type TEXT,
    agent_model TEXT,
    keywords TEXT NOT NULL DEFAULT '[]',
    associated_files TEXT NOT NULL DEFAULT '[]',
    pinned INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0,
    reinforcement_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compaction_snapshots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    sequence_num INTEGER NOT NULL DEFAULT 1,
    current_goal TEXT,
    progress_summary TEXT,
    open_questions TEXT NOT NULL DEFAULT '[]',
    blockers TEXT NOT NULL DEFAULT '[]',
    next_steps TEXT NOT NULL DEFAULT '[]',
    active_files TEXT NOT NULL DEFAULT '[]',
    key_decisions TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thought_links (
    id TEXT PRIMARY KEY,
    from_id TEXT NOT NULL,
    from_type TEXT NOT NULL,
    to_id TEXT NOT NULL,
    to_type TEXT NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'related',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS error_patterns (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    error_description TEXT NOT NULL,
    cause TEXT,
    fix TEXT,
    prevention_rule_id TEXT REFERENCES rules(id),
    project TEXT,
    branch TEXT,
    agent_type TEXT,
    agent_model TEXT,
    keywords TEXT NOT NULL DEFAULT '[]',
    associated_files TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_summaries (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL DEFAULT '',
    tech_stack TEXT NOT NULL DEFAULT '[]',
    key_patterns TEXT NOT NULL DEFAULT '[]',
    active_goals TEXT NOT NULL DEFAULT '[]',
    total_sessions INTEGER NOT NULL DEFAULT 0,
    total_thoughts INTEGER NOT NULL DEFAULT 0,
    total_rules INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_summaries (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id),
    project TEXT,
    branch TEXT,
    goal TEXT,
    outcome TEXT,
    decisions_made TEXT NOT NULL DEFAULT '[]',
    rules_learned TEXT NOT NULL DEFAULT '[]',
    errors_encountered TEXT NOT NULL DEFAULT '[]',
    files_modified TEXT NOT NULL DEFAULT '[]',
    unresolved_items TEXT NOT NULL DEFAULT '[]',
    next_session_hints TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thought_groups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    project TEXT,
    branch TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS group_members (
    group_id TEXT NOT NULL REFERENCES thought_groups(id),
    item_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (group_id, item_id)
);

CREATE TABLE IF NOT EXISTS embedding_meta (
    item_id TEXT PRIMARY KEY,
    item_type TEXT NOT NULL,
    text_content TEXT NOT NULL,
    model_name TEXT NOT NULL,
    project TEXT,
    branch TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS specs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    priority TEXT NOT NULL DEFAULT 'medium',
    acceptance_criteria TEXT NOT NULL DEFAULT '[]',
    project TEXT,
    branch TEXT,
    session_id TEXT REFERENCES sessions(id),
    author_id TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS features (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed',
    priority TEXT NOT NULL DEFAULT 'medium',
    spec_id TEXT REFERENCES specs(id),
    project TEXT,
    branch TEXT,
    session_id TEXT REFERENCES sessions(id),
    lead_id TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS components (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'module',
    project TEXT,
    branch TEXT,
    owner_id TEXT,
    tech_stack TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'individual',
    role TEXT NOT NULL DEFAULT '',
    email TEXT,
    github TEXT,
    skills TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    project TEXT,
    lead_id TEXT REFERENCES people(id),
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id TEXT NOT NULL REFERENCES teams(id),
    person_id TEXT NOT NULL REFERENCES people(id),
    role TEXT NOT NULL DEFAULT 'member',
    joined_at TEXT NOT NULL,
    PRIMARY KEY (team_id, person_id)
);

CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT 'project',
    status TEXT NOT NULL DEFAULT 'draft',
    priority TEXT NOT NULL DEFAULT 'medium',
    session_id TEXT REFERENCES sessions(id),
    project TEXT,
    branch TEXT,
    due_date TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_tasks (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES plans(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    position INTEGER NOT NULL DEFAULT 0,
    assignee TEXT,
    depends_on TEXT REFERENCES plan_tasks(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS instructions (
    id TEXT PRIMARY KEY,
    section TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    priority TEXT NOT NULL DEFAULT 'medium',
    scope TEXT NOT NULL DEFAULT 'global',
    project TEXT,
    branch TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    ticket_number TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    type TEXT NOT NULL DEFAULT 'task',
    assignee_id TEXT,
    reporter_id TEXT,
    project TEXT,
    branch TEXT,
    session_id TEXT REFERENCES sessions(id),
    parent_id TEXT REFERENCES tickets(id),
    tags TEXT NOT NULL DEFAULT '[]',
    due_date TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    url TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'link',
    mime_type TEXT,
    description TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS endpoints (
    id TEXT PRIMARY KEY,
    method TEXT NOT NULL DEFAULT 'GET',
    path TEXT NOT NULL,
    base_url TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    auth_type TEXT NOT NULL DEFAULT 'none',
    rate_limit TEXT,
    request_schema TEXT NOT NULL DEFAULT '{}',
    response_schema TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    project TEXT,
    branch TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credentials (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'api_key',
    provider TEXT NOT NULL DEFAULT '',
    vault_path TEXT,
    env_var TEXT,
    description TEXT NOT NULL DEFAULT '',
    project TEXT,
    last_rotated TEXT,
    expires_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS environments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'development',
    url TEXT,
    description TEXT NOT NULL DEFAULT '',
    project TEXT,
    config TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deployments (
    id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    environment_id TEXT REFERENCES environments(id),
    status TEXT NOT NULL DEFAULT 'pending',
    strategy TEXT NOT NULL DEFAULT 'rolling',
    description TEXT NOT NULL DEFAULT '',
    project TEXT,
    branch TEXT,
    session_id TEXT REFERENCES sessions(id),
    deployed_by TEXT,
    rollback_to TEXT REFERENCES deployments(id),
    deployed_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS builds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    pipeline TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    trigger_type TEXT NOT NULL DEFAULT 'push',
    commit_sha TEXT,
    branch TEXT,
    artifact_url TEXT,
    duration_seconds INTEGER,
    project TEXT,
    session_id TEXT REFERENCES sessions(id),
    started_at TEXT,
    finished_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'p3',
    status TEXT NOT NULL DEFAULT 'investigating',
    description TEXT NOT NULL DEFAULT '',
    root_cause TEXT,
    resolution TEXT,
    timeline TEXT NOT NULL DEFAULT '[]',
    project TEXT,
    lead_id TEXT,
    started_at TEXT,
    resolved_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dependencies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'library',
    source TEXT,
    license TEXT,
    description TEXT NOT NULL DEFAULT '',
    project TEXT,
    pinned_version TEXT,
    latest_version TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runbooks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    steps TEXT NOT NULL DEFAULT '[]',
    trigger_conditions TEXT,
    project TEXT,
    last_executed TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    context TEXT NOT NULL DEFAULT '',
    options TEXT NOT NULL DEFAULT '[]',
    outcome TEXT,
    consequences TEXT,
    project TEXT,
    branch TEXT,
    session_id TEXT REFERENCES sessions(id),
    author_id TEXT,
    superseded_by TEXT REFERENCES decisions(id),
    decided_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    parent_id TEXT REFERENCES comments(id),
    project TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagrams (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    diagram_type TEXT NOT NULL DEFAULT 'mermaid',
    definition TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    data_source TEXT,
    project TEXT,
    branch TEXT,
    session_id TEXT REFERENCES sessions(id),
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    action TEXT NOT NULL,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    actor TEXT,
    project TEXT,
    created_at TEXT NOT NULL
);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS thoughts_fts USING fts5(
    id UNINDEXED, summary, content, keywords,
    content='thoughts', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
    id UNINDEXED, summary, content, keywords,
    content='rules', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS error_patterns_fts USING fts5(
    id UNINDEXED, error_description, cause, fix, keywords,
    content='error_patterns', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS session_summaries_fts USING fts5(
    id UNINDEXED, goal, outcome, next_session_hints,
    content='session_summaries', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS plans_fts USING fts5(
    id UNINDEXED, title, description, tags,
    content='plans', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS specs_fts USING fts5(
    id UNINDEXED, title, description, tags,
    content='specs', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS features_fts USING fts5(
    id UNINDEXED, name, description, tags,
    content='features', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS components_fts USING fts5(
    id UNINDEXED, name, description, tags,
    content='components', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS tickets_fts USING fts5(
    id UNINDEXED, ticket_number, title, description, tags,
    content='tickets', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS instructions_fts USING fts5(
    id UNINDEXED, section, title, content, tags,
    content='instructions', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS endpoints_fts USING fts5(
    id UNINDEXED, method, path, description, tags,
    content='endpoints', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS credentials_fts USING fts5(
    id UNINDEXED, name, provider, description, tags,
    content='credentials', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS environments_fts USING fts5(
    id UNINDEXED, name, description, tags,
    content='environments', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS deployments_fts USING fts5(
    id UNINDEXED, version, description, tags,
    content='deployments', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS builds_fts USING fts5(
    id UNINDEXED, name, pipeline, tags,
    content='builds', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS incidents_fts USING fts5(
    id UNINDEXED, title, description, root_cause, resolution, tags,
    content='incidents', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS dependencies_fts USING fts5(
    id UNINDEXED, name, description, tags,
    content='dependencies', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS runbooks_fts USING fts5(
    id UNINDEXED, title, description, trigger_conditions, tags,
    content='runbooks', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    id UNINDEXED, title, context, outcome, consequences, tags,
    content='decisions', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS diagrams_fts USING fts5(
    id UNINDEXED, title, description, definition, tags,
    content='diagrams', content_rowid='rowid'
);
CREATE VIRTUAL TABLE IF NOT EXISTS comments_fts USING fts5(
    id UNINDEXED, author, content, tags,
    content='comments', content_rowid='rowid'
);
"""

FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS thoughts_ai AFTER INSERT ON thoughts BEGIN
    INSERT INTO thoughts_fts(rowid, id, summary, content, keywords)
    VALUES (new.rowid, new.id, new.summary, new.content, new.keywords);
END;
CREATE TRIGGER IF NOT EXISTS thoughts_ad AFTER DELETE ON thoughts BEGIN
    INSERT INTO thoughts_fts(thoughts_fts, rowid, id, summary, content, keywords)
    VALUES ('delete', old.rowid, old.id, old.summary, old.content, old.keywords);
END;
CREATE TRIGGER IF NOT EXISTS thoughts_au AFTER UPDATE ON thoughts BEGIN
    INSERT INTO thoughts_fts(thoughts_fts, rowid, id, summary, content, keywords)
    VALUES ('delete', old.rowid, old.id, old.summary, old.content, old.keywords);
    INSERT INTO thoughts_fts(rowid, id, summary, content, keywords)
    VALUES (new.rowid, new.id, new.summary, new.content, new.keywords);
END;

CREATE TRIGGER IF NOT EXISTS rules_ai AFTER INSERT ON rules BEGIN
    INSERT INTO rules_fts(rowid, id, summary, content, keywords)
    VALUES (new.rowid, new.id, new.summary, new.content, new.keywords);
END;
CREATE TRIGGER IF NOT EXISTS rules_ad AFTER DELETE ON rules BEGIN
    INSERT INTO rules_fts(rules_fts, rowid, id, summary, content, keywords)
    VALUES ('delete', old.rowid, old.id, old.summary, old.content, old.keywords);
END;
CREATE TRIGGER IF NOT EXISTS rules_au AFTER UPDATE ON rules BEGIN
    INSERT INTO rules_fts(rules_fts, rowid, id, summary, content, keywords)
    VALUES ('delete', old.rowid, old.id, old.summary, old.content, old.keywords);
    INSERT INTO rules_fts(rowid, id, summary, content, keywords)
    VALUES (new.rowid, new.id, new.summary, new.content, new.keywords);
END;

CREATE TRIGGER IF NOT EXISTS error_patterns_ai AFTER INSERT ON error_patterns BEGIN
    INSERT INTO error_patterns_fts(rowid, id, error_description, cause, fix, keywords)
    VALUES (new.rowid, new.id, new.error_description, new.cause, new.fix, new.keywords);
END;
CREATE TRIGGER IF NOT EXISTS error_patterns_ad AFTER DELETE ON error_patterns BEGIN
    INSERT INTO error_patterns_fts(error_patterns_fts, rowid, id, error_description, cause, fix, keywords)
    VALUES ('delete', old.rowid, old.id, old.error_description, old.cause, old.fix, old.keywords);
END;
CREATE TRIGGER IF NOT EXISTS error_patterns_au AFTER UPDATE ON error_patterns BEGIN
    INSERT INTO error_patterns_fts(error_patterns_fts, rowid, id, error_description, cause, fix, keywords)
    VALUES ('delete', old.rowid, old.id, old.error_description, old.cause, old.fix, old.keywords);
    INSERT INTO error_patterns_fts(rowid, id, error_description, cause, fix, keywords)
    VALUES (new.rowid, new.id, new.error_description, new.cause, new.fix, new.keywords);
END;

CREATE TRIGGER IF NOT EXISTS session_summaries_ai AFTER INSERT ON session_summaries BEGIN
    INSERT INTO session_summaries_fts(rowid, id, goal, outcome, next_session_hints)
    VALUES (new.rowid, new.id, new.goal, new.outcome, new.next_session_hints);
END;
CREATE TRIGGER IF NOT EXISTS session_summaries_ad AFTER DELETE ON session_summaries BEGIN
    INSERT INTO session_summaries_fts(session_summaries_fts, rowid, id, goal, outcome, next_session_hints)
    VALUES ('delete', old.rowid, old.id, old.goal, old.outcome, old.next_session_hints);
END;
CREATE TRIGGER IF NOT EXISTS session_summaries_au AFTER UPDATE ON session_summaries BEGIN
    INSERT INTO session_summaries_fts(session_summaries_fts, rowid, id, goal, outcome, next_session_hints)
    VALUES ('delete', old.rowid, old.id, old.goal, old.outcome, old.next_session_hints);
    INSERT INTO session_summaries_fts(rowid, id, goal, outcome, next_session_hints)
    VALUES (new.rowid, new.id, new.goal, new.outcome, new.next_session_hints);
END;

CREATE TRIGGER IF NOT EXISTS plans_ai AFTER INSERT ON plans BEGIN
    INSERT INTO plans_fts(rowid, id, title, description, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS plans_ad AFTER DELETE ON plans BEGIN
    INSERT INTO plans_fts(plans_fts, rowid, id, title, description, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS plans_au AFTER UPDATE ON plans BEGIN
    INSERT INTO plans_fts(plans_fts, rowid, id, title, description, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.tags);
    INSERT INTO plans_fts(rowid, id, title, description, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS specs_ai AFTER INSERT ON specs BEGIN
    INSERT INTO specs_fts(rowid, id, title, description, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS specs_ad AFTER DELETE ON specs BEGIN
    INSERT INTO specs_fts(specs_fts, rowid, id, title, description, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS specs_au AFTER UPDATE ON specs BEGIN
    INSERT INTO specs_fts(specs_fts, rowid, id, title, description, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.tags);
    INSERT INTO specs_fts(rowid, id, title, description, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS features_ai AFTER INSERT ON features BEGIN
    INSERT INTO features_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS features_ad AFTER DELETE ON features BEGIN
    INSERT INTO features_fts(features_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS features_au AFTER UPDATE ON features BEGIN
    INSERT INTO features_fts(features_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
    INSERT INTO features_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS components_ai AFTER INSERT ON components BEGIN
    INSERT INTO components_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS components_ad AFTER DELETE ON components BEGIN
    INSERT INTO components_fts(components_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS components_au AFTER UPDATE ON components BEGIN
    INSERT INTO components_fts(components_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
    INSERT INTO components_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS tickets_ai AFTER INSERT ON tickets BEGIN
    INSERT INTO tickets_fts(rowid, id, ticket_number, title, description, tags)
    VALUES (new.rowid, new.id, new.ticket_number, new.title, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS tickets_ad AFTER DELETE ON tickets BEGIN
    INSERT INTO tickets_fts(tickets_fts, rowid, id, ticket_number, title, description, tags)
    VALUES ('delete', old.rowid, old.id, old.ticket_number, old.title, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS tickets_au AFTER UPDATE ON tickets BEGIN
    INSERT INTO tickets_fts(tickets_fts, rowid, id, ticket_number, title, description, tags)
    VALUES ('delete', old.rowid, old.id, old.ticket_number, old.title, old.description, old.tags);
    INSERT INTO tickets_fts(rowid, id, ticket_number, title, description, tags)
    VALUES (new.rowid, new.id, new.ticket_number, new.title, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS instructions_ai AFTER INSERT ON instructions BEGIN
    INSERT INTO instructions_fts(rowid, id, section, title, content, tags)
    VALUES (new.rowid, new.id, new.section, new.title, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS instructions_ad AFTER DELETE ON instructions BEGIN
    INSERT INTO instructions_fts(instructions_fts, rowid, id, section, title, content, tags)
    VALUES ('delete', old.rowid, old.id, old.section, old.title, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS instructions_au AFTER UPDATE ON instructions BEGIN
    INSERT INTO instructions_fts(instructions_fts, rowid, id, section, title, content, tags)
    VALUES ('delete', old.rowid, old.id, old.section, old.title, old.content, old.tags);
    INSERT INTO instructions_fts(rowid, id, section, title, content, tags)
    VALUES (new.rowid, new.id, new.section, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS endpoints_ai AFTER INSERT ON endpoints BEGIN
    INSERT INTO endpoints_fts(rowid, id, method, path, description, tags)
    VALUES (new.rowid, new.id, new.method, new.path, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS endpoints_ad AFTER DELETE ON endpoints BEGIN
    INSERT INTO endpoints_fts(endpoints_fts, rowid, id, method, path, description, tags)
    VALUES ('delete', old.rowid, old.id, old.method, old.path, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS endpoints_au AFTER UPDATE ON endpoints BEGIN
    INSERT INTO endpoints_fts(endpoints_fts, rowid, id, method, path, description, tags)
    VALUES ('delete', old.rowid, old.id, old.method, old.path, old.description, old.tags);
    INSERT INTO endpoints_fts(rowid, id, method, path, description, tags)
    VALUES (new.rowid, new.id, new.method, new.path, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS credentials_ai AFTER INSERT ON credentials BEGIN
    INSERT INTO credentials_fts(rowid, id, name, provider, description, tags)
    VALUES (new.rowid, new.id, new.name, new.provider, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS credentials_ad AFTER DELETE ON credentials BEGIN
    INSERT INTO credentials_fts(credentials_fts, rowid, id, name, provider, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.provider, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS credentials_au AFTER UPDATE ON credentials BEGIN
    INSERT INTO credentials_fts(credentials_fts, rowid, id, name, provider, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.provider, old.description, old.tags);
    INSERT INTO credentials_fts(rowid, id, name, provider, description, tags)
    VALUES (new.rowid, new.id, new.name, new.provider, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS environments_ai AFTER INSERT ON environments BEGIN
    INSERT INTO environments_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS environments_ad AFTER DELETE ON environments BEGIN
    INSERT INTO environments_fts(environments_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS environments_au AFTER UPDATE ON environments BEGIN
    INSERT INTO environments_fts(environments_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
    INSERT INTO environments_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS deployments_ai AFTER INSERT ON deployments BEGIN
    INSERT INTO deployments_fts(rowid, id, version, description, tags)
    VALUES (new.rowid, new.id, new.version, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS deployments_ad AFTER DELETE ON deployments BEGIN
    INSERT INTO deployments_fts(deployments_fts, rowid, id, version, description, tags)
    VALUES ('delete', old.rowid, old.id, old.version, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS deployments_au AFTER UPDATE ON deployments BEGIN
    INSERT INTO deployments_fts(deployments_fts, rowid, id, version, description, tags)
    VALUES ('delete', old.rowid, old.id, old.version, old.description, old.tags);
    INSERT INTO deployments_fts(rowid, id, version, description, tags)
    VALUES (new.rowid, new.id, new.version, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS builds_ai AFTER INSERT ON builds BEGIN
    INSERT INTO builds_fts(rowid, id, name, pipeline, tags)
    VALUES (new.rowid, new.id, new.name, new.pipeline, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS builds_ad AFTER DELETE ON builds BEGIN
    INSERT INTO builds_fts(builds_fts, rowid, id, name, pipeline, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.pipeline, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS builds_au AFTER UPDATE ON builds BEGIN
    INSERT INTO builds_fts(builds_fts, rowid, id, name, pipeline, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.pipeline, old.tags);
    INSERT INTO builds_fts(rowid, id, name, pipeline, tags)
    VALUES (new.rowid, new.id, new.name, new.pipeline, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS incidents_ai AFTER INSERT ON incidents BEGIN
    INSERT INTO incidents_fts(rowid, id, title, description, root_cause, resolution, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.root_cause, new.resolution, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS incidents_ad AFTER DELETE ON incidents BEGIN
    INSERT INTO incidents_fts(incidents_fts, rowid, id, title, description, root_cause, resolution, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.root_cause, old.resolution, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS incidents_au AFTER UPDATE ON incidents BEGIN
    INSERT INTO incidents_fts(incidents_fts, rowid, id, title, description, root_cause, resolution, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.root_cause, old.resolution, old.tags);
    INSERT INTO incidents_fts(rowid, id, title, description, root_cause, resolution, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.root_cause, new.resolution, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS dependencies_ai AFTER INSERT ON dependencies BEGIN
    INSERT INTO dependencies_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS dependencies_ad AFTER DELETE ON dependencies BEGIN
    INSERT INTO dependencies_fts(dependencies_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS dependencies_au AFTER UPDATE ON dependencies BEGIN
    INSERT INTO dependencies_fts(dependencies_fts, rowid, id, name, description, tags)
    VALUES ('delete', old.rowid, old.id, old.name, old.description, old.tags);
    INSERT INTO dependencies_fts(rowid, id, name, description, tags)
    VALUES (new.rowid, new.id, new.name, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS runbooks_ai AFTER INSERT ON runbooks BEGIN
    INSERT INTO runbooks_fts(rowid, id, title, description, trigger_conditions, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.trigger_conditions, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS runbooks_ad AFTER DELETE ON runbooks BEGIN
    INSERT INTO runbooks_fts(runbooks_fts, rowid, id, title, description, trigger_conditions, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.trigger_conditions, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS runbooks_au AFTER UPDATE ON runbooks BEGIN
    INSERT INTO runbooks_fts(runbooks_fts, rowid, id, title, description, trigger_conditions, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.trigger_conditions, old.tags);
    INSERT INTO runbooks_fts(rowid, id, title, description, trigger_conditions, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.trigger_conditions, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO decisions_fts(rowid, id, title, context, outcome, consequences, tags)
    VALUES (new.rowid, new.id, new.title, new.context, new.outcome, new.consequences, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, id, title, context, outcome, consequences, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.context, old.outcome, old.consequences, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, id, title, context, outcome, consequences, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.context, old.outcome, old.consequences, old.tags);
    INSERT INTO decisions_fts(rowid, id, title, context, outcome, consequences, tags)
    VALUES (new.rowid, new.id, new.title, new.context, new.outcome, new.consequences, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS diagrams_ai AFTER INSERT ON diagrams BEGIN
    INSERT INTO diagrams_fts(rowid, id, title, description, definition, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.definition, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS diagrams_ad AFTER DELETE ON diagrams BEGIN
    INSERT INTO diagrams_fts(diagrams_fts, rowid, id, title, description, definition, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.definition, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS diagrams_au AFTER UPDATE ON diagrams BEGIN
    INSERT INTO diagrams_fts(diagrams_fts, rowid, id, title, description, definition, tags)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.definition, old.tags);
    INSERT INTO diagrams_fts(rowid, id, title, description, definition, tags)
    VALUES (new.rowid, new.id, new.title, new.description, new.definition, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS comments_ai AFTER INSERT ON comments BEGIN
    INSERT INTO comments_fts(rowid, id, author, content, tags)
    VALUES (new.rowid, new.id, new.author, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS comments_ad AFTER DELETE ON comments BEGIN
    INSERT INTO comments_fts(comments_fts, rowid, id, author, content, tags)
    VALUES ('delete', old.rowid, old.id, old.author, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS comments_au AFTER UPDATE ON comments BEGIN
    INSERT INTO comments_fts(comments_fts, rowid, id, author, content, tags)
    VALUES ('delete', old.rowid, old.id, old.author, old.content, old.tags);
    INSERT INTO comments_fts(rowid, id, author, content, tags)
    VALUES (new.rowid, new.id, new.author, new.content, new.tags);
END;
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_thoughts_project ON thoughts(project);
CREATE INDEX IF NOT EXISTS idx_thoughts_pinned ON thoughts(pinned) WHERE pinned = 1;
CREATE INDEX IF NOT EXISTS idx_thoughts_session ON thoughts(session_id);
CREATE INDEX IF NOT EXISTS idx_rules_project ON rules(project);
CREATE INDEX IF NOT EXISTS idx_rules_severity ON rules(severity);
CREATE INDEX IF NOT EXISTS idx_rules_pinned ON rules(pinned) WHERE pinned = 1;
CREATE INDEX IF NOT EXISTS idx_rules_session ON rules(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_compaction_session ON compaction_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_error_patterns_project ON error_patterns(project);
CREATE INDEX IF NOT EXISTS idx_thought_links_from ON thought_links(from_id);
CREATE INDEX IF NOT EXISTS idx_thought_links_to ON thought_links(to_id);
CREATE INDEX IF NOT EXISTS idx_group_members_item ON group_members(item_id);
CREATE INDEX IF NOT EXISTS idx_embedding_meta_type ON embedding_meta(item_type);
CREATE INDEX IF NOT EXISTS idx_sessions_branch ON sessions(branch);
CREATE INDEX IF NOT EXISTS idx_thoughts_branch ON thoughts(branch);
CREATE INDEX IF NOT EXISTS idx_rules_branch ON rules(branch);
CREATE INDEX IF NOT EXISTS idx_error_patterns_branch ON error_patterns(branch);
CREATE INDEX IF NOT EXISTS idx_session_summaries_branch ON session_summaries(branch);
CREATE INDEX IF NOT EXISTS idx_thought_groups_branch ON thought_groups(branch);
CREATE INDEX IF NOT EXISTS idx_embedding_meta_branch ON embedding_meta(branch);
CREATE INDEX IF NOT EXISTS idx_thoughts_project_branch ON thoughts(project, branch);
CREATE INDEX IF NOT EXISTS idx_rules_project_branch ON rules(project, branch);
CREATE INDEX IF NOT EXISTS idx_sessions_project_branch ON sessions(project, branch);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_type, model);
CREATE INDEX IF NOT EXISTS idx_thoughts_agent ON thoughts(agent_type, agent_model);
CREATE INDEX IF NOT EXISTS idx_rules_agent ON rules(agent_type, agent_model);
CREATE INDEX IF NOT EXISTS idx_error_patterns_agent ON error_patterns(agent_type, agent_model);
CREATE INDEX IF NOT EXISTS idx_plans_project ON plans(project);
CREATE INDEX IF NOT EXISTS idx_plans_branch ON plans(branch);
CREATE INDEX IF NOT EXISTS idx_plans_project_branch ON plans(project, branch);
CREATE INDEX IF NOT EXISTS idx_plans_session ON plans(session_id);
CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
CREATE INDEX IF NOT EXISTS idx_plan_tasks_plan ON plan_tasks(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_tasks_status ON plan_tasks(status);
CREATE INDEX IF NOT EXISTS idx_plan_tasks_depends ON plan_tasks(depends_on);
CREATE INDEX IF NOT EXISTS idx_specs_project ON specs(project);
CREATE INDEX IF NOT EXISTS idx_specs_branch ON specs(branch);
CREATE INDEX IF NOT EXISTS idx_specs_project_branch ON specs(project, branch);
CREATE INDEX IF NOT EXISTS idx_specs_status ON specs(status);
CREATE INDEX IF NOT EXISTS idx_specs_author ON specs(author_id);
CREATE INDEX IF NOT EXISTS idx_features_project ON features(project);
CREATE INDEX IF NOT EXISTS idx_features_branch ON features(branch);
CREATE INDEX IF NOT EXISTS idx_features_project_branch ON features(project, branch);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_features_spec ON features(spec_id);
CREATE INDEX IF NOT EXISTS idx_features_lead ON features(lead_id);
CREATE INDEX IF NOT EXISTS idx_components_project ON components(project);
CREATE INDEX IF NOT EXISTS idx_components_branch ON components(branch);
CREATE INDEX IF NOT EXISTS idx_components_project_branch ON components(project, branch);
CREATE INDEX IF NOT EXISTS idx_components_owner ON components(owner_id);
CREATE INDEX IF NOT EXISTS idx_components_type ON components(type);
CREATE INDEX IF NOT EXISTS idx_people_type ON people(type);
CREATE INDEX IF NOT EXISTS idx_teams_project ON teams(project);
CREATE INDEX IF NOT EXISTS idx_teams_lead ON teams(lead_id);
CREATE INDEX IF NOT EXISTS idx_team_members_person ON team_members(person_id);
CREATE INDEX IF NOT EXISTS idx_tickets_project ON tickets(project);
CREATE INDEX IF NOT EXISTS idx_tickets_branch ON tickets(branch);
CREATE INDEX IF NOT EXISTS idx_tickets_project_branch ON tickets(project, branch);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_assignee ON tickets(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tickets_parent ON tickets(parent_id);
CREATE INDEX IF NOT EXISTS idx_tickets_number ON tickets(ticket_number);
CREATE INDEX IF NOT EXISTS idx_instructions_project ON instructions(project);
CREATE INDEX IF NOT EXISTS idx_instructions_scope ON instructions(scope);
CREATE INDEX IF NOT EXISTS idx_instructions_active ON instructions(active) WHERE active = 1;
CREATE INDEX IF NOT EXISTS idx_instructions_project_branch ON instructions(project, branch);
CREATE INDEX IF NOT EXISTS idx_attachments_entity ON attachments(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_attachments_type ON attachments(type);
CREATE INDEX IF NOT EXISTS idx_endpoints_project ON endpoints(project);
CREATE INDEX IF NOT EXISTS idx_endpoints_branch ON endpoints(branch);
CREATE INDEX IF NOT EXISTS idx_endpoints_project_branch ON endpoints(project, branch);
CREATE INDEX IF NOT EXISTS idx_endpoints_status ON endpoints(status);
CREATE INDEX IF NOT EXISTS idx_endpoints_method ON endpoints(method);
CREATE INDEX IF NOT EXISTS idx_credentials_project ON credentials(project);
CREATE INDEX IF NOT EXISTS idx_credentials_type ON credentials(type);
CREATE INDEX IF NOT EXISTS idx_credentials_provider ON credentials(provider);
CREATE INDEX IF NOT EXISTS idx_credentials_expires ON credentials(expires_at);
CREATE INDEX IF NOT EXISTS idx_environments_project ON environments(project);
CREATE INDEX IF NOT EXISTS idx_environments_type ON environments(type);
CREATE INDEX IF NOT EXISTS idx_deployments_project ON deployments(project);
CREATE INDEX IF NOT EXISTS idx_deployments_branch ON deployments(branch);
CREATE INDEX IF NOT EXISTS idx_deployments_project_branch ON deployments(project, branch);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);
CREATE INDEX IF NOT EXISTS idx_deployments_environment ON deployments(environment_id);
CREATE INDEX IF NOT EXISTS idx_deployments_session ON deployments(session_id);
CREATE INDEX IF NOT EXISTS idx_builds_project ON builds(project);
CREATE INDEX IF NOT EXISTS idx_builds_branch ON builds(branch);
CREATE INDEX IF NOT EXISTS idx_builds_project_branch ON builds(project, branch);
CREATE INDEX IF NOT EXISTS idx_builds_status ON builds(status);
CREATE INDEX IF NOT EXISTS idx_builds_session ON builds(session_id);
CREATE INDEX IF NOT EXISTS idx_builds_commit ON builds(commit_sha);
CREATE INDEX IF NOT EXISTS idx_incidents_project ON incidents(project);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_lead ON incidents(lead_id);
CREATE INDEX IF NOT EXISTS idx_dependencies_project ON dependencies(project);
CREATE INDEX IF NOT EXISTS idx_dependencies_type ON dependencies(type);
CREATE INDEX IF NOT EXISTS idx_dependencies_name ON dependencies(name);
CREATE INDEX IF NOT EXISTS idx_runbooks_project ON runbooks(project);
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project);
CREATE INDEX IF NOT EXISTS idx_decisions_branch ON decisions(branch);
CREATE INDEX IF NOT EXISTS idx_decisions_project_branch ON decisions(project, branch);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_author ON decisions(author_id);
CREATE INDEX IF NOT EXISTS idx_decisions_superseded ON decisions(superseded_by);
CREATE INDEX IF NOT EXISTS idx_diagrams_project ON diagrams(project);
CREATE INDEX IF NOT EXISTS idx_diagrams_branch ON diagrams(branch);
CREATE INDEX IF NOT EXISTS idx_diagrams_project_branch ON diagrams(project, branch);
CREATE INDEX IF NOT EXISTS idx_diagrams_type ON diagrams(diagram_type);
CREATE INDEX IF NOT EXISTS idx_diagrams_session ON diagrams(session_id);
CREATE INDEX IF NOT EXISTS idx_comments_project ON comments(project);
CREATE INDEX IF NOT EXISTS idx_comments_entity ON comments(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_comments_author ON comments(author);
CREATE INDEX IF NOT EXISTS idx_audit_log_project ON audit_log(project);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);
"""


class SQLiteBackend(DatabaseBackend):
    """SQLite implementation with FTS5 full-text search and sqlite-vec vector search."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
    ):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.embedding_dim = embedding_dim
        self.conn: sqlite3.Connection | None = None
        self._last_rowcount = 0
        self.vec_enabled = False

    # ── Lifecycle ───────────────────────────────────────────────────────

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        # Load sqlite-vec
        self.conn.enable_load_extension(True)
        try:
            import sqlite_vec
            sqlite_vec.load(self.conn)
            self.vec_enabled = True
        except Exception:
            self.vec_enabled = False
        finally:
            self.conn.enable_load_extension(False)

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_schema(self) -> None:
        assert self.conn is not None
        self.conn.executescript(CORE_SCHEMA)
        self._migrate_add_branch()  # must run before INDEXES (adds branch column)
        self._migrate_add_agent_attribution()  # adds agent_type/agent_model columns
        self._migrate_add_person_type()  # adds type column to people
        self._migrate_add_instruction_priority()  # adds priority column to instructions
        self.conn.executescript(FTS_SCHEMA)
        self.conn.executescript(FTS_TRIGGERS)
        self._rebuild_fts()  # ensure FTS indexes are synced with existing data
        self.conn.executescript(INDEXES)
        # sqlite-vec virtual table for vector search
        if self.vec_enabled:
            self.conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS embeddings_vec
                USING vec0(item_id TEXT PRIMARY KEY, embedding float[{self.embedding_dim}])
            """)
        self.conn.commit()

    def _migrate_add_branch(self) -> None:
        """Add branch column to existing tables (idempotent for existing DBs)."""
        assert self.conn is not None
        tables = [
            "sessions", "thoughts", "rules", "error_patterns",
            "session_summaries", "thought_groups", "embedding_meta",
        ]
        for table in tables:
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN branch TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
        self.conn.commit()

    def _migrate_add_agent_attribution(self) -> None:
        """Add agent_type and agent_model columns to content tables (idempotent).

        Also backfills existing rows from their linked session where possible.
        """
        assert self.conn is not None
        tables = ["thoughts", "rules", "error_patterns"]
        added_any = False
        for table in tables:
            for col in ("agent_type", "agent_model"):
                try:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                    added_any = True
                except sqlite3.OperationalError:
                    pass  # column already exists
        # Backfill from sessions for rows that have a session_id but no agent info
        if added_any:
            for table in tables:
                self.conn.execute(f"""
                    UPDATE {table} SET
                        agent_type = (SELECT s.agent_type FROM sessions s WHERE s.id = {table}.session_id),
                        agent_model = (SELECT s.model FROM sessions s WHERE s.id = {table}.session_id)
                    WHERE session_id IS NOT NULL AND agent_type IS NULL
                """)
        self.conn.commit()

    def _rebuild_fts(self) -> None:
        """Rebuild FTS indexes so they stay in sync with content tables.

        This is idempotent and fast on small/empty tables. On upgrade from an
        older schema, existing rows won't be in the FTS index until rebuild.
        """
        assert self.conn is not None
        fts_tables = [
            "thoughts_fts", "rules_fts", "error_patterns_fts",
            "session_summaries_fts", "plans_fts",
            "specs_fts", "features_fts", "components_fts",
            "tickets_fts", "instructions_fts",
            "endpoints_fts", "credentials_fts", "environments_fts",
            "deployments_fts", "builds_fts", "incidents_fts",
            "dependencies_fts", "runbooks_fts", "decisions_fts",
            "comments_fts",
        ]
        for fts in fts_tables:
            try:
                self.conn.execute(f"INSERT INTO {fts}({fts}) VALUES('rebuild')")
            except Exception:
                pass  # table may not exist yet on first run
        self.conn.commit()

    def _migrate_add_person_type(self) -> None:
        """Add type column to people table (idempotent)."""
        assert self.conn is not None
        try:
            self.conn.execute("ALTER TABLE people ADD COLUMN type TEXT NOT NULL DEFAULT 'individual'")
        except sqlite3.OperationalError:
            pass  # column already exists or table doesn't exist yet
        self.conn.commit()

    def _migrate_add_instruction_priority(self) -> None:
        """Add priority column to instructions table (idempotent)."""
        assert self.conn is not None
        try:
            self.conn.execute("ALTER TABLE instructions ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'")
        except sqlite3.OperationalError:
            pass  # column already exists or table doesn't exist yet
        self.conn.commit()

    # ── Primitives ──────────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple | list = ()) -> Any:
        assert self.conn is not None
        cur = self.conn.execute(sql, params)
        self._last_rowcount = cur.rowcount
        self.conn.commit()
        return cur

    def execute_script(self, sql: str) -> None:
        assert self.conn is not None
        self.conn.executescript(sql)
        self.conn.commit()

    def fetchone(self, sql: str, params: tuple | list = ()) -> dict | None:
        assert self.conn is not None
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple | list = ()) -> list[dict]:
        assert self.conn is not None
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def insert_returning(self, sql: str, params: tuple | list, table: str, id_val: str) -> dict:
        self.execute(sql, params)
        return self.fetchone(f"SELECT * FROM {table} WHERE id=?", (id_val,))

    def last_rowcount(self) -> int:
        return self._last_rowcount

    @property
    def ph(self) -> str:
        return "?"

    # ── FTS5 Search ─────────────────────────────────────────────────────

    def fts_search(
        self, table: str, query: str, project: Optional[str] = None,
        branch: Optional[str] = None,
        include_archived: bool = False, limit: int = 50,
    ) -> list[dict]:
        fts_table = f"{table}_fts"
        fts_query = self._build_fts_query(query)
        try:
            q = f"""
                SELECT m.*, fts.rank AS _fts_rank
                FROM {fts_table} fts
                JOIN {table} m ON fts.id = m.id
                WHERE {fts_table} MATCH ?
            """
            params: list[Any] = [fts_query]
            if project:
                q += " AND m.project=?"
                params.append(project)
            if branch:
                q += " AND m.branch=?"
                params.append(branch)
            if not include_archived and table in ("thoughts", "rules"):
                q += " AND m.archived=0"
            q += " ORDER BY fts.rank LIMIT ?"
            params.append(limit)
            rows = self.fetchall(q, params)
            # Normalize rank (FTS5 rank is negative, more negative = better match)
            for r in rows:
                r["_fts_rank"] = abs(r["_fts_rank"])
            return rows
        except sqlite3.OperationalError:
            return self._fallback_like_search(table, query, project, branch, include_archived, limit)

    def fts_search_errors(self, query: str, project: Optional[str] = None, branch: Optional[str] = None, limit: int = 50) -> list[dict]:
        fts_query = self._build_fts_query(query)
        try:
            q = """
                SELECT m.*, fts.rank AS _fts_rank
                FROM error_patterns_fts fts
                JOIN error_patterns m ON fts.id = m.id
                WHERE error_patterns_fts MATCH ?
            """
            params: list[Any] = [fts_query]
            if project:
                q += " AND m.project=?"
                params.append(project)
            if branch:
                q += " AND m.branch=?"
                params.append(branch)
            q += " ORDER BY fts.rank LIMIT ?"
            params.append(limit)
            rows = self.fetchall(q, params)
            for r in rows:
                r["_fts_rank"] = abs(r["_fts_rank"])
            return rows
        except sqlite3.OperationalError:
            return []

    def fts_search_sessions(self, query: str, project: Optional[str] = None, branch: Optional[str] = None, limit: int = 50) -> list[dict]:
        fts_query = self._build_fts_query(query)
        try:
            q = """
                SELECT m.*, fts.rank AS _fts_rank
                FROM session_summaries_fts fts
                JOIN session_summaries m ON fts.id = m.id
                WHERE session_summaries_fts MATCH ?
            """
            params: list[Any] = [fts_query]
            if project:
                q += " AND m.project=?"
                params.append(project)
            if branch:
                q += " AND m.branch=?"
                params.append(branch)
            q += " ORDER BY fts.rank LIMIT ?"
            params.append(limit)
            rows = self.fetchall(q, params)
            for r in rows:
                r["_fts_rank"] = abs(r["_fts_rank"])
            return rows
        except sqlite3.OperationalError:
            return []

    # ── Vector / sqlite-vec ─────────────────────────────────────────────

    def store_embedding(
        self, item_id: str, item_type: str, text_content: str,
        embedding: list[float], model_name: str,
    ) -> None:
        assert self.conn is not None
        if not self.vec_enabled:
            raise RuntimeError("sqlite-vec is not available; install sqlite-vec to enable embeddings.")
        from ..utils import now_iso
        import struct

        ts = now_iso()
        vec_blob = _float_list_to_blob(embedding)

        # Upsert metadata
        self.conn.execute(
            """INSERT OR REPLACE INTO embedding_meta
               (item_id, item_type, text_content, model_name, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (item_id, item_type, text_content, model_name, ts),
        )
        # Upsert vector — delete + insert since vec0 doesn't support ON CONFLICT
        self.conn.execute("DELETE FROM embeddings_vec WHERE item_id=?", (item_id,))
        self.conn.execute(
            "INSERT INTO embeddings_vec (item_id, embedding) VALUES (?, ?)",
            (item_id, vec_blob),
        )
        self.conn.commit()

    def vector_search(
        self, embedding: list[float], item_type: Optional[str] = None,
        project: Optional[str] = None, branch: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        assert self.conn is not None
        if not self.vec_enabled:
            return []

        vec_blob = _float_list_to_blob(embedding)

        # vec0 KNN query
        q = """
            SELECT v.item_id, v.distance AS _distance, em.item_type, em.text_content, em.project, em.branch
            FROM embeddings_vec v
            JOIN embedding_meta em ON v.item_id = em.item_id
            WHERE v.embedding MATCH ? AND k = ?
        """
        params: list[Any] = [vec_blob, limit * 3]  # over-fetch, then filter

        rows = [dict(r) for r in self.conn.execute(q, params).fetchall()]

        # Post-filter by type/project/branch (vec0 doesn't support JOINed WHERE in MATCH)
        results = []
        for r in rows:
            if item_type and r.get("item_type") != item_type:
                continue
            if project and r.get("project") != project:
                continue
            if branch and r.get("branch") != branch:
                continue
            results.append(r)
            if len(results) >= limit:
                break
        return results

    def delete_embedding(self, item_id: str) -> None:
        assert self.conn is not None
        if self.vec_enabled:
            self.conn.execute("DELETE FROM embeddings_vec WHERE item_id=?", (item_id,))
        self.conn.execute("DELETE FROM embedding_meta WHERE item_id=?", (item_id,))
        self.conn.commit()

    def has_embeddings(self) -> bool:
        assert self.conn is not None
        if not self.vec_enabled:
            return False
        row = self.conn.execute("SELECT COUNT(*) AS cnt FROM embedding_meta").fetchone()
        return row["cnt"] > 0 if row else False

    def diagnostics(self) -> dict:
        assert self.conn is not None
        info: dict[str, Any] = {
            "backend": "sqlite",
            "db_path": str(self.db_path),
            "connected": True,
            "journal_mode": None,
            "wal_enabled": False,
            "foreign_keys": None,
            "vec": {"enabled": self.vec_enabled},
            "counts": {},
            "fts": {},
            "warnings": [],
        }

        try:
            self.conn.execute("SELECT 1")
        except Exception as exc:  # pragma: no cover - connectivity failure path
            info["connected"] = False
            info["error"] = str(exc)
            info["status"] = "error"
            return info

        try:
            jm_row = self.conn.execute("PRAGMA journal_mode").fetchone()
            info["journal_mode"] = jm_row[0] if jm_row else None
            info["wal_enabled"] = str(info["journal_mode"]).lower() == "wal"
        except Exception as exc:
            info["warnings"].append(f"journal_mode check failed: {exc}")

        try:
            fk_row = self.conn.execute("PRAGMA foreign_keys").fetchone()
            info["foreign_keys"] = bool(fk_row[0]) if fk_row else False
        except Exception as exc:
            info["warnings"].append(f"foreign_keys check failed: {exc}")

        tables = [
            "sessions", "thoughts", "rules", "error_patterns",
            "session_summaries", "compaction_snapshots", "project_summaries",
            "thought_groups", "group_members", "embedding_meta",
            "plans", "plan_tasks",
            "specs", "features", "components", "people", "teams", "team_members",
            "tickets", "instructions", "attachments",
            "endpoints", "credentials", "environments", "deployments",
            "builds", "incidents", "dependencies", "runbooks",
            "decisions", "comments", "audit_log",
        ]
        counts: dict[str, Any] = {}
        for tbl in tables:
            try:
                row = self.conn.execute(f"SELECT COUNT(*) AS cnt FROM {tbl}").fetchone()
                counts[tbl] = row["cnt"] if row else 0
            except Exception as exc:
                counts[tbl] = None
                info["warnings"].append(f"{tbl} count failed: {exc}")
        info["counts"] = counts

        vec_info: dict[str, Any] = {"enabled": self.vec_enabled}
        try:
            row = self.conn.execute("SELECT COUNT(*) AS cnt FROM embedding_meta").fetchone()
            vec_info["meta_rows"] = row["cnt"] if row else 0
        except Exception as exc:
            vec_info["meta_error"] = str(exc)
        if self.vec_enabled:
            try:
                row = self.conn.execute("SELECT COUNT(*) AS cnt FROM embeddings_vec").fetchone()
                vec_info["vec_rows"] = row["cnt"] if row else 0
            except Exception as exc:
                vec_info["vec_error"] = str(exc)
                info["warnings"].append(f"embeddings_vec check failed: {exc}")
        info["vec"] = vec_info

        fts_tables = [
            "thoughts_fts", "rules_fts", "error_patterns_fts", "session_summaries_fts",
            "plans_fts", "specs_fts", "features_fts", "components_fts",
        ]
        fts_status: dict[str, str] = {}
        for tbl in fts_tables:
            try:
                self.conn.execute(f"SELECT COUNT(*) FROM {tbl} LIMIT 1")
                fts_status[tbl] = "ok"
            except Exception as exc:
                fts_status[tbl] = f"error: {exc}"
                info["warnings"].append(f"{tbl} unavailable: {exc}")
        info["fts"] = fts_status
        info["fts_ok"] = all(v == "ok" for v in fts_status.values()) if fts_status else True

        info["status"] = "ok" if info["connected"] and not info["warnings"] else "degraded"
        return info

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_fts_query(query: str) -> str:
        terms = query.strip().split()
        escaped = []
        for t in terms:
            t = t.replace('"', '""')
            escaped.append(f'"{t}"')
        return " OR ".join(escaped)

    def _fallback_like_search(
        self, table: str, query: str, project: Optional[str],
        branch: Optional[str], include_archived: bool, limit: int,
    ) -> list[dict]:
        terms = query.split()
        if not terms:
            return []
        conditions = []
        params: list[Any] = []
        col_map = {
            "thoughts": ("summary", "content", "keywords"),
            "rules": ("summary", "content", "keywords"),
            "error_patterns": ("error_description", "cause", "fix"),
        }
        cols = col_map.get(table, ("summary", "content", "keywords"))
        for term in terms:
            like = f"%{term}%"
            sub = " OR ".join(f"{c} LIKE ?" for c in cols)
            conditions.append(f"({sub})")
            params.extend([like] * len(cols))
        q = f"SELECT *, 1.0 AS _fts_rank FROM {table} WHERE ({' OR '.join(conditions)})"
        if project:
            q += " AND project=?"
            params.append(project)
        if branch:
            q += " AND branch=?"
            params.append(branch)
        if not include_archived and table in ("thoughts", "rules"):
            q += " AND archived=0"
        q += f" LIMIT ?"
        params.append(limit)
        return self.fetchall(q, params)


def _float_list_to_blob(vec: list[float]) -> bytes:
    """Pack a list of floats into a little-endian binary blob for sqlite-vec."""
    import struct
    return struct.pack(f"<{len(vec)}f", *vec)
