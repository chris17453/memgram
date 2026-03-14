"""Export all memgram data as readable markdown files."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

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


def _slugify(text: str, max_length: int = 80) -> str:
    """Create a filesystem-safe slug: lowercase, dash-separated, trimmed length."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if max_length and len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def _build_slug_map(
    items: Sequence,
    label_getter: Callable[[Any], str | None],
    key_getter: Callable[[Any], str] = lambda item: item["id"],
) -> dict[str, str]:
    """Build a stable slug map keyed by item id/key with collision handling."""
    slugs: dict[str, str] = {}
    used: set[str] = set()

    for item in items:
        key = str(key_getter(item))
        raw_label = label_getter(item) or ""
        base = _slugify(raw_label) or _slugify(key) or key.lower()
        suffix = _slugify(key) or key.lower()

        slug = base
        if slug in used:
            slug = f"{base}-{suffix[:6] or '1'}"
            counter = 2
            while slug in used:
                slug = f"{base}-{suffix[:6] or '1'}-{counter}"
                counter += 1

        used.add(slug)
        slugs[key] = slug

    return slugs


def _collect_projects(thoughts, rules, sessions, project_sums) -> set[str]:
    projects: set[str] = set()
    for t in thoughts:
        if t.get("project"):
            projects.add(t["project"])
    for r in rules:
        if r.get("project"):
            projects.add(r["project"])
    for s in sessions:
        if s.get("project"):
            projects.add(s["project"])
    for ps in project_sums:
        projects.add(ps["project"])
    return projects


def _build_slug_maps(thoughts, rules, errors, sessions, groups, project_names: set[str]) -> dict[str, dict[str, str]]:
    return {
        "thoughts": _build_slug_map(thoughts, lambda t: t.get("summary")),
        "rules": _build_slug_map(rules, lambda r: r.get("summary")),
        "errors": _build_slug_map(errors, lambda e: e.get("error_description")),
        "sessions": _build_slug_map(sessions, lambda s: s.get("goal")),
        "groups": _build_slug_map(groups, lambda g: g.get("name")),
        "projects": _build_slug_map(
            list(project_names),
            label_getter=lambda name: name,
            key_getter=lambda name: str(name),
        ),
    }


