"""Data models for memgram."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Session:
    id: str
    agent_type: str
    model: str
    project: Optional[str] = None
    branch: Optional[str] = None
    goal: Optional[str] = None
    status: str = "active"
    summary: Optional[str] = None
    compaction_count: int = 0
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    metadata: Optional[str] = None  # JSON


@dataclass
class Thought:
    id: str
    session_id: Optional[str] = None
    type: str = "note"  # observation, decision, idea, error, pattern, note
    summary: str = ""
    content: str = ""
    project: Optional[str] = None
    branch: Optional[str] = None
    agent_type: Optional[str] = None  # AI agent: copilot, claude, codex, etc.
    agent_model: Optional[str] = None  # Model: gpt-4, claude-sonnet, etc.
    keywords: str = "[]"  # JSON array
    associated_files: str = "[]"  # JSON array
    pinned: int = 0
    archived: int = 0
    access_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_accessed: Optional[str] = None


@dataclass
class Rule:
    id: str
    session_id: Optional[str] = None
    type: str = "do"  # do, dont, context_dependent
    severity: str = "preference"  # critical, preference, context_dependent
    summary: str = ""
    content: str = ""
    condition: Optional[str] = None
    project: Optional[str] = None
    branch: Optional[str] = None
    agent_type: Optional[str] = None  # AI agent: copilot, claude, codex, etc.
    agent_model: Optional[str] = None  # Model: gpt-4, claude-sonnet, etc.
    keywords: str = "[]"
    associated_files: str = "[]"
    pinned: int = 0
    archived: int = 0
    reinforcement_count: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_accessed: Optional[str] = None


@dataclass
class CompactionSnapshot:
    id: str
    session_id: str
    sequence_num: int = 1
    current_goal: Optional[str] = None
    progress_summary: Optional[str] = None
    open_questions: str = "[]"
    blockers: str = "[]"
    next_steps: str = "[]"
    active_files: str = "[]"
    key_decisions: str = "[]"
    created_at: Optional[str] = None


@dataclass
class ThoughtLink:
    id: str
    from_id: str
    from_type: str  # thought, rule, error_pattern, spec, feature, component, plan, person
    to_id: str
    to_type: str  # thought, rule, error_pattern, spec, feature, component, plan, person
    link_type: str = "related"  # informs, contradicts, supersedes, related, caused_by, implements, owns, depends_on, authored_by
    created_at: Optional[str] = None


@dataclass
class ErrorPattern:
    id: str
    session_id: Optional[str] = None
    error_description: str = ""
    cause: Optional[str] = None
    fix: Optional[str] = None
    prevention_rule_id: Optional[str] = None
    project: Optional[str] = None
    branch: Optional[str] = None
    agent_type: Optional[str] = None  # AI agent: copilot, claude, codex, etc.
    agent_model: Optional[str] = None  # Model: gpt-4, claude-sonnet, etc.
    keywords: str = "[]"
    associated_files: str = "[]"
    created_at: Optional[str] = None


@dataclass
class ProjectSummary:
    id: str
    project: str
    summary: str = ""
    tech_stack: str = "[]"
    key_patterns: str = "[]"
    active_goals: str = "[]"
    total_sessions: int = 0
    total_thoughts: int = 0
    total_rules: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class SessionSummary:
    id: str
    session_id: str
    project: Optional[str] = None
    branch: Optional[str] = None
    goal: Optional[str] = None
    outcome: Optional[str] = None
    decisions_made: str = "[]"
    rules_learned: str = "[]"
    errors_encountered: str = "[]"
    files_modified: str = "[]"
    unresolved_items: str = "[]"
    next_session_hints: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ThoughtGroup:
    id: str
    name: str
    description: str = ""
    project: Optional[str] = None
    branch: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class GroupMember:
    group_id: str
    item_id: str
    item_type: str  # thought, rule, error_pattern
    added_at: Optional[str] = None


@dataclass
class Plan:
    id: str
    title: str
    description: str = ""
    scope: str = "project"  # project, sprint, session, milestone, custom
    status: str = "draft"  # draft, active, paused, completed, abandoned
    priority: str = "medium"  # low, medium, high, critical
    session_id: Optional[str] = None  # pin to a session
    project: Optional[str] = None
    branch: Optional[str] = None
    due_date: Optional[str] = None  # ISO 8601
    tags: str = "[]"  # JSON array
    total_tasks: int = 0
    completed_tasks: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class PlanTask:
    id: str
    plan_id: str
    title: str
    description: str = ""
    status: str = "pending"  # pending, in_progress, completed, skipped, blocked
    position: int = 0
    assignee: Optional[str] = None  # agent or person
    depends_on: Optional[str] = None  # task_id dependency
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Spec:
    id: str
    title: str
    description: str = ""
    status: str = "draft"  # draft, review, approved, implemented, deprecated
    priority: str = "medium"  # low, medium, high, critical
    acceptance_criteria: str = "[]"  # JSON array of criteria strings
    project: Optional[str] = None
    branch: Optional[str] = None
    session_id: Optional[str] = None
    author_id: Optional[str] = None  # person id
    tags: str = "[]"  # JSON array
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Feature:
    id: str
    name: str
    description: str = ""
    status: str = "proposed"  # proposed, in_progress, completed, shipped, deprecated
    priority: str = "medium"  # low, medium, high, critical
    spec_id: Optional[str] = None  # linked spec
    project: Optional[str] = None
    branch: Optional[str] = None
    session_id: Optional[str] = None
    lead_id: Optional[str] = None  # person id
    tags: str = "[]"  # JSON array
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Component:
    id: str
    name: str
    description: str = ""
    type: str = "module"  # service, module, library, api, ui, database, infrastructure
    project: Optional[str] = None
    branch: Optional[str] = None
    owner_id: Optional[str] = None  # person id
    tech_stack: str = "[]"  # JSON array
    tags: str = "[]"  # JSON array
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Person:
    id: str
    name: str
    type: str = "individual"  # individual, contractor, team_member
    role: str = ""  # engineer, designer, pm, lead, devops, etc.
    email: Optional[str] = None
    github: Optional[str] = None
    skills: str = "[]"  # JSON array
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Team:
    id: str
    name: str
    description: str = ""
    project: Optional[str] = None
    lead_id: Optional[str] = None  # person id
    tags: str = "[]"  # JSON array
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TeamMember:
    team_id: str
    person_id: str
    role: str = "member"  # member, lead, contributor
    joined_at: Optional[str] = None


@dataclass
class Ticket:
    id: str
    ticket_number: str  # e.g. "MG-42", "PROJ-123"
    title: str
    description: str = ""
    status: str = "open"  # open, in_progress, review, resolved, closed, wontfix
    priority: str = "medium"  # low, medium, high, critical
    type: str = "task"  # bug, task, feature, improvement, question
    assignee_id: Optional[str] = None  # person id
    reporter_id: Optional[str] = None  # person id
    project: Optional[str] = None
    branch: Optional[str] = None
    session_id: Optional[str] = None
    parent_id: Optional[str] = None  # parent ticket for sub-tickets
    tags: str = "[]"  # JSON array
    due_date: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Instruction:
    id: str
    section: str  # slug: "session-lifecycle"
    title: str  # "Session Lifecycle"
    content: str = ""
    position: int = 0
    priority: str = "medium"  # critical, high, medium, low
    scope: str = "global"  # global, project, branch
    project: Optional[str] = None
    branch: Optional[str] = None
    active: int = 1
    tags: str = "[]"  # JSON array
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Attachment:
    id: str
    entity_id: str  # ID of the entity this is attached to
    entity_type: str  # person, team, component, feature, spec, plan, thought, rule, error_pattern, project, instruction
    url: str  # URL or relative file path
    label: str = ""  # display label
    type: str = "link"  # link, image, audio, video, document
    mime_type: Optional[str] = None
    description: str = ""
    position: int = 0
    created_at: Optional[str] = None


@dataclass
class Endpoint:
    id: str
    method: str = "GET"  # GET, POST, PUT, DELETE, PATCH
    path: str = ""
    base_url: str = ""
    description: str = ""
    auth_type: str = "none"  # none, api_key, bearer, oauth, basic
    rate_limit: Optional[str] = None
    request_schema: str = "{}"  # JSON
    response_schema: str = "{}"  # JSON
    status: str = "active"  # active, deprecated, planned
    project: Optional[str] = None
    branch: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Credential:
    id: str
    name: str
    type: str = "api_key"  # api_key, token, password, certificate, ssh_key, oauth
    provider: str = ""
    vault_path: Optional[str] = None
    env_var: Optional[str] = None
    description: str = ""
    project: Optional[str] = None
    last_rotated: Optional[str] = None
    expires_at: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Environment:
    id: str
    name: str
    type: str = "development"  # development, staging, production, testing, local
    url: Optional[str] = None
    description: str = ""
    project: Optional[str] = None
    config: str = "{}"  # JSON
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Deployment:
    id: str
    version: str
    environment_id: Optional[str] = None
    status: str = "pending"  # pending, deploying, deployed, failed, rolled_back
    strategy: str = "rolling"  # rolling, canary, blue_green, recreate
    description: str = ""
    project: Optional[str] = None
    branch: Optional[str] = None
    session_id: Optional[str] = None
    deployed_by: Optional[str] = None
    rollback_to: Optional[str] = None
    deployed_at: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Build:
    id: str
    name: str
    pipeline: str = ""
    status: str = "pending"  # pending, running, passed, failed, cancelled
    trigger_type: str = "push"  # push, pr, manual, schedule
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    artifact_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    project: Optional[str] = None
    session_id: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Incident:
    id: str
    title: str
    severity: str = "p3"  # p0, p1, p2, p3, p4
    status: str = "investigating"  # investigating, identified, monitoring, resolved, postmortem
    description: str = ""
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    timeline: str = "[]"  # JSON array
    project: Optional[str] = None
    lead_id: Optional[str] = None
    started_at: Optional[str] = None
    resolved_at: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Dependency:
    id: str
    name: str
    version: str = ""
    type: str = "library"  # library, service, database, api, tool
    source: Optional[str] = None
    license: Optional[str] = None
    description: str = ""
    project: Optional[str] = None
    pinned_version: Optional[str] = None
    latest_version: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Runbook:
    id: str
    title: str
    description: str = ""
    steps: str = "[]"  # JSON array of step objects
    trigger_conditions: Optional[str] = None
    project: Optional[str] = None
    last_executed: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Decision:
    id: str
    title: str
    status: str = "proposed"  # proposed, accepted, deprecated, superseded
    context: str = ""
    options: str = "[]"  # JSON array
    outcome: Optional[str] = None
    consequences: Optional[str] = None
    project: Optional[str] = None
    branch: Optional[str] = None
    session_id: Optional[str] = None
    author_id: Optional[str] = None
    superseded_by: Optional[str] = None
    decided_at: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Diagram:
    id: str
    title: str
    diagram_type: str = "mermaid"  # mermaid, chart, network, servicemap, table
    definition: str = ""           # raw mermaid syntax, Chart.js JSON, D3 JSON, etc.
    description: str = ""
    data_source: Optional[str] = None  # future: query or entity ref for auto-population
    project: Optional[str] = None
    branch: Optional[str] = None
    session_id: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Comment:
    id: str
    entity_id: str
    entity_type: str
    author: str = ""
    content: str = ""
    parent_id: Optional[str] = None
    project: Optional[str] = None
    tags: str = "[]"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class AuditLogEntry:
    id: str
    entity_id: str
    entity_type: str
    action: str  # created, updated, deleted, status_changed
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    actor: Optional[str] = None
    project: Optional[str] = None
    created_at: Optional[str] = None
