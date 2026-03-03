"""Export all memgram data as readable markdown files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .db import create_db


def _json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _bullet_list(items: list[str], indent: str = "") -> str:
    if not items:
        return f"{indent}_(none)_\n"
    return "".join(f"{indent}- {item}\n" for item in items)


def _badge(label: str, value: str) -> str:
    return f"**{label}:** {value}"


def export_markdown(db_path: Optional[str] = None, output_dir: str = "memgram-export") -> Path:
    """Export entire memgram database as markdown files.

    Structure:
        output_dir/
        ├── index.md               # Overview with stats and links
        ├── sessions/
        │   └── <id>.md            # One file per session
        ├── thoughts/
        │   └── <id>.md
        ├── rules/
        │   └── <id>.md
        ├── errors/
        │   └── <id>.md
        ├── groups/
        │   └── <id>.md
        └── projects/
            └── <project>.md       # Project summary + all related items
    """
    out = Path(output_dir)
    db = create_db("sqlite", db_path=db_path) if db_path else create_db("sqlite")

    for sub in ("sessions", "thoughts", "rules", "errors", "groups", "projects"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    p = db.backend.ph
    sessions = db.backend.fetchall("SELECT * FROM sessions ORDER BY started_at DESC")
    thoughts = db.backend.fetchall("SELECT * FROM thoughts ORDER BY created_at DESC")
    rules = db.backend.fetchall("SELECT * FROM rules ORDER BY pinned DESC, severity='critical' DESC, reinforcement_count DESC")
    errors = db.backend.fetchall("SELECT * FROM error_patterns ORDER BY created_at DESC")
    groups = db.backend.fetchall("SELECT * FROM thought_groups ORDER BY updated_at DESC")
    snapshots = db.backend.fetchall("SELECT * FROM compaction_snapshots ORDER BY created_at DESC")
    session_sums = db.backend.fetchall("SELECT * FROM session_summaries ORDER BY created_at DESC")
    project_sums = db.backend.fetchall("SELECT * FROM project_summaries ORDER BY project")
    links = db.backend.fetchall("SELECT * FROM thought_links ORDER BY created_at DESC")

    # ── Index ───────────────────────────────────────────────────────────

    idx = ["# Memgram Export\n"]
    idx.append(f"| Item | Count |")
    idx.append(f"|------|-------|")
    idx.append(f"| Sessions | {len(sessions)} |")
    idx.append(f"| Thoughts | {len(thoughts)} |")
    idx.append(f"| Rules | {len(rules)} |")
    idx.append(f"| Error Patterns | {len(errors)} |")
    idx.append(f"| Groups | {len(groups)} |")
    idx.append(f"| Links | {len(links)} |")
    idx.append(f"| Projects | {len(project_sums)} |")
    idx.append("")

    # Rules summary in index
    if rules:
        idx.append("## Rules Overview\n")
        idx.append("| Severity | Type | Summary | Reinforced | Project |")
        idx.append("|----------|------|---------|------------|---------|")
        for r in rules:
            pin = "📌 " if r["pinned"] else ""
            arc = "🗄️ " if r["archived"] else ""
            idx.append(f"| {r['severity']} | {r['type']} | {arc}{pin}[{r['summary']}](rules/{r['id']}.md) | ×{r['reinforcement_count']} | {r.get('project') or 'global'} |")
        idx.append("")

    # Recent sessions in index
    if sessions:
        idx.append("## Recent Sessions\n")
        idx.append("| Date | Agent | Model | Project | Goal | Status |")
        idx.append("|------|-------|-------|---------|------|--------|")
        for s in sessions[:20]:
            date = (s.get("started_at") or "")[:10]
            idx.append(f"| {date} | {s['agent_type']} | {s['model']} | {s.get('project') or '-'} | [{s.get('goal') or '-'}](sessions/{s['id']}.md) | {s['status']} |")
        idx.append("")

    # Projects in index
    if project_sums:
        idx.append("## Projects\n")
        for ps in project_sums:
            idx.append(f"- [{ps['project']}](projects/{ps['project']}.md) — {ps['summary'][:80]}")
        idx.append("")

    (out / "index.md").write_text("\n".join(idx))

    # ── Sessions ────────────────────────────────────────────────────────

    ss_by_id = {s["session_id"]: s for s in session_sums}
    snap_by_session: dict[str, list] = {}
    for snap in snapshots:
        snap_by_session.setdefault(snap["session_id"], []).append(snap)

    for s in sessions:
        lines = [f"# Session: {s.get('goal') or s['id']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{s['id']}` |")
        lines.append(f"| Agent | {s['agent_type']} |")
        lines.append(f"| Model | {s['model']} |")
        lines.append(f"| Project | {s.get('project') or '-'} |")
        lines.append(f"| Status | {s['status']} |")
        lines.append(f"| Started | {s.get('started_at') or '-'} |")
        lines.append(f"| Ended | {s.get('ended_at') or '-'} |")
        lines.append(f"| Compactions | {s['compaction_count']} |")
        lines.append("")

        if s.get("summary"):
            lines.append(f"## Summary\n\n{s['summary']}\n")

        # Session summary
        ss = ss_by_id.get(s["id"])
        if ss:
            lines.append("## Session Summary\n")
            if ss.get("outcome"):
                lines.append(f"**Outcome:** {ss['outcome']}\n")
            decisions = _json_list(ss.get("decisions_made"))
            if decisions:
                lines.append("**Decisions:**\n")
                lines.append(_bullet_list(decisions))
            files = _json_list(ss.get("files_modified"))
            if files:
                lines.append("**Files Modified:**\n")
                lines.append(_bullet_list(files))
            unresolved = _json_list(ss.get("unresolved_items"))
            if unresolved:
                lines.append("**Unresolved:**\n")
                lines.append(_bullet_list(unresolved))
            if ss.get("next_session_hints"):
                lines.append(f"**Next Session Hints:** {ss['next_session_hints']}\n")

        # Snapshots
        snaps = snap_by_session.get(s["id"], [])
        if snaps:
            lines.append("## Compaction Snapshots\n")
            for snap in sorted(snaps, key=lambda x: x["sequence_num"]):
                lines.append(f"### Snapshot #{snap['sequence_num']} ({snap['created_at'][:19]})\n")
                if snap.get("current_goal"):
                    lines.append(f"**Goal:** {snap['current_goal']}\n")
                if snap.get("progress_summary"):
                    lines.append(f"**Progress:** {snap['progress_summary']}\n")
                ns = _json_list(snap.get("next_steps"))
                if ns:
                    lines.append("**Next Steps:**\n")
                    lines.append(_bullet_list(ns))
                bl = _json_list(snap.get("blockers"))
                if bl:
                    lines.append("**Blockers:**\n")
                    lines.append(_bullet_list(bl))
                oq = _json_list(snap.get("open_questions"))
                if oq:
                    lines.append("**Open Questions:**\n")
                    lines.append(_bullet_list(oq))

        (out / "sessions" / f"{s['id']}.md").write_text("\n".join(lines))

    # ── Thoughts ────────────────────────────────────────────────────────

    for t in thoughts:
        lines = [f"# {t['summary']}\n"]
        tags = []
        if t["pinned"]:
            tags.append("📌 Pinned")
        if t["archived"]:
            tags.append("🗄️ Archived")
        if tags:
            lines.append(" ".join(tags) + "\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{t['id']}` |")
        lines.append(f"| Type | {t['type']} |")
        lines.append(f"| Project | {t.get('project') or '-'} |")
        lines.append(f"| Created | {t['created_at']} |")
        lines.append(f"| Accessed | {t['access_count']} times |")
        kw = _json_list(t.get("keywords"))
        if kw:
            lines.append(f"| Keywords | {', '.join(kw)} |")
        files = _json_list(t.get("associated_files"))
        if files:
            lines.append(f"| Files | {', '.join(f'`{f}`' for f in files)} |")
        if t.get("session_id"):
            lines.append(f"| Session | [{t['session_id']}](../sessions/{t['session_id']}.md) |")
        lines.append("")
        if t.get("content"):
            lines.append(f"## Content\n\n{t['content']}\n")

        (out / "thoughts" / f"{t['id']}.md").write_text("\n".join(lines))

    # ── Rules ───────────────────────────────────────────────────────────

    for r in rules:
        lines = [f"# {r['summary']}\n"]
        tags = []
        if r["pinned"]:
            tags.append("📌 Pinned")
        if r["archived"]:
            tags.append("🗄️ Archived")
        sev_emoji = {"critical": "🔴", "preference": "🟡", "context_dependent": "🔵"}
        tags.append(f"{sev_emoji.get(r['severity'], '')} {r['severity']}")
        type_emoji = {"do": "✅", "dont": "❌", "context_dependent": "⚖️"}
        tags.append(f"{type_emoji.get(r['type'], '')} {r['type']}")
        lines.append(" | ".join(tags) + "\n")

        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{r['id']}` |")
        lines.append(f"| Reinforced | ×{r['reinforcement_count']} |")
        lines.append(f"| Project | {r.get('project') or 'global'} |")
        lines.append(f"| Created | {r['created_at']} |")
        if r.get("condition"):
            lines.append(f"| Condition | {r['condition']} |")
        kw = _json_list(r.get("keywords"))
        if kw:
            lines.append(f"| Keywords | {', '.join(kw)} |")
        files = _json_list(r.get("associated_files"))
        if files:
            lines.append(f"| Files | {', '.join(f'`{f}`' for f in files)} |")
        if r.get("session_id"):
            lines.append(f"| Session | [{r['session_id']}](../sessions/{r['session_id']}.md) |")
        lines.append("")
        if r.get("content"):
            lines.append(f"## Details\n\n{r['content']}\n")

        (out / "rules" / f"{r['id']}.md").write_text("\n".join(lines))

    # ── Error Patterns ──────────────────────────────────────────────────

    for e in errors:
        lines = [f"# Error: {e['error_description'][:80]}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{e['id']}` |")
        lines.append(f"| Project | {e.get('project') or '-'} |")
        lines.append(f"| Created | {e['created_at']} |")
        kw = _json_list(e.get("keywords"))
        if kw:
            lines.append(f"| Keywords | {', '.join(kw)} |")
        files = _json_list(e.get("associated_files"))
        if files:
            lines.append(f"| Files | {', '.join(f'`{f}`' for f in files)} |")
        if e.get("prevention_rule_id"):
            lines.append(f"| Prevention Rule | [{e['prevention_rule_id']}](../rules/{e['prevention_rule_id']}.md) |")
        if e.get("session_id"):
            lines.append(f"| Session | [{e['session_id']}](../sessions/{e['session_id']}.md) |")
        lines.append("")
        lines.append(f"## Error\n\n{e['error_description']}\n")
        if e.get("cause"):
            lines.append(f"## Cause\n\n{e['cause']}\n")
        if e.get("fix"):
            lines.append(f"## Fix\n\n{e['fix']}\n")

        (out / "errors" / f"{e['id']}.md").write_text("\n".join(lines))

    # ── Groups ──────────────────────────────────────────────────────────

    for g in groups:
        members = db.backend.fetchall(
            f"SELECT * FROM group_members WHERE group_id={p}", (g["id"],),
        )
        lines = [f"# Group: {g['name']}\n"]
        if g.get("description"):
            lines.append(f"{g['description']}\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{g['id']}` |")
        lines.append(f"| Project | {g.get('project') or '-'} |")
        lines.append(f"| Members | {len(members)} |")
        lines.append(f"| Updated | {g['updated_at']} |")
        lines.append("")
        if members:
            lines.append("## Members\n")
            type_dir = {"thought": "thoughts", "rule": "rules", "error_pattern": "errors"}
            for m in members:
                d = type_dir.get(m["item_type"], "thoughts")
                # Fetch summary
                table = {"thought": "thoughts", "rule": "rules", "error_pattern": "error_patterns"}.get(m["item_type"])
                summary = ""
                if table:
                    row = db.backend.fetchone(f"SELECT * FROM {table} WHERE id={p}", (m["item_id"],))
                    if row:
                        summary = row.get("summary", row.get("error_description", ""))[:60]
                lines.append(f"- [{m['item_type']}] [{summary}](../{d}/{m['item_id']}.md)")
            lines.append("")

        (out / "groups" / f"{g['id']}.md").write_text("\n".join(lines))

    # ── Projects ────────────────────────────────────────────────────────

    # Build a per-project view even if no project_summary exists
    all_projects = set()
    for t in thoughts:
        if t.get("project"):
            all_projects.add(t["project"])
    for r in rules:
        if r.get("project"):
            all_projects.add(r["project"])
    for s in sessions:
        if s.get("project"):
            all_projects.add(s["project"])
    for ps in project_sums:
        all_projects.add(ps["project"])

    ps_by_name = {ps["project"]: ps for ps in project_sums}

    for proj in sorted(all_projects):
        lines = [f"# Project: {proj}\n"]
        ps = ps_by_name.get(proj)
        if ps:
            if ps.get("summary"):
                lines.append(f"{ps['summary']}\n")
            ts = _json_list(ps.get("tech_stack"))
            if ts:
                lines.append(f"**Tech Stack:** {', '.join(ts)}\n")
            kp = _json_list(ps.get("key_patterns"))
            if kp:
                lines.append("**Key Patterns:**\n")
                lines.append(_bullet_list(kp))
            ag = _json_list(ps.get("active_goals"))
            if ag:
                lines.append("**Active Goals:**\n")
                lines.append(_bullet_list(ag))
            lines.append(f"**Stats:** {ps['total_sessions']} sessions, {ps['total_thoughts']} thoughts, {ps['total_rules']} rules\n")

        # Project rules
        proj_rules = [r for r in rules if r.get("project") == proj]
        if proj_rules:
            lines.append("## Rules\n")
            for r in proj_rules:
                sev = {"critical": "🔴", "preference": "🟡", "context_dependent": "🔵"}.get(r["severity"], "")
                typ = {"do": "✅", "dont": "❌", "context_dependent": "⚖️"}.get(r["type"], "")
                pin = "📌 " if r["pinned"] else ""
                lines.append(f"- {sev} {typ} {pin}[{r['summary']}](../rules/{r['id']}.md) (×{r['reinforcement_count']})")
            lines.append("")

        # Project thoughts
        proj_thoughts = [t for t in thoughts if t.get("project") == proj]
        if proj_thoughts:
            lines.append("## Thoughts\n")
            for t in proj_thoughts[:50]:
                pin = "📌 " if t["pinned"] else ""
                lines.append(f"- [{t['type']}] {pin}[{t['summary']}](../thoughts/{t['id']}.md)")
            lines.append("")

        # Project errors
        proj_errors = [e for e in errors if e.get("project") == proj]
        if proj_errors:
            lines.append("## Error Patterns\n")
            for e in proj_errors:
                lines.append(f"- [{e['error_description'][:60]}](../errors/{e['id']}.md)")
            lines.append("")

        # Project sessions
        proj_sessions = [s for s in sessions if s.get("project") == proj]
        if proj_sessions:
            lines.append("## Sessions\n")
            lines.append("| Date | Agent | Goal | Status |")
            lines.append("|------|-------|------|--------|")
            for s in proj_sessions[:20]:
                date = (s.get("started_at") or "")[:10]
                lines.append(f"| {date} | {s['agent_type']}/{s['model']} | [{s.get('goal') or '-'}](../sessions/{s['id']}.md) | {s['status']} |")
            lines.append("")

        (out / "projects" / f"{proj}.md").write_text("\n".join(lines))

    db.close()

    total = len(sessions) + len(thoughts) + len(rules) + len(errors) + len(groups) + len(all_projects) + 1
    return out, total


def main_export():
    """CLI entry point for export."""
    import argparse
    from .db.sqlite import DEFAULT_DB_PATH

    default_db = os.environ.get("MEMGRAM_DB_PATH", str(DEFAULT_DB_PATH))
    parser = argparse.ArgumentParser(description="Export memgram database as markdown files")
    parser.add_argument("--db-path", type=str, default=default_db,
                        help=f"Path to SQLite database (default: {default_db})")
    parser.add_argument("-o", "--output", type=str, default="memgram-export",
                        help="Output directory (default: memgram-export)")
    args = parser.parse_args()
    out_path, count = export_markdown(db_path=args.db_path, output_dir=args.output)
    print(f"Exported {count} files to {out_path.resolve()}")