def _parse_export_file(path: Path, item_type: str) -> dict[str, Any] | None:
    """Parse an exported markdown file to extract its ID and label for slugging."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return None

    title = lines[0].lstrip("#").strip()
    lower_title = title.lower()
    label = title
    if item_type == "sessions" and lower_title.startswith("session:"):
        label = title.split(":", 1)[1].strip() or title
    elif item_type == "errors" and lower_title.startswith("error:"):
        label = title.split(":", 1)[1].strip() or title
    elif item_type == "projects" and lower_title.startswith("project:"):
        label = title.split(":", 1)[1].strip() or title
    elif item_type == "groups" and lower_title.startswith("group:"):
        label = title.split(":", 1)[1].strip() or title

    id_match = re.search(r"\|\s*ID\s*\|\s*`([^`]+)`", text)
    item_id = id_match.group(1).strip() if id_match else path.stem

    return {"id": item_id, "label": label, "path": path}


def rename_existing_exports(output_dir: str = "memgram-export") -> dict[str, int]:
    """Rename legacy ID-named exports to slug filenames and rewrite internal links.

    This is safe to run repeatedly; it will no-op when files already use slugs.
    Returns a summary of renamed files and updated documents.
    """
    out = Path(output_dir)
    if not out.exists():
        raise FileNotFoundError(f"Export directory not found: {out}")

    type_dirs = {
        "sessions": out / "sessions",
        "thoughts": out / "thoughts",
        "rules": out / "rules",
        "errors": out / "errors",
        "groups": out / "groups",
    }

    parsed: dict[str, list[dict[str, Any]]] = {k: [] for k in type_dirs}
    label_map: dict[str, str] = {}
    for item_type, dir_path in type_dirs.items():
        if not dir_path.exists():
            continue
        for md_path in dir_path.glob("*.md"):
            info = _parse_export_file(md_path, item_type)
            if not info:
                continue
            parsed[item_type].append(info)
            label_map[info["id"]] = info["label"]

    slug_maps = {
        "sessions": _build_slug_map(parsed["sessions"], lambda i: i["label"]),
        "thoughts": _build_slug_map(parsed["thoughts"], lambda i: i["label"]),
        "rules": _build_slug_map(parsed["rules"], lambda i: i["label"]),
        "errors": _build_slug_map(parsed["errors"], lambda i: i["label"]),
        "groups": _build_slug_map(parsed["groups"], lambda i: i["label"]),
    }

    renamed = 0
    for item_type, slug_map in slug_maps.items():
        dir_path = type_dirs[item_type]
        for info in parsed[item_type]:
            item_id = info["id"]
            slug = slug_map.get(item_id)
            if not slug:
                continue
            current = info["path"]
            target = dir_path / f"{slug}.md"
            if current.resolve() == target.resolve():
                continue
            if target.exists() and target != current:
                info["path"] = target  # assume slugged file already exists
                continue
            current.rename(target)
            info["path"] = target
            renamed += 1

    def _rewrite_links(content: str) -> str:
        updated = content
        for item_type, slug_map in slug_maps.items():
            for item_id, slug in slug_map.items():
                updated = re.sub(
                    fr"(\.\./{item_type}/){re.escape(item_id)}\.md",
                    rf"\1{slug}.md",
                    updated,
                )
                updated = re.sub(
                    fr"({item_type}/){re.escape(item_id)}\.md",
                    rf"\1{slug}.md",
                    updated,
                )
                label = label_map.get(item_id)
                if label:
                    updated = updated.replace(f"[{item_id}]", f"[{label}]")
        return updated

    updated_docs = 0
    for md_path in out.glob("**/*.md"):
        original = md_path.read_text(encoding="utf-8")
        rewritten = _rewrite_links(original)
        if rewritten != original:
            md_path.write_text(rewritten, encoding="utf-8")
            updated_docs += 1

    return {"renamed": renamed, "updated": updated_docs}


def _fetch_all_data(db_path: Optional[str] = None, project: Optional[str] = None):
    """Fetch all memgram data from the database. Returns (db, data_dict).

    If *project* is given, only items belonging to that project are returned.
    """
    db = create_db("sqlite", db_path=db_path) if db_path else create_db("sqlite")
    p = db.backend.ph

    if project:
        data = {
            "sessions": db.backend.fetchall(f"SELECT * FROM sessions WHERE project={p} ORDER BY started_at DESC", (project,)),
            "thoughts": db.backend.fetchall(f"SELECT * FROM thoughts WHERE project={p} ORDER BY created_at DESC", (project,)),
            "rules": db.backend.fetchall(f"SELECT * FROM rules WHERE project={p} ORDER BY pinned DESC, severity='critical' DESC, reinforcement_count DESC", (project,)),
            "errors": db.backend.fetchall(f"SELECT * FROM error_patterns WHERE project={p} ORDER BY created_at DESC", (project,)),
            "groups": db.backend.fetchall(f"SELECT * FROM thought_groups WHERE project={p} ORDER BY updated_at DESC", (project,)),
            "snapshots": db.backend.fetchall(
                f"SELECT cs.* FROM compaction_snapshots cs JOIN sessions s ON cs.session_id=s.id WHERE s.project={p} ORDER BY cs.created_at DESC", (project,)),
            "session_sums": db.backend.fetchall(
                f"SELECT ss.* FROM session_summaries ss JOIN sessions s ON ss.session_id=s.id WHERE s.project={p} ORDER BY ss.created_at DESC", (project,)),
            "project_sums": db.backend.fetchall(f"SELECT * FROM project_summaries WHERE project={p} ORDER BY project", (project,)),
            "links": db.backend.fetchall("SELECT * FROM thought_links ORDER BY created_at DESC"),
        }
    else:
        data = {
            "sessions": db.backend.fetchall("SELECT * FROM sessions ORDER BY started_at DESC"),
            "thoughts": db.backend.fetchall("SELECT * FROM thoughts ORDER BY created_at DESC"),
            "rules": db.backend.fetchall("SELECT * FROM rules ORDER BY pinned DESC, severity='critical' DESC, reinforcement_count DESC"),
            "errors": db.backend.fetchall("SELECT * FROM error_patterns ORDER BY created_at DESC"),
            "groups": db.backend.fetchall("SELECT * FROM thought_groups ORDER BY updated_at DESC"),
            "snapshots": db.backend.fetchall("SELECT * FROM compaction_snapshots ORDER BY created_at DESC"),
            "session_sums": db.backend.fetchall("SELECT * FROM session_summaries ORDER BY created_at DESC"),
            "project_sums": db.backend.fetchall("SELECT * FROM project_summaries ORDER BY project"),
            "links": db.backend.fetchall("SELECT * FROM thought_links ORDER BY created_at DESC"),
        }
    return db, data


def export_markdown(db_path: Optional[str] = None, output_dir: str = "memgram-export", project: Optional[str] = None) -> Path:
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
    db, data = _fetch_all_data(db_path, project=project)

    for sub in ("sessions", "thoughts", "rules", "errors", "groups", "projects"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    p = db.backend.ph
    sessions = data["sessions"]
    thoughts = data["thoughts"]
    rules = data["rules"]
    errors = data["errors"]
    groups = data["groups"]
    snapshots = data["snapshots"]
    session_sums = data["session_sums"]
    project_sums = data["project_sums"]
    links = data["links"]
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums)
    slug_maps = _build_slug_maps(thoughts, rules, errors, sessions, groups, all_projects)
    thought_slugs = slug_maps["thoughts"]
    rule_slugs = slug_maps["rules"]
    error_slugs = slug_maps["errors"]
    session_slugs = slug_maps["sessions"]
    group_slugs = slug_maps["groups"]
    project_slugs = slug_maps["projects"]
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums)
    slug_maps = _build_slug_maps(thoughts, rules, errors, sessions, groups, all_projects)
    thought_slugs = slug_maps["thoughts"]
    rule_slugs = slug_maps["rules"]
    error_slugs = slug_maps["errors"]
    session_slugs = slug_maps["sessions"]
    group_slugs = slug_maps["groups"]
    project_slugs = slug_maps["projects"]

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
            r_slug = rule_slugs.get(r["id"], r["id"])
            idx.append(f"| {r['severity']} | {r['type']} | {arc}{pin}[{r['summary']}](rules/{r_slug}.md) | ×{r['reinforcement_count']} | {r.get('project') or 'global'} |")
        idx.append("")

    # Recent sessions in index
    if sessions:
        idx.append("## Recent Sessions\n")
        idx.append("| Date | Agent | Model | Project | Goal | Status |")
        idx.append("|------|-------|-------|---------|------|--------|")
        for s in sessions[:20]:
            date = (s.get("started_at") or "")[:10]
            sess_slug = session_slugs.get(s["id"], s["id"])
            idx.append(f"| {date} | {s['agent_type']} | {s['model']} | {s.get('project') or '-'} | [{s.get('goal') or '-'}](sessions/{sess_slug}.md) | {s['status']} |")
        idx.append("")

    # Projects in index
    if project_sums:
        idx.append("## Projects\n")
        for ps in project_sums:
            proj_slug = project_slugs.get(ps["project"], ps["project"])
            idx.append(f"- [{ps['project']}](projects/{proj_slug}.md) — {ps['summary'][:80]}")
        idx.append("")

    (out / "index.md").write_text("\n".join(idx))

    # ── Sessions ────────────────────────────────────────────────────────

    ss_by_id = {s["session_id"]: s for s in session_sums}
    snap_by_session: dict[str, list] = {}
    for snap in snapshots:
        snap_by_session.setdefault(snap["session_id"], []).append(snap)

    for s in sessions:
        sess_slug = session_slugs.get(s["id"], s["id"])
        lines = [f"# Session: {s.get('goal') or s['id']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{s['id']}` |")
        lines.append(f"| Agent | {s['agent_type']} |")
        lines.append(f"| Model | {s['model']} |")
        lines.append(f"| Project | {s.get('project') or '-'} |")
        lines.append(f"| Branch | {s.get('branch') or '-'} |")
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

        (out / "sessions" / f"{sess_slug}.md").write_text("\n".join(lines))

    # ── Thoughts ────────────────────────────────────────────────────────

    for t in thoughts:
        t_slug = thought_slugs.get(t["id"], t["id"])
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
        lines.append(f"| Branch | {t.get('branch') or '-'} |")
        lines.append(f"| Created | {t['created_at']} |")
        lines.append(f"| Accessed | {t['access_count']} times |")
        kw = _json_list(t.get("keywords"))
        if kw:
            lines.append(f"| Keywords | {', '.join(kw)} |")
        files = _json_list(t.get("associated_files"))
        if files:
            lines.append(f"| Files | {', '.join(f'`{f}`' for f in files)} |")
        if t.get("session_id"):
            sess_slug = session_slugs.get(str(t["session_id"]), str(t["session_id"]))
            lines.append(f"| Session | [{t['session_id']}](../sessions/{sess_slug}.md) |")
        lines.append("")
        if t.get("content"):
            lines.append(f"## Content\n\n{t['content']}\n")

        (out / "thoughts" / f"{t_slug}.md").write_text("\n".join(lines))

    # ── Rules ───────────────────────────────────────────────────────────

    for r in rules:
        r_slug = rule_slugs.get(r["id"], r["id"])
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
        lines.append(f"| Branch | {r.get('branch') or '-'} |")
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
            sess_slug = session_slugs.get(str(r["session_id"]), str(r["session_id"]))
            lines.append(f"| Session | [{r['session_id']}](../sessions/{sess_slug}.md) |")
        lines.append("")
        if r.get("content"):
            lines.append(f"## Details\n\n{r['content']}\n")

        (out / "rules" / f"{r_slug}.md").write_text("\n".join(lines))

    # ── Error Patterns ──────────────────────────────────────────────────

    for e in errors:
        e_slug = error_slugs.get(e["id"], e["id"])
        lines = [f"# Error: {e['error_description'][:80]}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{e['id']}` |")
        lines.append(f"| Project | {e.get('project') or '-'} |")
        lines.append(f"| Branch | {e.get('branch') or '-'} |")
        lines.append(f"| Created | {e['created_at']} |")
        kw = _json_list(e.get("keywords"))
        if kw:
            lines.append(f"| Keywords | {', '.join(kw)} |")
        files = _json_list(e.get("associated_files"))
        if files:
            lines.append(f"| Files | {', '.join(f'`{f}`' for f in files)} |")
        if e.get("prevention_rule_id"):
            rule_slug = rule_slugs.get(str(e["prevention_rule_id"]), str(e["prevention_rule_id"]))
            lines.append(f"| Prevention Rule | [{e['prevention_rule_id']}](../rules/{rule_slug}.md) |")
        if e.get("session_id"):
            sess_slug = session_slugs.get(str(e["session_id"]), str(e["session_id"]))
            lines.append(f"| Session | [{e['session_id']}](../sessions/{sess_slug}.md) |")
        lines.append("")
        lines.append(f"## Error\n\n{e['error_description']}\n")
        if e.get("cause"):
            lines.append(f"## Cause\n\n{e['cause']}\n")
        if e.get("fix"):
            lines.append(f"## Fix\n\n{e['fix']}\n")

        (out / "errors" / f"{e_slug}.md").write_text("\n".join(lines))

    # ── Groups ──────────────────────────────────────────────────────────

    for g in groups:
        g_slug = group_slugs.get(g["id"], g["id"])
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
        lines.append(f"| Branch | {g.get('branch') or '-'} |")
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
                slug_lookup = {
                    "thought": thought_slugs,
                    "rule": rule_slugs,
                    "error_pattern": error_slugs,
                }.get(m["item_type"], {})
                item_slug = slug_lookup.get(m["item_id"], m["item_id"])
                if table:
                    row = db.backend.fetchone(f"SELECT * FROM {table} WHERE id={p}", (m["item_id"],))
                    if row:
                        summary = row.get("summary", row.get("error_description", ""))[:60]
                lines.append(f"- [{m['item_type']}] [{summary}](../{d}/{item_slug}.md)")
            lines.append("")

        (out / "groups" / f"{g_slug}.md").write_text("\n".join(lines))

    # ── Projects ────────────────────────────────────────────────────────

    ps_by_name = {ps["project"]: ps for ps in project_sums}

    for proj in sorted(all_projects):
        proj_slug = project_slugs.get(proj, proj)
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
                r_slug = rule_slugs.get(r["id"], r["id"])
                lines.append(f"- {sev} {typ} {pin}[{r['summary']}](../rules/{r_slug}.md) (×{r['reinforcement_count']})")
            lines.append("")

        # Project thoughts
        proj_thoughts = [t for t in thoughts if t.get("project") == proj]
        if proj_thoughts:
            lines.append("## Thoughts\n")
            for t in proj_thoughts[:50]:
                pin = "📌 " if t["pinned"] else ""
                t_slug = thought_slugs.get(t["id"], t["id"])
                lines.append(f"- [{t['type']}] {pin}[{t['summary']}](../thoughts/{t_slug}.md)")
            lines.append("")

        # Project errors
        proj_errors = [e for e in errors if e.get("project") == proj]
        if proj_errors:
            lines.append("## Error Patterns\n")
            for e in proj_errors:
                e_slug = error_slugs.get(e["id"], e["id"])
                lines.append(f"- [{e['error_description'][:60]}](../errors/{e_slug}.md)")
            lines.append("")

        # Project sessions
        proj_sessions = [s for s in sessions if s.get("project") == proj]
        if proj_sessions:
            lines.append("## Sessions\n")
            lines.append("| Date | Agent | Goal | Status |")
            lines.append("|------|-------|------|--------|")
            for s in proj_sessions[:20]:
                date = (s.get("started_at") or "")[:10]
                sess_slug = session_slugs.get(s["id"], s["id"])
                lines.append(f"| {date} | {s['agent_type']}/{s['model']} | [{s.get('goal') or '-'}](../sessions/{sess_slug}.md) | {s['status']} |")
            lines.append("")

        (out / "projects" / f"{proj_slug}.md").write_text("\n".join(lines))

    db.close()

    total = len(sessions) + len(thoughts) + len(rules) + len(errors) + len(groups) + len(all_projects) + 1
    return out, total


# ── Jekyll Export ──────────────────────────────────────────────────────────


def _front_matter(**kwargs) -> str:
    """Generate YAML front matter block."""
    lines = ["---"]
    for k, v in kwargs.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        elif v is not None:
            # Escape quotes in strings
            lines.append(f'{k}: "{v}"')
    lines.append("---\n")
    return "\n".join(lines)


_JEKYLL_CONFIG = """\
title: Memgram Export
description: AI Memory Graph — exported knowledge base
remote_theme: just-the-docs/just-the-docs
color_scheme: dark

