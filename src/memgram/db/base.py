"""Abstract database backend for memgram.

All backend implementations (SQLite, PostgreSQL, MSSQL) must implement
the DatabaseBackend protocol. Business logic (scoring, resume context
assembly) lives in the base so it's shared across all backends.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from ..utils import new_id, now_iso


class DatabaseBackend(ABC):
    """Abstract interface that every DB backend must implement."""

    # ── Lifecycle ───────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def _init_schema(self) -> None: ...

    # ── Primitive operations ────────────────────────────────────────────

    @abstractmethod
    def execute(self, sql: str, params: tuple | list = ()) -> Any: ...

    @abstractmethod
    def execute_script(self, sql: str) -> None: ...

    @abstractmethod
    def fetchone(self, sql: str, params: tuple | list = ()) -> Optional[dict]: ...

    @abstractmethod
    def fetchall(self, sql: str, params: tuple | list = ()) -> list[dict]: ...

    @abstractmethod
    def insert_returning(self, sql: str, params: tuple | list, table: str, id_val: str) -> dict:
        """Insert a row and return it as a dict. Backends handle RETURNING vs re-SELECT."""
        ...

    @abstractmethod
    def last_rowcount(self) -> int: ...

    # ── Full-text search (dialect-specific) ─────────────────────────────

    @abstractmethod
    def fts_search(
        self, table: str, query: str, project: Optional[str] = None,
        include_archived: bool = False, limit: int = 50,
    ) -> list[dict]:
        """Full-text search on a content table. Returns rows with a `_fts_rank` key."""
        ...

    @abstractmethod
    def fts_search_errors(self, query: str, project: Optional[str] = None, limit: int = 50) -> list[dict]: ...

    @abstractmethod
    def fts_search_sessions(self, query: str, project: Optional[str] = None, limit: int = 50) -> list[dict]: ...

    # ── Vector / RAG (dialect-specific) ─────────────────────────────────

    @abstractmethod
    def store_embedding(
        self, item_id: str, item_type: str, text_content: str,
        embedding: list[float], model_name: str,
    ) -> None:
        """Store a vector embedding for an item."""
        ...

    @abstractmethod
    def vector_search(
        self, embedding: list[float], item_type: Optional[str] = None,
        project: Optional[str] = None, limit: int = 20,
    ) -> list[dict]:
        """Find nearest neighbors by vector similarity. Returns rows with `_distance` key."""
        ...

    @abstractmethod
    def delete_embedding(self, item_id: str) -> None:
        """Remove embeddings for an item."""
        ...

    @abstractmethod
    def has_embeddings(self) -> bool:
        """Check if the vector table has any data (to know if RAG is available)."""
        ...

    # ── Placeholder ─────────────────────────────────────────────────────

    @property
    @abstractmethod
    def ph(self) -> str:
        """Parameter placeholder character. '?' for SQLite, '%s' for Postgres, etc."""
        ...

    # ── JSON helpers ────────────────────────────────────────────────────

    def encode_json(self, val: Any) -> str:
        return json.dumps(val) if val is not None else "[]"

    def decode_json(self, val: str | None) -> Any:
        if val is None:
            return []
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return []


class MemgramDB:
    """High-level memgram database interface.

    All business logic lives here. Delegates raw SQL to a DatabaseBackend.
    """

    def __init__(self, backend: DatabaseBackend):
        self.backend = backend
        self.backend.connect()
        self.backend._init_schema()

    def close(self):
        self.backend.close()

    @property
    def _p(self) -> str:
        return self.backend.ph

    # ── Sessions ────────────────────────────────────────────────────────

    def create_session(
        self, agent_type: str, model: str,
        project: Optional[str] = None, goal: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        ts = now_iso()
        sid = new_id()
        p = self._p
        self.backend.execute(
            f"""INSERT INTO sessions (id, agent_type, model, project, goal, status, compaction_count, started_at, metadata)
               VALUES ({p}, {p}, {p}, {p}, {p}, 'active', 0, {p}, {p})""",
            (sid, agent_type, model, project, goal, ts,
             self.backend.encode_json(metadata) if metadata else None),
        )
        return self.backend.fetchone(f"SELECT * FROM sessions WHERE id={p}", (sid,))

    def end_session(self, session_id: str, summary: Optional[str] = None) -> dict:
        ts = now_iso()
        p = self._p
        self.backend.execute(
            f"UPDATE sessions SET status='completed', summary={p}, ended_at={p} WHERE id={p}",
            (summary, ts, session_id),
        )
        return self.backend.fetchone(f"SELECT * FROM sessions WHERE id={p}", (session_id,))

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.backend.fetchone(
            f"SELECT * FROM sessions WHERE id={self._p}", (session_id,),
        )

    def list_sessions(
        self, project: Optional[str] = None,
        agent_type: Optional[str] = None, limit: int = 20,
    ) -> list[dict]:
        p = self._p
        q = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []
        if project:
            q += f" AND project={p}"
            params.append(project)
        if agent_type:
            q += f" AND agent_type={p}"
            params.append(agent_type)
        q += f" ORDER BY started_at DESC LIMIT {p}"
        params.append(limit)
        return self.backend.fetchall(q, params)

    # ── Thoughts ────────────────────────────────────────────────────────

    def add_thought(
        self, summary: str, content: str = "", type: str = "note",
        session_id: Optional[str] = None, project: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        associated_files: Optional[list[str]] = None,
        pinned: bool = False,
    ) -> dict:
        ts = now_iso()
        tid = new_id()
        p = self._p
        self.backend.execute(
            f"""INSERT INTO thoughts
               (id, session_id, type, summary, content, project, keywords,
                associated_files, pinned, archived, access_count,
                created_at, updated_at, last_accessed)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},0,0,{p},{p},{p})""",
            (tid, session_id, type, summary, content, project,
             self.backend.encode_json(keywords or []),
             self.backend.encode_json(associated_files or []),
             1 if pinned else 0, ts, ts, ts),
        )
        return self.backend.fetchone(f"SELECT * FROM thoughts WHERE id={p}", (tid,))

    def update_thought(self, thought_id: str, **fields) -> Optional[dict]:
        allowed = {"summary", "content", "type", "project", "keywords",
                    "associated_files", "pinned", "archived"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_thought(thought_id)
        if "keywords" in updates and isinstance(updates["keywords"], list):
            updates["keywords"] = self.backend.encode_json(updates["keywords"])
        if "associated_files" in updates and isinstance(updates["associated_files"], list):
            updates["associated_files"] = self.backend.encode_json(updates["associated_files"])
        updates["updated_at"] = now_iso()
        p = self._p
        set_clause = ", ".join(f"{k}={p}" for k in updates)
        vals = list(updates.values()) + [thought_id]
        self.backend.execute(f"UPDATE thoughts SET {set_clause} WHERE id={p}", vals)
        return self.get_thought(thought_id)

    def get_thought(self, thought_id: str) -> Optional[dict]:
        p = self._p
        self.backend.execute(
            f"UPDATE thoughts SET access_count=access_count+1, last_accessed={p} WHERE id={p}",
            (now_iso(), thought_id),
        )
        return self.backend.fetchone(f"SELECT * FROM thoughts WHERE id={p}", (thought_id,))

    # ── Rules ───────────────────────────────────────────────────────────

    def add_rule(
        self, summary: str, content: str = "", type: str = "do",
        severity: str = "preference", condition: Optional[str] = None,
        session_id: Optional[str] = None, project: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        associated_files: Optional[list[str]] = None,
        pinned: bool = False,
    ) -> dict:
        ts = now_iso()
        rid = new_id()
        p = self._p
        self.backend.execute(
            f"""INSERT INTO rules
               (id, session_id, type, severity, summary, content, condition, project,
                keywords, associated_files, pinned, archived, reinforcement_count,
                created_at, updated_at, last_accessed)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},0,1,{p},{p},{p})""",
            (rid, session_id, type, severity, summary, content, condition, project,
             self.backend.encode_json(keywords or []),
             self.backend.encode_json(associated_files or []),
             1 if pinned else 0, ts, ts, ts),
        )
        return self.backend.fetchone(f"SELECT * FROM rules WHERE id={p}", (rid,))

    def reinforce_rule(self, rule_id: str, note: Optional[str] = None) -> Optional[dict]:
        ts = now_iso()
        p = self._p
        self.backend.execute(
            f"UPDATE rules SET reinforcement_count=reinforcement_count+1, updated_at={p}, last_accessed={p} WHERE id={p}",
            (ts, ts, rule_id),
        )
        if note:
            row = self.backend.fetchone(f"SELECT content FROM rules WHERE id={p}", (rule_id,))
            if row:
                new_content = row["content"] + f"\n\n[Reinforced {ts}] {note}"
                self.backend.execute(f"UPDATE rules SET content={p} WHERE id={p}", (new_content, rule_id))
        return self.get_rule(rule_id)

    def get_rule(self, rule_id: str) -> Optional[dict]:
        p = self._p
        row = self.backend.fetchone(f"SELECT * FROM rules WHERE id={p}", (rule_id,))
        if row:
            self.backend.execute(
                f"UPDATE rules SET last_accessed={p} WHERE id={p}", (now_iso(), rule_id),
            )
        return row

    def get_rules(
        self, project: Optional[str] = None,
        severity: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        include_global: bool = True, limit: int = 50,
    ) -> list[dict]:
        p = self._p
        q = "SELECT * FROM rules WHERE archived=0"
        params: list[Any] = []
        if project:
            if include_global:
                q += f" AND (project={p} OR project IS NULL)"
            else:
                q += f" AND project={p}"
            params.append(project)
        if severity:
            q += f" AND severity={p}"
            params.append(severity)
        q += f" ORDER BY pinned DESC, reinforcement_count DESC, updated_at DESC LIMIT {p}"
        params.append(limit)
        rows = self.backend.fetchall(q, params)
        if keywords:
            kw_set = {k.lower() for k in keywords}
            return [
                r for r in rows
                if {k.lower() for k in self.backend.decode_json(r.get("keywords", "[]"))} & kw_set
            ]
        return rows

    # ── Compaction Snapshots ────────────────────────────────────────────

    def save_snapshot(
        self, session_id: str, current_goal: Optional[str] = None,
        progress_summary: Optional[str] = None,
        open_questions: Optional[list[str]] = None,
        blockers: Optional[list[str]] = None,
        next_steps: Optional[list[str]] = None,
        active_files: Optional[list[str]] = None,
        key_decisions: Optional[list[str]] = None,
    ) -> dict:
        p = self._p
        row = self.backend.fetchone(
            f"SELECT COALESCE(MAX(sequence_num), 0) + 1 AS next_seq FROM compaction_snapshots WHERE session_id={p}",
            (session_id,),
        )
        seq = row["next_seq"]
        ts = now_iso()
        sid = new_id()
        self.backend.execute(
            f"""INSERT INTO compaction_snapshots
               (id, session_id, sequence_num, current_goal, progress_summary,
                open_questions, blockers, next_steps, active_files, key_decisions, created_at)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})""",
            (sid, session_id, seq, current_goal, progress_summary,
             self.backend.encode_json(open_questions or []),
             self.backend.encode_json(blockers or []),
             self.backend.encode_json(next_steps or []),
             self.backend.encode_json(active_files or []),
             self.backend.encode_json(key_decisions or []), ts),
        )
        self.backend.execute(
            f"UPDATE sessions SET compaction_count=compaction_count+1 WHERE id={p}",
            (session_id,),
        )
        return self.backend.fetchone(f"SELECT * FROM compaction_snapshots WHERE id={p}", (sid,))

    def get_latest_snapshot(self, session_id: str) -> Optional[dict]:
        p = self._p
        return self.backend.fetchone(
            f"SELECT * FROM compaction_snapshots WHERE session_id={p} ORDER BY sequence_num DESC LIMIT 1",
            (session_id,),
        )

    # ── Error Patterns ──────────────────────────────────────────────────

    def add_error_pattern(
        self, error_description: str, cause: Optional[str] = None,
        fix: Optional[str] = None, prevention_rule_id: Optional[str] = None,
        session_id: Optional[str] = None, project: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        associated_files: Optional[list[str]] = None,
    ) -> dict:
        ts = now_iso()
        eid = new_id()
        p = self._p
        self.backend.execute(
            f"""INSERT INTO error_patterns
               (id, session_id, error_description, cause, fix, prevention_rule_id,
                project, keywords, associated_files, created_at)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p})""",
            (eid, session_id, error_description, cause, fix, prevention_rule_id,
             project, self.backend.encode_json(keywords or []),
             self.backend.encode_json(associated_files or []), ts),
        )
        return self.backend.fetchone(f"SELECT * FROM error_patterns WHERE id={p}", (eid,))

    # ── Thought Links ───────────────────────────────────────────────────

    def link_items(
        self, from_id: str, from_type: str,
        to_id: str, to_type: str,
        link_type: str = "related",
    ) -> dict:
        ts = now_iso()
        lid = new_id()
        p = self._p
        self.backend.execute(
            f"""INSERT INTO thought_links (id, from_id, from_type, to_id, to_type, link_type, created_at)
               VALUES ({p},{p},{p},{p},{p},{p},{p})""",
            (lid, from_id, from_type, to_id, to_type, link_type, ts),
        )
        return self.backend.fetchone(f"SELECT * FROM thought_links WHERE id={p}", (lid,))

    def get_related(self, item_id: str) -> list[dict]:
        p = self._p
        return self.backend.fetchall(
            f"SELECT * FROM thought_links WHERE from_id={p} OR to_id={p}",
            (item_id, item_id),
        )

    # ── Project Summaries ───────────────────────────────────────────────

    def get_project_summary(self, project: str) -> Optional[dict]:
        return self.backend.fetchone(
            f"SELECT * FROM project_summaries WHERE project={self._p}", (project,),
        )

    def update_project_summary(
        self, project: str, summary: Optional[str] = None,
        tech_stack: Optional[list[str]] = None,
        key_patterns: Optional[list[str]] = None,
        active_goals: Optional[list[str]] = None,
    ) -> dict:
        ts = now_iso()
        p = self._p
        existing = self.get_project_summary(project)
        if not existing:
            pid = new_id()
            self.backend.execute(
                f"""INSERT INTO project_summaries
                   (id, project, summary, tech_stack, key_patterns, active_goals,
                    total_sessions, total_thoughts, total_rules, created_at, updated_at)
                   VALUES ({p},{p},{p},{p},{p},{p},0,0,0,{p},{p})""",
                (pid, project, summary or "",
                 self.backend.encode_json(tech_stack or []),
                 self.backend.encode_json(key_patterns or []),
                 self.backend.encode_json(active_goals or []), ts, ts),
            )
        else:
            updates: dict[str, Any] = {}
            if summary is not None:
                updates["summary"] = summary
            if tech_stack is not None:
                updates["tech_stack"] = self.backend.encode_json(tech_stack)
            if key_patterns is not None:
                updates["key_patterns"] = self.backend.encode_json(key_patterns)
            if active_goals is not None:
                updates["active_goals"] = self.backend.encode_json(active_goals)
            if updates:
                updates["updated_at"] = ts
                set_clause = ", ".join(f"{k}={p}" for k in updates)
                vals = list(updates.values()) + [project]
                self.backend.execute(
                    f"UPDATE project_summaries SET {set_clause} WHERE project={p}", vals,
                )
        # Update counts
        self.backend.execute(f"""
            UPDATE project_summaries SET
                total_sessions = (SELECT COUNT(*) FROM sessions WHERE project={p}),
                total_thoughts = (SELECT COUNT(*) FROM thoughts WHERE project={p}),
                total_rules = (SELECT COUNT(*) FROM rules WHERE project={p})
            WHERE project={p}
        """, (project, project, project, project))
        return self.backend.fetchone(
            f"SELECT * FROM project_summaries WHERE project={p}", (project,),
        )

    # ── Session Summaries ───────────────────────────────────────────────

    def add_session_summary(
        self, session_id: str, project: Optional[str] = None,
        goal: Optional[str] = None, outcome: Optional[str] = None,
        decisions_made: Optional[list[str]] = None,
        rules_learned: Optional[list[str]] = None,
        errors_encountered: Optional[list[str]] = None,
        files_modified: Optional[list[str]] = None,
        unresolved_items: Optional[list[str]] = None,
        next_session_hints: Optional[str] = None,
    ) -> dict:
        ts = now_iso()
        sid = new_id()
        p = self._p
        # Delete existing summary for this session (upsert)
        self.backend.execute(
            f"DELETE FROM session_summaries WHERE session_id={p}", (session_id,),
        )
        self.backend.execute(
            f"""INSERT INTO session_summaries
               (id, session_id, project, goal, outcome, decisions_made, rules_learned,
                errors_encountered, files_modified, unresolved_items, next_session_hints, created_at)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})""",
            (sid, session_id, project, goal, outcome,
             self.backend.encode_json(decisions_made or []),
             self.backend.encode_json(rules_learned or []),
             self.backend.encode_json(errors_encountered or []),
             self.backend.encode_json(files_modified or []),
             self.backend.encode_json(unresolved_items or []),
             next_session_hints, ts),
        )
        return self.backend.fetchone(
            f"SELECT * FROM session_summaries WHERE session_id={p}", (session_id,),
        )

    # ── Groups ──────────────────────────────────────────────────────────

    def create_group(self, name: str, description: str = "", project: Optional[str] = None) -> dict:
        ts = now_iso()
        gid = new_id()
        p = self._p
        self.backend.execute(
            f"INSERT INTO thought_groups (id, name, description, project, created_at, updated_at) VALUES ({p},{p},{p},{p},{p},{p})",
            (gid, name, description, project, ts, ts),
        )
        return self.backend.fetchone(
            f"SELECT * FROM thought_groups WHERE id={p}", (gid,),
        )

    def add_to_group(self, group_id: str, item_id: str, item_type: str) -> dict:
        ts = now_iso()
        p = self._p
        # Ignore duplicate
        existing = self.backend.fetchone(
            f"SELECT * FROM group_members WHERE group_id={p} AND item_id={p}",
            (group_id, item_id),
        )
        if not existing:
            self.backend.execute(
                f"INSERT INTO group_members (group_id, item_id, item_type, added_at) VALUES ({p},{p},{p},{p})",
                (group_id, item_id, item_type, ts),
            )
        self.backend.execute(
            f"UPDATE thought_groups SET updated_at={p} WHERE id={p}", (ts, group_id),
        )
        return {"group_id": group_id, "item_id": item_id, "item_type": item_type, "added_at": ts}

    def remove_from_group(self, group_id: str, item_id: str) -> bool:
        p = self._p
        self.backend.execute(
            f"DELETE FROM group_members WHERE group_id={p} AND item_id={p}",
            (group_id, item_id),
        )
        return self.backend.last_rowcount() > 0

    def get_group(
        self, group_id: Optional[str] = None,
        name: Optional[str] = None, project: Optional[str] = None,
    ) -> Optional[dict]:
        p = self._p
        if group_id:
            group = self.backend.fetchone(f"SELECT * FROM thought_groups WHERE id={p}", (group_id,))
        elif name:
            q = f"SELECT * FROM thought_groups WHERE name={p}"
            params: list[Any] = [name]
            if project:
                q += f" AND project={p}"
                params.append(project)
            group = self.backend.fetchone(q, params)
        else:
            return None
        if not group:
            return None
        members = self.backend.fetchall(
            f"SELECT * FROM group_members WHERE group_id={p}", (group["id"],),
        )
        resolved = []
        for m in members:
            table_map = {"thought": "thoughts", "rule": "rules", "error_pattern": "error_patterns"}
            tbl = table_map.get(m["item_type"])
            if tbl:
                detail = self.backend.fetchone(f"SELECT * FROM {tbl} WHERE id={p}", (m["item_id"],))
                if detail:
                    m["detail"] = detail
            resolved.append(m)
        group["members"] = resolved
        return group

    # ── Pin / Archive ───────────────────────────────────────────────────

    def pin_item(self, item_id: str, pinned: bool = True) -> Optional[dict]:
        val = 1 if pinned else 0
        ts = now_iso()
        p = self._p
        for table in ("thoughts", "rules"):
            self.backend.execute(
                f"UPDATE {table} SET pinned={p}, updated_at={p} WHERE id={p}",
                (val, ts, item_id),
            )
            if self.backend.last_rowcount() > 0:
                return self.backend.fetchone(f"SELECT * FROM {table} WHERE id={p}", (item_id,))
        return None

    def archive_item(self, item_id: str) -> Optional[dict]:
        ts = now_iso()
        p = self._p
        for table in ("thoughts", "rules"):
            self.backend.execute(
                f"UPDATE {table} SET archived=1, updated_at={p} WHERE id={p}",
                (ts, item_id),
            )
            if self.backend.last_rowcount() > 0:
                return self.backend.fetchone(f"SELECT * FROM {table} WHERE id={p}", (item_id,))
        return None

    # ── Search ──────────────────────────────────────────────────────────

    def search(
        self, query: str, project: Optional[str] = None,
        type_filter: Optional[str] = None,
        include_archived: bool = False, limit: int = 20,
    ) -> list[dict]:
        """Unified full-text search across all tables."""
        results: list[dict] = []

        if not type_filter or type_filter in ("thought", "thoughts"):
            for r in self.backend.fts_search("thoughts", query, project, include_archived):
                r["_type"] = "thought"
                r["_score"] = self._compute_score(r, r.pop("_fts_rank", 1.0))
                results.append(r)

        if not type_filter or type_filter in ("rule", "rules"):
            for r in self.backend.fts_search("rules", query, project, include_archived):
                r["_type"] = "rule"
                r["_score"] = self._compute_score(r, r.pop("_fts_rank", 1.0))
                results.append(r)

        if not type_filter or type_filter in ("error", "error_pattern", "error_patterns"):
            for r in self.backend.fts_search_errors(query, project):
                r["_type"] = "error_pattern"
                r["_score"] = r.pop("_fts_rank", 1.0)
                results.append(r)

        if not type_filter or type_filter in ("session", "session_summary"):
            for r in self.backend.fts_search_sessions(query, project):
                r["_type"] = "session_summary"
                r["_score"] = r.pop("_fts_rank", 1.0)
                results.append(r)

        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results[:limit]

    # ── Vector / RAG Search ────────────────────────────────────────────

    def store_embedding(
        self, item_id: str, item_type: str, text_content: str,
        embedding: list[float], model_name: str,
    ) -> None:
        """Store a vector embedding for an item."""
        self.backend.store_embedding(item_id, item_type, text_content, embedding, model_name)

    def search_by_embedding(
        self, embedding: list[float], project: Optional[str] = None,
        type_filter: Optional[str] = None, limit: int = 20,
    ) -> list[dict]:
        """RAG-style semantic search using vector similarity.

        Returns items ranked by cosine distance, enriched with full item details.
        Falls back to empty results if no embeddings exist.
        """
        if not self.backend.has_embeddings():
            return []

        raw = self.backend.vector_search(embedding, type_filter, project, limit)
        results = []
        p = self._p
        for r in raw:
            item_id = r["item_id"]
            item_type = r["item_type"]
            table_map = {
                "thought": "thoughts", "rule": "rules",
                "error_pattern": "error_patterns",
                "session_summary": "session_summaries",
            }
            tbl = table_map.get(item_type)
            if tbl:
                detail = self.backend.fetchone(f"SELECT * FROM {tbl} WHERE id={p}", (item_id,))
                if detail:
                    detail["_type"] = item_type
                    detail["_distance"] = r.get("_distance", 0)
                    detail["_score"] = max(0, 1.0 - r.get("_distance", 0))
                    results.append(detail)
        return results

    def delete_embedding(self, item_id: str) -> None:
        """Remove embeddings for an item."""
        self.backend.delete_embedding(item_id)

    # ── Resume Context ──────────────────────────────────────────────────

    def get_resume_context(self, project: Optional[str] = None) -> dict:
        """Get everything an AI needs to resume work."""
        p = self._p
        context: dict[str, Any] = {}

        # Last session
        sessions = self.list_sessions(project=project, limit=1)
        if sessions:
            last = sessions[0]
            context["last_session"] = last
            snapshot = self.get_latest_snapshot(last["id"])
            if snapshot:
                context["last_snapshot"] = snapshot
            ss = self.backend.fetchone(
                f"SELECT * FROM session_summaries WHERE session_id={p}", (last["id"],),
            )
            if ss:
                context["last_session_summary"] = ss

        # Pinned thoughts
        q = "SELECT * FROM thoughts WHERE pinned=1 AND archived=0"
        params: list[Any] = []
        if project:
            q += f" AND (project={p} OR project IS NULL)"
            params.append(project)
        context["pinned_thoughts"] = self.backend.fetchall(q, params)

        # Active rules (pinned + critical)
        q = "SELECT * FROM rules WHERE archived=0 AND (pinned=1 OR severity='critical')"
        params = []
        if project:
            q += f" AND (project={p} OR project IS NULL)"
            params.append(project)
        q += " ORDER BY pinned DESC, reinforcement_count DESC"
        context["active_rules"] = self.backend.fetchall(q, params)

        # Project summary
        if project:
            ps = self.get_project_summary(project)
            if ps:
                context["project_summary"] = ps

        return context

    # ── Scoring (shared logic) ──────────────────────────────────────────

    @staticmethod
    def _compute_score(item: dict, fts_rank: float) -> float:
        score = fts_rank * 0.4
        try:
            created = datetime.fromisoformat(item.get("created_at", ""))
            age_days = (datetime.now(timezone.utc) - created).days
            recency = max(0.0, 1.0 - (age_days / 30.0))
        except (ValueError, TypeError):
            recency = 0.5
        score += recency * 0.2
        access = min(item.get("access_count", 0), 100) / 100.0
        score += access * 0.1
        if item.get("pinned"):
            score += 0.2
        sev = item.get("severity", "")
        if sev == "critical":
            score += 0.1
        elif sev == "preference":
            score += 0.03
        return round(score, 4)
