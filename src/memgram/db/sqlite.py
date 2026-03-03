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

    # ── Lifecycle ───────────────────────────────────────────────────────

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        # Load sqlite-vec
        self.conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_schema(self) -> None:
        assert self.conn is not None
        self.conn.executescript(CORE_SCHEMA)
        self._migrate_add_branch()  # must run before INDEXES (adds branch column)
        self.conn.executescript(FTS_SCHEMA)
        self.conn.executescript(FTS_TRIGGERS)
        self.conn.executescript(INDEXES)
        # sqlite-vec virtual table for vector search
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
        self.conn.execute("DELETE FROM embeddings_vec WHERE item_id=?", (item_id,))
        self.conn.execute("DELETE FROM embedding_meta WHERE item_id=?", (item_id,))
        self.conn.commit()

    def has_embeddings(self) -> bool:
        assert self.conn is not None
        row = self.conn.execute("SELECT COUNT(*) AS cnt FROM embedding_meta").fetchone()
        return row["cnt"] > 0 if row else False

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