permalink: pretty

aux_links:
  Memgram on GitHub:
    - https://github.com/chris17453/memgram

nav_external_links: []

search_enabled: true
search.heading_level: 3

back_to_top: true
back_to_top_text: Back to top

footer_content: >-
  Exported by <a href="https://github.com/chris17453/memgram">memgram</a>.

plugins:
  - jekyll-remote-theme

exclude:
  - Gemfile
  - Gemfile.lock
  - README.md
"""

_GEMFILE = """\
source "https://rubygems.org"

gem "jekyll", "~> 4.3"
gem "jekyll-remote-theme"

group :jekyll_plugins do
  gem "just-the-docs"
end
"""


def export_jekyll(db_path: Optional[str] = None, output_dir: str = "memgram-jekyll", project: Optional[str] = None) -> tuple[Path, int]:
    """Export memgram database as a Jekyll site for GitHub Pages.

    Uses the just-the-docs theme with proper front matter and navigation.
    """
    out = Path(output_dir)
    db, data = _fetch_all_data(db_path, project=project)

    for sub in ("sessions", "thoughts", "rules", "errors", "groups", "projects"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    p = db.backend.ph
    sessions = data["sessions"]
    thoughts = data["thoughts"]
    rules = data["rules"]
    errors = data["errors"]
    groups = data["groups"]
    snapshots = data["snapshots"]
    session_sums = data["session_sums"]
    project_sums = data["project_sums"]
    links = data["links"]

    # ── Config files ───────────────────────────────────────────────────
    (out / "_config.yml").write_text(_JEKYLL_CONFIG)
    (out / "Gemfile").write_text(_GEMFILE)
    (out / ".nojekyll").write_text("")  # Not needed but harmless; ensures _config.yml is used

    # ── Index ──────────────────────────────────────────────────────────
    idx = [_front_matter(layout="default", title="Home", nav_order=1)]
    idx.append("# Memgram Export\n")
    idx.append("| Item | Count |")
    idx.append("|------|-------|")
    idx.append(f"| [Sessions](sessions/) | {len(sessions)} |")
    idx.append(f"| [Thoughts](thoughts/) | {len(thoughts)} |")
    idx.append(f"| [Rules](rules/) | {len(rules)} |")
    idx.append(f"| [Error Patterns](errors/) | {len(errors)} |")
    idx.append(f"| [Groups](groups/) | {len(groups)} |")
    idx.append(f"| Links | {len(links)} |")
    idx.append(f"| [Projects](projects/) | {len(project_sums)} |")
    idx.append("")

    if rules:
        idx.append("## Rules Overview\n")
        idx.append("| Severity | Type | Summary | Reinforced | Project |")
        idx.append("|----------|------|---------|------------|---------|")
        for r in rules:
            pin = "📌 " if r["pinned"] else ""
            arc = "🗄️ " if r["archived"] else ""
            r_slug = rule_slugs.get(r["id"], r["id"])
            idx.append(f"| {r['severity']} | {r['type']} | {arc}{pin}[{r['summary']}](rules/{r_slug}/) | ×{r['reinforcement_count']} | {r.get('project') or 'global'} |")
        idx.append("")

    if sessions:
        idx.append("## Recent Sessions\n")
        idx.append("| Date | Agent | Model | Project | Goal | Status |")
        idx.append("|------|-------|-------|---------|------|--------|")
        for s in sessions[:20]:
            date = (s.get("started_at") or "")[:10]
            sess_slug = session_slugs.get(s["id"], s["id"])
            idx.append(f"| {date} | {s['agent_type']} | {s['model']} | {s.get('project') or '-'} | [{s.get('goal') or '-'}](sessions/{sess_slug}/) | {s['status']} |")
        idx.append("")

    if project_sums:
        idx.append("## Projects\n")
        for ps in project_sums:
            proj_slug = project_slugs.get(ps["project"], ps["project"])
            idx.append(f"- [{ps['project']}](projects/{proj_slug}/) — {ps['summary'][:80]}")
        idx.append("")

    (out / "index.md").write_text("\n".join(idx))

    # ── Section Index Pages ────────────────────────────────────────────

    section_nav = {
        "sessions": ("Sessions", 2),
        "thoughts": ("Thoughts", 3),
        "rules": ("Rules", 4),
        "errors": ("Error Patterns", 5),
        "groups": ("Groups", 6),
        "projects": ("Projects", 7),
    }

    for section, (title, nav_order) in section_nav.items():
        fm = _front_matter(
            layout="default", title=title, nav_order=nav_order,
            has_children=True, has_toc=False,
        )
        (out / section / "index.md").write_text(fm + f"# {title}\n")

    # ── Sessions ───────────────────────────────────────────────────────

    ss_by_id = {s["session_id"]: s for s in session_sums}
    snap_by_session: dict[str, list] = {}
    for snap in snapshots:
        snap_by_session.setdefault(snap["session_id"], []).append(snap)

    for i, s in enumerate(sessions):
        sess_slug = session_slugs.get(s["id"], s["id"])
        title = (s.get("goal") or s["id"])[:80]
        fm = _front_matter(
            layout="default", title=title,
            parent="Sessions", nav_order=i + 1,
        )
        lines = [fm, f"# Session: {s.get('goal') or s['id']}\n"]
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| ID | `{s['id']}` |")
        lines.append(f"| Agent | {s['agent_type']} |")
        lines.append(f"| Model | {s['model']} |")
        lines.append(f"| Project | {s.get('project') or '-'} |")
        lines.append(f"| Branch | {s.get('branch') or '-'} |")
        lines.append(f"| Status | {s['status']} |")
        lines.append(f"| Started | {s.get('started_at') or '-'} |")
        lines.append(f"| Ended | {s.get('ended_at') or '-'} |")
        lines.append(f"| Compactions | {s['compaction_count']} |")
        lines.append("")

        if s.get("summary"):
            lines.append(f"## Summary\n\n{s['summary']}\n")

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

        (out / "sessions" / f"{sess_slug}.md").write_text("\n".join(lines))

    # ── Thoughts ───────────────────────────────────────────────────────

    for i, t in enumerate(thoughts):
        t_slug = thought_slugs.get(t["id"], t["id"])
        title = t["summary"][:80].replace('"', '\\"')
        fm = _front_matter(
            layout="default", title=title,
            parent="Thoughts", nav_order=i + 1,
        )
        lines = [fm, f"# {t['summary']}\n"]
        tags = []
        if t["pinned"]:
            tags.append("📌 Pinned")
        if t["archived"]:
            tags.append("🗄️ Archived")
        if tags:
            lines.append(" ".join(tags) + "\n")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| ID | `{t['id']}` |")
        lines.append(f"| Type | {t['type']} |")
        lines.append(f"| Project | {t.get('project') or '-'} |")
        lines.append(f"| Branch | {t.get('branch') or '-'} |")
        lines.append(f"| Created | {t['created_at']} |")
        lines.append(f"| Accessed | {t['access_count']} times |")
        kw = _json_list(t.get("keywords"))
        if kw:
            lines.append(f"| Keywords | {', '.join(kw)} |")
        files = _json_list(t.get("associated_files"))
        if files:
            lines.append(f"| Files | {', '.join(f'`{f}`' for f in files)} |")
        if t.get("session_id"):
            sess_slug = session_slugs.get(str(t["session_id"]), str(t["session_id"]))
            lines.append(f"| Session | [{t['session_id']}](../sessions/{sess_slug}/) |")
        lines.append("")
        if t.get("content"):
            lines.append(f"## Content\n\n{t['content']}\n")

        (out / "thoughts" / f"{t_slug}.md").write_text("\n".join(lines))

    # ── Rules ──────────────────────────────────────────────────────────

    for i, r in enumerate(rules):
        r_slug = rule_slugs.get(r["id"], r["id"])
        title = r["summary"][:80].replace('"', '\\"')
        fm = _front_matter(
            layout="default", title=title,
            parent="Rules", nav_order=i + 1,
        )
        lines = [fm, f"# {r['summary']}\n"]
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

        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| ID | `{r['id']}` |")
        lines.append(f"| Reinforced | ×{r['reinforcement_count']} |")
        lines.append(f"| Project | {r.get('project') or 'global'} |")
        lines.append(f"| Branch | {r.get('branch') or '-'} |")
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
            sess_slug = session_slugs.get(str(r["session_id"]), str(r["session_id"]))
            lines.append(f"| Session | [{r['session_id']}](../sessions/{sess_slug}/) |")
        lines.append("")
        if r.get("content"):
            lines.append(f"## Details\n\n{r['content']}\n")

        (out / "rules" / f"{r_slug}.md").write_text("\n".join(lines))

    # ── Error Patterns ─────────────────────────────────────────────────

    for i, e in enumerate(errors):
        e_slug = error_slugs.get(e["id"], e["id"])
        title = e["error_description"][:80].replace('"', '\\"')
        fm = _front_matter(
            layout="default", title=title,
            parent="Error Patterns", nav_order=i + 1,
        )
        lines = [fm, f"# Error: {e['error_description'][:80]}\n"]
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| ID | `{e['id']}` |")
        lines.append(f"| Project | {e.get('project') or '-'} |")
        lines.append(f"| Branch | {e.get('branch') or '-'} |")
        lines.append(f"| Created | {e['created_at']} |")
        kw = _json_list(e.get("keywords"))
        if kw:
            lines.append(f"| Keywords | {', '.join(kw)} |")
        files = _json_list(e.get("associated_files"))
        if files:
            lines.append(f"| Files | {', '.join(f'`{f}`' for f in files)} |")
        if e.get("prevention_rule_id"):
            rule_slug = rule_slugs.get(str(e["prevention_rule_id"]), str(e["prevention_rule_id"]))
            lines.append(f"| Prevention Rule | [{e['prevention_rule_id']}](../rules/{rule_slug}/) |")
        if e.get("session_id"):
            sess_slug = session_slugs.get(str(e["session_id"]), str(e["session_id"]))
            lines.append(f"| Session | [{e['session_id']}](../sessions/{sess_slug}/) |")
        lines.append("")
        lines.append(f"## Error\n\n{e['error_description']}\n")
        if e.get("cause"):
            lines.append(f"## Cause\n\n{e['cause']}\n")
        if e.get("fix"):
            lines.append(f"## Fix\n\n{e['fix']}\n")

        (out / "errors" / f"{e_slug}.md").write_text("\n".join(lines))

    # ── Groups ─────────────────────────────────────────────────────────

    for i, g in enumerate(groups):
        g_slug = group_slugs.get(g["id"], g["id"])
        members = db.backend.fetchall(
            f"SELECT * FROM group_members WHERE group_id={p}", (g["id"],),
        )
        title = g["name"][:80].replace('"', '\\"')
        fm = _front_matter(
            layout="default", title=f"Group: {title}",
            parent="Groups", nav_order=i + 1,
        )
        lines = [fm, f"# Group: {g['name']}\n"]
        if g.get("description"):
            lines.append(f"{g['description']}\n")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| ID | `{g['id']}` |")
        lines.append(f"| Project | {g.get('project') or '-'} |")
        lines.append(f"| Branch | {g.get('branch') or '-'} |")
        lines.append(f"| Members | {len(members)} |")
        lines.append(f"| Updated | {g['updated_at']} |")
        lines.append("")
        if members:
            lines.append("## Members\n")
            type_dir = {"thought": "thoughts", "rule": "rules", "error_pattern": "errors"}
            for m in members:
                d = type_dir.get(m["item_type"], "thoughts")
                table = {"thought": "thoughts", "rule": "rules", "error_pattern": "error_patterns"}.get(m["item_type"])
                summary = ""
                slug_lookup = {
                    "thought": thought_slugs,
                    "rule": rule_slugs,
                    "error_pattern": error_slugs,
                }.get(m["item_type"], {})
                item_slug = slug_lookup.get(m["item_id"], m["item_id"])
                if table:
                    row = db.backend.fetchone(f"SELECT * FROM {table} WHERE id={p}", (m["item_id"],))
                    if row:
                        summary = row.get("summary", row.get("error_description", ""))[:60]
                lines.append(f"- [{m['item_type']}] [{summary}](../{d}/{item_slug}/) ")
            lines.append("")

        (out / "groups" / f"{g_slug}.md").write_text("\n".join(lines))

    # ── Projects ───────────────────────────────────────────────────────

    ps_by_name = {ps["project"]: ps for ps in project_sums}

    for i, proj in enumerate(sorted(all_projects)):
        proj_slug = project_slugs.get(proj, proj)
        fm = _front_matter(
            layout="default", title=f"Project: {proj}",
            parent="Projects", nav_order=i + 1,
        )
        lines = [fm, f"# Project: {proj}\n"]
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

        proj_rules = [r for r in rules if r.get("project") == proj]
        if proj_rules:
            lines.append("## Rules\n")
            for r in proj_rules:
                sev = {"critical": "🔴", "preference": "🟡", "context_dependent": "🔵"}.get(r["severity"], "")
                typ = {"do": "✅", "dont": "❌", "context_dependent": "⚖️"}.get(r["type"], "")
                pin = "📌 " if r["pinned"] else ""
                r_slug = rule_slugs.get(r["id"], r["id"])
                lines.append(f"- {sev} {typ} {pin}[{r['summary']}](../rules/{r_slug}/) (×{r['reinforcement_count']})")
            lines.append("")

        proj_thoughts = [t for t in thoughts if t.get("project") == proj]
        if proj_thoughts:
            lines.append("## Thoughts\n")
            for t in proj_thoughts[:50]:
                pin = "📌 " if t["pinned"] else ""
                t_slug = thought_slugs.get(t["id"], t["id"])
                lines.append(f"- [{t['type']}] {pin}[{t['summary']}](../thoughts/{t_slug}/)")
            lines.append("")

        proj_errors = [e for e in errors if e.get("project") == proj]
        if proj_errors:
            lines.append("## Error Patterns\n")
            for e in proj_errors:
                e_slug = error_slugs.get(e["id"], e["id"])
                lines.append(f"- [{e['error_description'][:60]}](../errors/{e_slug}/)")
            lines.append("")

        proj_sessions = [s for s in sessions if s.get("project") == proj]
        if proj_sessions:
            lines.append("## Sessions\n")
            lines.append("| Date | Agent | Goal | Status |")
            lines.append("|------|-------|------|--------|")
            for s in proj_sessions[:20]:
                date = (s.get("started_at") or "")[:10]
                sess_slug = session_slugs.get(s["id"], s["id"])
                lines.append(f"| {date} | {s['agent_type']}/{s['model']} | [{s.get('goal') or '-'}](../sessions/{sess_slug}/) | {s['status']} |")
            lines.append("")

        (out / "projects" / f"{proj_slug}.md").write_text("\n".join(lines))

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
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output directory (default: memgram-export or memgram-jekyll)")
    parser.add_argument("-f", "--format", type=str, default="markdown",
                        choices=["markdown", "jekyll"],
                        help="Export format: markdown (plain) or jekyll (GitHub Pages site)")
    parser.add_argument("-p", "--project", type=str, default=None,
                        help="Export only a single project (by name)")
    args = parser.parse_args()

    if args.format == "jekyll":
        output_dir = args.output or "memgram-jekyll"
        out_path, count = export_jekyll(db_path=args.db_path, output_dir=output_dir, project=args.project)
        print(f"Exported {count} files as Jekyll site to {out_path.resolve()}")
        print(f"To deploy: push to GitHub and enable Pages from Settings > Pages")
    else:
        output_dir = args.output or "memgram-export"
        out_path, count = export_markdown(db_path=args.db_path, output_dir=output_dir, project=args.project)
        print(f"Exported {count} files to {out_path.resolve()}")
