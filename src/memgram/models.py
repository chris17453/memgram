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
    from_type: str  # thought, rule
    to_id: str
    to_type: str  # thought, rule
    link_type: str = "related"  # informs, contradicts, supersedes, related, caused_by
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
