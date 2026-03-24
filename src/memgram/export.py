"""Export all memgram data as readable markdown files."""

from __future__ import annotations

import html as _html
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


def _collect_projects(*collections) -> set[str]:
    projects: set[str] = set()
    for coll in collections:
        for item in coll:
            proj = item.get("project") if isinstance(item, dict) else None
            if proj:
                projects.add(proj)
    return projects


def _build_slug_maps(data: dict, project_names: set[str]) -> dict[str, dict[str, str]]:
    maps = {
        "thoughts": _build_slug_map(data.get("thoughts", []), lambda t: t.get("summary")),
        "rules": _build_slug_map(data.get("rules", []), lambda r: r.get("summary")),
        "errors": _build_slug_map(data.get("errors", []), lambda e: e.get("error_description")),
        "sessions": _build_slug_map(data.get("sessions", []), lambda s: s.get("goal")),
        "groups": _build_slug_map(data.get("groups", []), lambda g: g.get("name")),
        "plans": _build_slug_map(data.get("plans", []), lambda p: p.get("title")),
        "specs": _build_slug_map(data.get("specs", []), lambda s: s.get("title")),
        "features": _build_slug_map(data.get("features", []), lambda f: f.get("name")),
        "components": _build_slug_map(data.get("components", []), lambda c: c.get("name")),
        "people": _build_slug_map(data.get("people", []), lambda p: p.get("name")),
        "teams": _build_slug_map(data.get("teams", []), lambda t: t.get("name")),
        "projects": _build_slug_map(
            list(project_names),
            label_getter=lambda name: name,
            key_getter=lambda name: str(name),
        ),
    }
    return maps


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

    pf = f" WHERE project={p}" if project else ""
    pp = (project,) if project else ()

    if project:
        data = {
            "sessions": db.backend.fetchall(f"SELECT * FROM sessions WHERE project={p} ORDER BY started_at DESC", pp),
            "thoughts": db.backend.fetchall(f"SELECT * FROM thoughts WHERE project={p} ORDER BY created_at DESC", pp),
            "rules": db.backend.fetchall(f"SELECT * FROM rules WHERE project={p} ORDER BY pinned DESC, severity='critical' DESC, reinforcement_count DESC", pp),
            "errors": db.backend.fetchall(f"SELECT * FROM error_patterns WHERE project={p} ORDER BY created_at DESC", pp),
            "groups": db.backend.fetchall(f"SELECT * FROM thought_groups WHERE project={p} ORDER BY updated_at DESC", pp),
            "snapshots": db.backend.fetchall(
                f"SELECT cs.* FROM compaction_snapshots cs JOIN sessions s ON cs.session_id=s.id WHERE s.project={p} ORDER BY cs.created_at DESC", pp),
            "session_sums": db.backend.fetchall(
                f"SELECT ss.* FROM session_summaries ss JOIN sessions s ON ss.session_id=s.id WHERE s.project={p} ORDER BY ss.created_at DESC", pp),
            "project_sums": db.backend.fetchall(f"SELECT * FROM project_summaries WHERE project={p} ORDER BY project", pp),
            "links": db.backend.fetchall("SELECT * FROM thought_links ORDER BY created_at DESC"),
            "plans": db.backend.fetchall(f"SELECT * FROM plans WHERE project={p} ORDER BY updated_at DESC", pp),
            "specs": db.backend.fetchall(f"SELECT * FROM specs WHERE project={p} ORDER BY updated_at DESC", pp),
            "features": db.backend.fetchall(f"SELECT * FROM features WHERE project={p} ORDER BY updated_at DESC", pp),
            "components": db.backend.fetchall(f"SELECT * FROM components WHERE project={p} ORDER BY name", pp),
            "people": db.backend.fetchall("SELECT * FROM people ORDER BY name"),
            "teams": db.backend.fetchall(f"SELECT * FROM teams WHERE project={p} OR project IS NULL ORDER BY name", pp),
            "plan_tasks": db.backend.fetchall(
                f"SELECT pt.* FROM plan_tasks pt JOIN plans pl ON pt.plan_id=pl.id WHERE pl.project={p} ORDER BY pt.position", pp),
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
            "plans": db.backend.fetchall("SELECT * FROM plans ORDER BY updated_at DESC"),
            "specs": db.backend.fetchall("SELECT * FROM specs ORDER BY updated_at DESC"),
            "features": db.backend.fetchall("SELECT * FROM features ORDER BY updated_at DESC"),
            "components": db.backend.fetchall("SELECT * FROM components ORDER BY name"),
            "people": db.backend.fetchall("SELECT * FROM people ORDER BY name"),
            "teams": db.backend.fetchall("SELECT * FROM teams ORDER BY name"),
            "plan_tasks": db.backend.fetchall("SELECT * FROM plan_tasks ORDER BY position"),
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

    for sub in ("sessions", "thoughts", "rules", "errors", "groups", "projects",
                "plans", "specs", "features", "components", "people", "teams"):
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
    plans = data.get("plans", [])
    plan_tasks = data.get("plan_tasks", [])
    specs = data.get("specs", [])
    features = data.get("features", [])
    components = data.get("components", [])
    people = data.get("people", [])
    teams_data = data.get("teams", [])
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums, plans, specs, features, components, teams_data)
    slug_maps = _build_slug_maps(data, all_projects)
    thought_slugs = slug_maps["thoughts"]
    rule_slugs = slug_maps["rules"]
    error_slugs = slug_maps["errors"]
    session_slugs = slug_maps["sessions"]
    group_slugs = slug_maps["groups"]
    project_slugs = slug_maps["projects"]
    plan_slugs = slug_maps["plans"]
    spec_slugs = slug_maps["specs"]
    feature_slugs = slug_maps["features"]
    component_slugs = slug_maps["components"]
    people_slugs = slug_maps["people"]
    team_slugs = slug_maps["teams"]

    # Build task lookup by plan_id
    tasks_by_plan: dict[str, list] = {}
    for t in plan_tasks:
        tasks_by_plan.setdefault(t["plan_id"], []).append(t)

    # ── Index ───────────────────────────────────────────────────────────

    idx = ["# Memgram Export\n"]
    idx.append(f"| Item | Count |")
    idx.append(f"|------|-------|")
    idx.append(f"| Sessions | {len(sessions)} |")
    idx.append(f"| Thoughts | {len(thoughts)} |")
    idx.append(f"| Rules | {len(rules)} |")
    idx.append(f"| Error Patterns | {len(errors)} |")
    idx.append(f"| Groups | {len(groups)} |")
    idx.append(f"| Plans | {len(plans)} |")
    idx.append(f"| Specs | {len(specs)} |")
    idx.append(f"| Features | {len(features)} |")
    idx.append(f"| Components | {len(components)} |")
    idx.append(f"| People | {len(people)} |")
    idx.append(f"| Teams | {len(teams_data)} |")
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
        if t.get("agent_type"):
            lines.append(f"| Agent | {t['agent_type']} |")
        if t.get("agent_model"):
            lines.append(f"| Model | {t['agent_model']} |")
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
        if r.get("agent_type"):
            lines.append(f"| Agent | {r['agent_type']} |")
        if r.get("agent_model"):
            lines.append(f"| Model | {r['agent_model']} |")
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
        if e.get("agent_type"):
            lines.append(f"| Agent | {e['agent_type']} |")
        if e.get("agent_model"):
            lines.append(f"| Model | {e['agent_model']} |")
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

    # ── Plans ──────────────────────────────────────────────────────────

    for pl in plans:
        pl_slug = plan_slugs.get(pl["id"], pl["id"])
        lines = [f"# Plan: {pl['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{pl['id']}` |")
        lines.append(f"| Status | {pl['status']} |")
        lines.append(f"| Scope | {pl['scope']} |")
        lines.append(f"| Priority | {pl['priority']} |")
        lines.append(f"| Project | {pl.get('project') or '-'} |")
        lines.append(f"| Branch | {pl.get('branch') or '-'} |")
        lines.append(f"| Due | {pl.get('due_date') or '-'} |")
        lines.append(f"| Progress | {pl['completed_tasks']}/{pl['total_tasks']} tasks |")
        lines.append(f"| Created | {pl['created_at']} |")
        tags = _json_list(pl.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if pl.get("description"):
            lines.append(f"## Description\n\n{pl['description']}\n")
        ptasks = tasks_by_plan.get(pl["id"], [])
        if ptasks:
            lines.append("## Tasks\n")
            for t in sorted(ptasks, key=lambda x: x["position"]):
                status_icon = {"completed": "- [x]", "in_progress": "- [~]", "skipped": "- [-]", "blocked": "- [!]"}.get(t["status"], "- [ ]")
                assignee = f" @{t['assignee']}" if t.get("assignee") else ""
                lines.append(f"{status_icon} **{t['title']}**{assignee}")
                if t.get("description"):
                    lines.append(f"  {t['description']}")
            lines.append("")
        (out / "plans" / f"{pl_slug}.md").write_text("\n".join(lines))

    # ── Specs ──────────────────────────────────────────────────────────

    for sp in specs:
        sp_slug = spec_slugs.get(sp["id"], sp["id"])
        lines = [f"# Spec: {sp['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{sp['id']}` |")
        lines.append(f"| Status | {sp['status']} |")
        lines.append(f"| Priority | {sp['priority']} |")
        lines.append(f"| Project | {sp.get('project') or '-'} |")
        if sp.get("author_id"):
            author_slug = people_slugs.get(sp["author_id"], sp["author_id"])
            lines.append(f"| Author | [{sp['author_id']}](../people/{author_slug}.md) |")
        lines.append(f"| Created | {sp['created_at']} |")
        tags = _json_list(sp.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if sp.get("description"):
            lines.append(f"## Description\n\n{sp['description']}\n")
        ac = _json_list(sp.get("acceptance_criteria"))
        if ac:
            lines.append("## Acceptance Criteria\n")
            lines.append(_bullet_list(ac))
        # Linked features
        spec_features = [f for f in features if f.get("spec_id") == sp["id"]]
        if spec_features:
            lines.append("## Features\n")
            for f in spec_features:
                f_slug = feature_slugs.get(f["id"], f["id"])
                lines.append(f"- [{f['name']}](../features/{f_slug}.md) — {f['status']}")
            lines.append("")
        (out / "specs" / f"{sp_slug}.md").write_text("\n".join(lines))

    # ── Features ───────────────────────────────────────────────────────

    for ft in features:
        ft_slug = feature_slugs.get(ft["id"], ft["id"])
        lines = [f"# Feature: {ft['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{ft['id']}` |")
        lines.append(f"| Status | {ft['status']} |")
        lines.append(f"| Priority | {ft['priority']} |")
        lines.append(f"| Project | {ft.get('project') or '-'} |")
        if ft.get("spec_id"):
            sp_slug = spec_slugs.get(ft["spec_id"], ft["spec_id"])
            lines.append(f"| Spec | [{ft['spec_id']}](../specs/{sp_slug}.md) |")
        if ft.get("lead_id"):
            lead_slug = people_slugs.get(ft["lead_id"], ft["lead_id"])
            lines.append(f"| Lead | [{ft['lead_id']}](../people/{lead_slug}.md) |")
        lines.append(f"| Created | {ft['created_at']} |")
        tags = _json_list(ft.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if ft.get("description"):
            lines.append(f"## Description\n\n{ft['description']}\n")
        # Related links
        ft_links = [l for l in links if l["from_id"] == ft["id"] or l["to_id"] == ft["id"]]
        if ft_links:
            lines.append("## Related\n")
            for l in ft_links:
                other_id = l["to_id"] if l["from_id"] == ft["id"] else l["from_id"]
                other_type = l["to_type"] if l["from_id"] == ft["id"] else l["from_type"]
                lines.append(f"- {l['link_type']} → [{other_type}] `{other_id}`")
            lines.append("")
        (out / "features" / f"{ft_slug}.md").write_text("\n".join(lines))

    # ── Components ─────────────────────────────────────────────────────

    for cp in components:
        cp_slug = component_slugs.get(cp["id"], cp["id"])
        lines = [f"# Component: {cp['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{cp['id']}` |")
        lines.append(f"| Type | {cp['type']} |")
        lines.append(f"| Project | {cp.get('project') or '-'} |")
        if cp.get("owner_id"):
            owner_slug = people_slugs.get(cp["owner_id"], cp["owner_id"])
            lines.append(f"| Owner | [{cp['owner_id']}](../people/{owner_slug}.md) |")
        ts = _json_list(cp.get("tech_stack"))
        if ts:
            lines.append(f"| Tech Stack | {', '.join(ts)} |")
        lines.append(f"| Created | {cp['created_at']} |")
        tags = _json_list(cp.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if cp.get("description"):
            lines.append(f"## Description\n\n{cp['description']}\n")
        (out / "components" / f"{cp_slug}.md").write_text("\n".join(lines))

    # ── People ─────────────────────────────────────────────────────────

    for pr in people:
        pr_slug = people_slugs.get(pr["id"], pr["id"])
        lines = [f"# {pr['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{pr['id']}` |")
        lines.append(f"| Type | {pr.get('type', 'individual')} |")
        lines.append(f"| Role | {pr.get('role') or '-'} |")
        if pr.get("email"):
            lines.append(f"| Email | {pr['email']} |")
        if pr.get("github"):
            lines.append(f"| GitHub | {pr['github']} |")
        sk = _json_list(pr.get("skills"))
        if sk:
            lines.append(f"| Skills | {', '.join(sk)} |")
        lines.append("")
        if pr.get("notes"):
            lines.append(f"{pr['notes']}\n")
        # Owned components
        owned = [c for c in components if c.get("owner_id") == pr["id"]]
        if owned:
            lines.append("## Owned Components\n")
            for c in owned:
                c_slug = component_slugs.get(c["id"], c["id"])
                lines.append(f"- [{c['name']}](../components/{c_slug}.md) ({c['type']})")
            lines.append("")
        # Led features
        led = [f for f in features if f.get("lead_id") == pr["id"]]
        if led:
            lines.append("## Led Features\n")
            for f in led:
                f_slug = feature_slugs.get(f["id"], f["id"])
                lines.append(f"- [{f['name']}](../features/{f_slug}.md) — {f['status']}")
            lines.append("")
        # Authored specs
        authored = [s for s in specs if s.get("author_id") == pr["id"]]
        if authored:
            lines.append("## Authored Specs\n")
            for s in authored:
                s_slug = spec_slugs.get(s["id"], s["id"])
                lines.append(f"- [{s['title']}](../specs/{s_slug}.md) — {s['status']}")
            lines.append("")
        # Team memberships
        person_teams = db.backend.fetchall(
            f"SELECT t.*, tm.role AS member_role FROM team_members tm JOIN teams t ON tm.team_id=t.id WHERE tm.person_id={p}",
            (pr["id"],),
        )
        if person_teams:
            lines.append("## Teams\n")
            for t in person_teams:
                t_slug = team_slugs.get(t["id"], t["id"])
                lines.append(f"- [{t['name']}](../teams/{t_slug}.md) ({t['member_role']})")
            lines.append("")
        (out / "people" / f"{pr_slug}.md").write_text("\n".join(lines))

    # ── Teams ──────────────────────────────────────────────────────────

    for tm in teams_data:
        tm_slug = team_slugs.get(tm["id"], tm["id"])
        members = db.backend.fetchall(
            f"SELECT p.*, tmm.role AS member_role FROM team_members tmm JOIN people p ON tmm.person_id=p.id WHERE tmm.team_id={p}",
            (tm["id"],),
        )
        lines = [f"# Team: {tm['name']}\n"]
        if tm.get("description"):
            lines.append(f"{tm['description']}\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{tm['id']}` |")
        lines.append(f"| Project | {tm.get('project') or '-'} |")
        lines.append(f"| Members | {len(members)} |")
        if tm.get("lead_id"):
            lead_slug = people_slugs.get(tm["lead_id"], tm["lead_id"])
            lines.append(f"| Lead | [{tm['lead_id']}](../people/{lead_slug}.md) |")
        tags = _json_list(tm.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if members:
            lines.append("## Members\n")
            lines.append("| Name | Type | Role | Team Role |")
            lines.append("|------|------|------|-----------|")
            for m in members:
                m_slug = people_slugs.get(m["id"], m["id"])
                lines.append(f"| [{m['name']}](../people/{m_slug}.md) | {m.get('type', 'individual')} | {m.get('role', '-')} | {m['member_role']} |")
            lines.append("")
        (out / "teams" / f"{tm_slug}.md").write_text("\n".join(lines))

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

        # Project specs
        proj_specs = [s for s in specs if s.get("project") == proj]
        if proj_specs:
            lines.append("## Specs\n")
            for s in proj_specs:
                s_slug = spec_slugs.get(s["id"], s["id"])
                lines.append(f"- [{s['title']}](../specs/{s_slug}.md) — {s['status']}")
            lines.append("")

        # Project features
        proj_features = [f for f in features if f.get("project") == proj]
        if proj_features:
            lines.append("## Features\n")
            for f in proj_features:
                f_slug = feature_slugs.get(f["id"], f["id"])
                lines.append(f"- [{f['name']}](../features/{f_slug}.md) — {f['status']}")
            lines.append("")

        # Project components
        proj_components = [c for c in components if c.get("project") == proj]
        if proj_components:
            lines.append("## Components\n")
            for c in proj_components:
                c_slug = component_slugs.get(c["id"], c["id"])
                lines.append(f"- [{c['name']}](../components/{c_slug}.md) ({c['type']})")
            lines.append("")

        # Project plans
        proj_plans = [pl2 for pl2 in plans if pl2.get("project") == proj]
        if proj_plans:
            lines.append("## Plans\n")
            for pl2 in proj_plans:
                p_slug = plan_slugs.get(pl2["id"], pl2["id"])
                progress = f"{pl2['completed_tasks']}/{pl2['total_tasks']}"
                lines.append(f"- [{pl2['title']}](../plans/{p_slug}.md) — {pl2['status']} ({progress})")
            lines.append("")

        # Project teams
        proj_teams = [t for t in teams_data if t.get("project") == proj]
        if proj_teams:
            lines.append("## Teams\n")
            for t in proj_teams:
                t_slug = team_slugs.get(t["id"], t["id"])
                lines.append(f"- [{t['name']}](../teams/{t_slug}.md)")
            lines.append("")

        (out / "projects" / f"{proj_slug}.md").write_text("\n".join(lines))

    db.close()

    total = (len(sessions) + len(thoughts) + len(rules) + len(errors) + len(groups)
             + len(plans) + len(specs) + len(features) + len(components) + len(people)
             + len(teams_data) + len(all_projects) + 1)
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

    for sub in ("sessions", "thoughts", "rules", "errors", "groups", "projects",
                "plans", "specs", "features", "components", "people", "teams"):
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
    plans = data.get("plans", [])
    plan_tasks = data.get("plan_tasks", [])
    specs = data.get("specs", [])
    features = data.get("features", [])
    components = data.get("components", [])
    people = data.get("people", [])
    teams_data = data.get("teams", [])
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums, plans, specs, features, components, teams_data)
    slug_maps = _build_slug_maps(data, all_projects)
    thought_slugs = slug_maps["thoughts"]
    rule_slugs = slug_maps["rules"]
    error_slugs = slug_maps["errors"]
    session_slugs = slug_maps["sessions"]
    group_slugs = slug_maps["groups"]
    project_slugs = slug_maps["projects"]
    plan_slugs = slug_maps["plans"]
    spec_slugs = slug_maps["specs"]
    feature_slugs = slug_maps["features"]
    component_slugs = slug_maps["components"]
    people_slugs = slug_maps["people"]
    team_slugs = slug_maps["teams"]

    tasks_by_plan: dict[str, list] = {}
    for t in plan_tasks:
        tasks_by_plan.setdefault(t["plan_id"], []).append(t)

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
        "plans": ("Plans", 7),
        "specs": ("Specs", 8),
        "features": ("Features", 9),
        "components": ("Components", 10),
        "people": ("People", 11),
        "teams": ("Teams", 12),
        "projects": ("Projects", 13),
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
        if t.get("agent_type"):
            lines.append(f"| Agent | {t['agent_type']} |")
        if t.get("agent_model"):
            lines.append(f"| Model | {t['agent_model']} |")
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
        if r.get("agent_type"):
            lines.append(f"| Agent | {r['agent_type']} |")
        if r.get("agent_model"):
            lines.append(f"| Model | {r['agent_model']} |")
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
        if e.get("agent_type"):
            lines.append(f"| Agent | {e['agent_type']} |")
        if e.get("agent_model"):
            lines.append(f"| Model | {e['agent_model']} |")
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

        proj_specs = [s for s in specs if s.get("project") == proj]
        if proj_specs:
            lines.append("## Specs\n")
            for s in proj_specs:
                s_slug = spec_slugs.get(s["id"], s["id"])
                lines.append(f"- [{s['title']}](../specs/{s_slug}/) — {s['status']}")
            lines.append("")

        proj_features = [f for f in features if f.get("project") == proj]
        if proj_features:
            lines.append("## Features\n")
            for f in proj_features:
                f_slug = feature_slugs.get(f["id"], f["id"])
                lines.append(f"- [{f['name']}](../features/{f_slug}/) — {f['status']}")
            lines.append("")

        proj_components = [c for c in components if c.get("project") == proj]
        if proj_components:
            lines.append("## Components\n")
            for c in proj_components:
                c_slug = component_slugs.get(c["id"], c["id"])
                lines.append(f"- [{c['name']}](../components/{c_slug}/) ({c['type']})")
            lines.append("")

        proj_plans_j = [pl2 for pl2 in plans if pl2.get("project") == proj]
        if proj_plans_j:
            lines.append("## Plans\n")
            for pl2 in proj_plans_j:
                p_slug = plan_slugs.get(pl2["id"], pl2["id"])
                progress = f"{pl2['completed_tasks']}/{pl2['total_tasks']}"
                lines.append(f"- [{pl2['title']}](../plans/{p_slug}/) — {pl2['status']} ({progress})")
            lines.append("")

        proj_teams_j = [t for t in teams_data if t.get("project") == proj]
        if proj_teams_j:
            lines.append("## Teams\n")
            for t in proj_teams_j:
                t_slug = team_slugs.get(t["id"], t["id"])
                lines.append(f"- [{t['name']}](../teams/{t_slug}/)")
            lines.append("")

        (out / "projects" / f"{proj_slug}.md").write_text("\n".join(lines))

    db.close()

    total = (len(sessions) + len(thoughts) + len(rules) + len(errors) + len(groups)
             + len(plans) + len(specs) + len(features) + len(components) + len(people)
             + len(teams_data) + len(all_projects) + 1)
    return out, total


# ── Static HTML Export ─────────────────────────────────────────────────────


_HTML_CSS = """\
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #c9d1d9;
  --text-muted: #8b949e;
  --link: #58a6ff;
  --accent-green: #238636;
  --accent-red: #da3633;
  --accent-yellow: #d29922;
  --code-bg: #161b22;
  --code-text: #f0f6fc;
  --sidebar-w: 260px;
  --font: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --mono: ui-monospace, 'Cascadia Code', 'SF Mono', Menlo, monospace;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
}
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
code, pre {
  font-family: var(--mono);
  background: var(--code-bg);
  color: var(--code-text);
  border-radius: 4px;
}
code { padding: 2px 6px; font-size: 0.9em; }
pre { padding: 12px 16px; overflow-x: auto; border: 1px solid var(--border); margin: 12px 0; }

/* Layout */
.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: var(--sidebar-w);
  background: var(--surface);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  padding: 20px 0;
  z-index: 100;
}
.sidebar h2 {
  padding: 0 20px 12px;
  font-size: 1.1rem;
  color: var(--text);
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}
.sidebar .search-box {
  padding: 8px 16px;
}
.sidebar .search-box input {
  width: 100%;
  padding: 6px 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 0.85rem;
  outline: none;
}
.sidebar .search-box input:focus {
  border-color: var(--link);
}
.sidebar nav a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 20px;
  color: var(--text-muted);
  font-size: 0.9rem;
  transition: background 0.15s, color 0.15s;
}
.sidebar nav a:hover, .sidebar nav a.active {
  background: var(--bg);
  color: var(--text);
  text-decoration: none;
}
.sidebar nav a.active { border-left: 3px solid var(--link); padding-left: 17px; }
.sidebar .badge {
  background: var(--border);
  color: var(--text-muted);
  font-size: 0.75rem;
  padding: 1px 7px;
  border-radius: 10px;
}
.main {
  margin-left: var(--sidebar-w);
  padding: 24px 40px 60px;
  max-width: 1100px;
}
.breadcrumbs {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 16px;
}
.breadcrumbs a { color: var(--text-muted); }
.breadcrumbs a:hover { color: var(--link); }
.breadcrumbs .sep { margin: 0 6px; }

h1 { font-size: 1.8rem; margin-bottom: 16px; color: #e6edf3; }
h2 { font-size: 1.3rem; margin: 28px 0 12px; color: #e6edf3; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
h3 { font-size: 1.1rem; margin: 20px 0 8px; color: #e6edf3; }

/* Cards */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.stat-card .num { font-size: 1.8rem; font-weight: 700; color: var(--link); }
.stat-card .label { font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; }

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 0.9rem;
}
th, td {
  padding: 8px 12px;
  border: 1px solid var(--border);
  text-align: left;
}
th { background: var(--surface); color: var(--text-muted); font-weight: 600; }
tr:hover td { background: rgba(88,166,255,0.04); }

/* Tags / badges */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  margin: 2px 3px 2px 0;
  background: var(--border);
  color: var(--text-muted);
}
.tag.critical { background: rgba(218,54,51,0.2); color: #f85149; }
.tag.preference { background: rgba(210,153,34,0.2); color: #d29922; }
.tag.do { background: rgba(35,134,54,0.2); color: #3fb950; }
.tag.dont { background: rgba(218,54,51,0.2); color: #f85149; }
.tag.pinned { background: rgba(88,166,255,0.15); color: var(--link); }
.tag.archived { background: var(--border); color: var(--text-muted); }

/* Meta table (key-value) */
.meta-table { width: auto; min-width: 400px; }
.meta-table th { width: 140px; }

/* Content block (rendered markdown) */
.content-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin: 12px 0;
  word-break: break-word;
  font-size: 0.92rem;
  line-height: 1.6;
}
.content-block h1, .content-block h2, .content-block h3,
.content-block h4, .content-block h5, .content-block h6 {
  color: var(--text);
  margin-top: 1.2em;
  margin-bottom: 0.4em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.3em;
}
.content-block h1 { font-size: 1.4em; }
.content-block h2 { font-size: 1.2em; }
.content-block h3 { font-size: 1.1em; }
.content-block p { margin: 0.6em 0; }
.content-block ul, .content-block ol { padding-left: 1.5em; margin: 0.6em 0; }
.content-block li { margin: 0.3em 0; }
.content-block strong { color: #f0f6fc; }
.content-block em { color: #b1bac4; }
.content-block a { color: var(--link); }
/* Inline code */
.content-block code {
  background: #1c2129;
  color: #f0f6fc;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 0.88em;
}
/* Fenced code blocks */
.content-block pre {
  background: #0d1117;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px 16px;
  overflow-x: auto;
  margin: 0.8em 0;
}
.content-block pre code {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: 0.85em;
  line-height: 1.5;
  white-space: pre;
  color: #c9d1d9;
}
/* Tables inside content */
.content-block table {
  border-collapse: collapse;
  margin: 0.8em 0;
  width: 100%;
}
.content-block table th, .content-block table td {
  border: 1px solid var(--border);
  padding: 6px 10px;
  text-align: left;
}
.content-block table th {
  background: #1c2129;
}
.content-block blockquote {
  border-left: 3px solid var(--link);
  margin: 0.8em 0;
  padding: 0.4em 1em;
  color: #8b949e;
}
.content-block hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.2em 0;
}

/* Search results */
#search-results {
  display: none;
  margin-top: 12px;
}
#search-results.visible { display: block; }
#search-results .result-item {
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
}
#search-results .result-item a { font-weight: 500; }
#search-results .result-item .result-type {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-right: 6px;
}
#search-results .result-item .result-snippet {
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Responsive */
.sidebar-toggle {
  display: none;
  position: fixed; top: 10px; left: 10px;
  z-index: 200;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.2rem;
}
@media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); transition: transform 0.25s; }
  .sidebar.open { transform: translateX(0); }
  .sidebar-toggle { display: block; }
  .main { margin-left: 0; padding: 24px 16px 60px; }
}
"""

_HTML_SEARCH_JS = """\
(function() {
  var index = [];
  var input = document.getElementById('search-input');
  var resultsDiv = document.getElementById('search-results');
  if (!input || !resultsDiv) return;

  var base = document.documentElement.getAttribute('data-base') || '.';

  fetch(base + '/search-index.json')
    .then(function(r) { return r.json(); })
    .then(function(data) { index = data; });

  input.addEventListener('input', function() {
    var q = this.value.toLowerCase().trim();
    if (q.length < 2) {
      resultsDiv.className = '';
      resultsDiv.innerHTML = '';
      return;
    }
    var matches = [];
    for (var i = 0; i < index.length && matches.length < 30; i++) {
      var item = index[i];
      if ((item.title && item.title.toLowerCase().indexOf(q) >= 0) ||
          (item.content && item.content.toLowerCase().indexOf(q) >= 0) ||
          (item.keywords && item.keywords.join(' ').toLowerCase().indexOf(q) >= 0)) {
        matches.push(item);
      }
    }
    if (matches.length === 0) {
      resultsDiv.className = 'visible';
      resultsDiv.innerHTML = '<div class="result-item" style="color:var(--text-muted)">No results</div>';
      return;
    }
    var html = '';
    for (var j = 0; j < matches.length; j++) {
      var m = matches[j];
      var snippet = (m.content || '').substring(0, 120);
      html += '<div class="result-item">' +
        '<span class="result-type">' + m.type + '</span>' +
        '<a href="' + base + '/' + m.url + '">' + (m.title || m.id) + '</a>' +
        '<div class="result-snippet">' + snippet + '</div></div>';
    }
    resultsDiv.className = 'visible';
    resultsDiv.innerHTML = html;
  });
})();
"""


def _esc(text: Any) -> str:
    """HTML-escape user content."""
    return _html.escape(str(text)) if text is not None else ""


def _md(text: Any) -> str:
    """Render markdown text to HTML with fenced code blocks and tables."""
    if not text:
        return ""
    try:
        import markdown
        return markdown.markdown(
            str(text),
            extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
        )
    except ImportError:
        # Fallback: at least handle code blocks manually
        return _esc(text).replace("\n", "<br>")


def _html_page(
    title: str,
    content: str,
    breadcrumbs: list[tuple[str, str]],
    sidebar_counts: dict,
    active_section: str = "",
    depth: int = 0,
) -> str:
    """Generate a complete HTML page with sidebar, breadcrumbs, and content."""
    base = "/".join([".."] * depth) if depth > 0 else "."

    nav_items = [
        ("Home", "index.html", "home"),
        ("Sessions", "sessions/index.html", "sessions"),
        ("Thoughts", "thoughts/index.html", "thoughts"),
        ("Rules", "rules/index.html", "rules"),
        ("Errors", "errors/index.html", "errors"),
        ("Groups", "groups/index.html", "groups"),
        ("Plans", "plans/index.html", "plans"),
        ("Specs", "specs/index.html", "specs"),
        ("Features", "features/index.html", "features"),
        ("Components", "components/index.html", "components"),
        ("People", "people/index.html", "people"),
        ("Teams", "teams/index.html", "teams"),
        ("Projects", "projects/index.html", "projects"),
        ("Agents", "agents/index.html", "agents"),
    ]

    sidebar_html = []
    sidebar_html.append('<aside class="sidebar" id="sidebar">')
    sidebar_html.append(f'  <h2><a href="{base}/index.html" style="color:inherit;text-decoration:none">Memgram</a></h2>')
    sidebar_html.append('  <div class="search-box">')
    sidebar_html.append(f'    <input type="text" id="search-input" placeholder="Search...">')
    sidebar_html.append(f'    <div id="search-results"></div>')
    sidebar_html.append('  </div>')
    sidebar_html.append('  <nav>')
    for label, href, section_key in nav_items:
        active = ' class="active"' if section_key == active_section else ""
        count = sidebar_counts.get(section_key, 0)
        badge = f'<span class="badge">{count}</span>' if count else ""
        sidebar_html.append(f'    <a href="{base}/{href}"{active}>{_esc(label)}{badge}</a>')
    sidebar_html.append('  </nav>')
    sidebar_html.append('</aside>')

    bc_parts = []
    for bc_label, bc_href in breadcrumbs:
        if bc_href:
            bc_parts.append(f'<a href="{bc_href}">{_esc(bc_label)}</a>')
        else:
            bc_parts.append(_esc(bc_label))
    bc_html = '<span class="sep">/</span>'.join(bc_parts)

    return f"""<!DOCTYPE html>
<html lang="en" data-base="{base}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} - Memgram</title>
<link rel="stylesheet" href="{base}/style.css">
</head>
<body>
<button class="sidebar-toggle" onclick="document.getElementById('sidebar').classList.toggle('open')">&#9776;</button>
{"".join(sidebar_html)}
<div class="main">
<div class="breadcrumbs">{bc_html}</div>
{content}
</div>
<script src="{base}/search.js"></script>
</body>
</html>
"""


def _html_meta_table(rows: list[tuple[str, str]]) -> str:
    """Build an HTML key-value metadata table."""
    lines = ['<table class="meta-table">', "<thead><tr><th>Field</th><th>Value</th></tr></thead>", "<tbody>"]
    for label, value in rows:
        lines.append(f"<tr><td>{_esc(label)}</td><td>{value}</td></tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _html_tag(text: str, cls: str = "") -> str:
    """Render a small tag/badge span."""
    return f'<span class="tag {cls}">{_esc(text)}</span>'


def _html_keyword_tags(raw: str | None) -> str:
    """Render keywords as tag spans."""
    kw = _json_list(raw)
    if not kw:
        return ""
    return " ".join(_html_tag(k) for k in kw)


def export_html(
    db_path: Optional[str] = None,
    output_dir: str = "memgram-web",
    project: Optional[str] = None,
) -> tuple[Path, int]:
    """Export memgram database as a complete static HTML website.

    Generates a self-contained site with dark theme, sidebar navigation,
    client-side search, and cross-linked pages. No build step required.
    """
    out = Path(output_dir)
    db, data = _fetch_all_data(db_path, project=project)

    for sub in ("sessions", "thoughts", "rules", "errors", "groups", "projects", "agents",
                "plans", "specs", "features", "components", "people", "teams"):
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
    plans = data.get("plans", [])
    plan_tasks = data.get("plan_tasks", [])
    specs = data.get("specs", [])
    features = data.get("features", [])
    components = data.get("components", [])
    people = data.get("people", [])
    teams_data = data.get("teams", [])
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums, plans, specs, features, components, teams_data)
    slug_maps = _build_slug_maps(data, all_projects)
    thought_slugs = slug_maps["thoughts"]
    rule_slugs = slug_maps["rules"]
    error_slugs = slug_maps["errors"]
    session_slugs = slug_maps["sessions"]
    group_slugs = slug_maps["groups"]
    project_slugs = slug_maps["projects"]
    plan_slugs = slug_maps["plans"]
    spec_slugs = slug_maps["specs"]
    feature_slugs = slug_maps["features"]
    component_slugs = slug_maps["components"]
    people_slugs = slug_maps["people"]
    team_slugs = slug_maps["teams"]

    tasks_by_plan: dict[str, list] = {}
    for t in plan_tasks:
        tasks_by_plan.setdefault(t["plan_id"], []).append(t)

    file_count = 0

    # Sidebar counts
    # Collect unique agents for count
    agent_set: set[tuple[str, str]] = set()
    for s in sessions:
        agent_set.add((s.get("agent_type") or "unknown", s.get("model") or "unknown"))
    for t in thoughts:
        if t.get("agent_type"):
            agent_set.add((t["agent_type"], t.get("agent_model") or "unknown"))
    for r in rules:
        if r.get("agent_type"):
            agent_set.add((r["agent_type"], r.get("agent_model") or "unknown"))
    for e in errors:
        if e.get("agent_type"):
            agent_set.add((e["agent_type"], e.get("agent_model") or "unknown"))

    sidebar_counts = {
        "sessions": len(sessions),
        "thoughts": len(thoughts),
        "rules": len(rules),
        "errors": len(errors),
        "groups": len(groups),
        "plans": len(plans),
        "specs": len(specs),
        "features": len(features),
        "components": len(components),
        "people": len(people),
        "teams": len(teams_data),
        "projects": len(all_projects),
        "agents": len(agent_set),
    }

    # ── Write CSS & JS ─────────────────────────────────────────────────
    (out / "style.css").write_text(_HTML_CSS)
    file_count += 1
    (out / "search.js").write_text(_HTML_SEARCH_JS)
    file_count += 1

    # ── Agent stats (compute once, used in index + agents page) ────────
    agent_stats: dict[tuple[str, str], dict] = {}
    for s in sessions:
        key = (s.get("agent_type") or "unknown", s.get("model") or "unknown")
        rec = agent_stats.setdefault(key, {
            "agent_type": key[0], "model": key[1],
            "sessions": 0, "thoughts": 0, "rules": 0, "errors": 0,
            "first_seen": s.get("started_at") or "", "last_seen": s.get("started_at") or "",
        })
        rec["sessions"] += 1
        ts = s.get("started_at") or ""
        if ts and (not rec["first_seen"] or ts < rec["first_seen"]):
            rec["first_seen"] = ts
        if ts and (not rec["last_seen"] or ts > rec["last_seen"]):
            rec["last_seen"] = ts
    for t in thoughts:
        key = (t.get("agent_type") or "unknown", t.get("agent_model") or "unknown")
        rec = agent_stats.setdefault(key, {
            "agent_type": key[0], "model": key[1],
            "sessions": 0, "thoughts": 0, "rules": 0, "errors": 0,
            "first_seen": t.get("created_at") or "", "last_seen": t.get("created_at") or "",
        })
        rec["thoughts"] += 1
    for r in rules:
        key = (r.get("agent_type") or "unknown", r.get("agent_model") or "unknown")
        rec = agent_stats.setdefault(key, {
            "agent_type": key[0], "model": key[1],
            "sessions": 0, "thoughts": 0, "rules": 0, "errors": 0,
            "first_seen": r.get("created_at") or "", "last_seen": r.get("created_at") or "",
        })
        rec["rules"] += 1
    for e in errors:
        key = (e.get("agent_type") or "unknown", e.get("agent_model") or "unknown")
        rec = agent_stats.setdefault(key, {
            "agent_type": key[0], "model": key[1],
            "sessions": 0, "thoughts": 0, "rules": 0, "errors": 0,
            "first_seen": e.get("created_at") or "", "last_seen": e.get("created_at") or "",
        })
        rec["errors"] += 1

    # ── Index (Dashboard) ──────────────────────────────────────────────
    idx = []
    idx.append('<h1>Memgram Dashboard</h1>')
    idx.append('<div class="stats-grid">')
    for label, count, href in [
        ("Sessions", len(sessions), "sessions/index.html"),
        ("Thoughts", len(thoughts), "thoughts/index.html"),
        ("Rules", len(rules), "rules/index.html"),
        ("Errors", len(errors), "errors/index.html"),
        ("Agents", len(agent_set), "agents/index.html"),
    ]:
        idx.append(f'<a href="{href}" style="text-decoration:none"><div class="stat-card"><div class="num">{count}</div><div class="label">{_esc(label)}</div></div></a>')
    idx.append('</div>')

    # Agent breakdown
    if agent_stats:
        idx.append('<h2>Agent Breakdown</h2>')
        idx.append('<table><thead><tr><th>Agent</th><th>Model</th><th>Sessions</th><th>Thoughts</th><th>Rules</th><th>Errors</th><th>First Seen</th><th>Last Seen</th></tr></thead><tbody>')
        total_s = total_t = total_r = total_e = 0
        for _key, rec in sorted(agent_stats.items()):
            total_s += rec["sessions"]
            total_t += rec["thoughts"]
            total_r += rec["rules"]
            total_e += rec["errors"]
            idx.append(f'<tr><td>{_esc(rec["agent_type"])}</td><td>{_esc(rec["model"])}</td>'
                       f'<td>{rec["sessions"]}</td><td>{rec["thoughts"]}</td><td>{rec["rules"]}</td><td>{rec["errors"]}</td>'
                       f'<td>{_esc(rec["first_seen"][:10] if rec["first_seen"] else "-")}</td>'
                       f'<td>{_esc(rec["last_seen"][:10] if rec["last_seen"] else "-")}</td></tr>')
        idx.append(f'<tr style="font-weight:700"><td colspan="2">Totals</td>'
                   f'<td>{total_s}</td><td>{total_t}</td><td>{total_r}</td><td>{total_e}</td><td></td><td></td></tr>')
        idx.append('</tbody></table>')

    # Rules overview
    if rules:
        idx.append('<h2>Rules Overview</h2>')
        idx.append('<table><thead><tr><th>Severity</th><th>Type</th><th>Summary</th><th>Reinforced</th><th>Project</th></tr></thead><tbody>')
        for r in rules:
            r_slug = rule_slugs.get(r["id"], r["id"])
            sev_cls = r["severity"] if r["severity"] in ("critical", "preference") else ""
            pin = _html_tag("pinned", "pinned") + " " if r["pinned"] else ""
            arc = _html_tag("archived", "archived") + " " if r["archived"] else ""
            idx.append(f'<tr><td>{_html_tag(r["severity"], sev_cls)}</td><td>{_html_tag(r["type"], r["type"])}</td>'
                       f'<td>{arc}{pin}<a href="rules/{r_slug}.html">{_esc(r["summary"])}</a></td>'
                       f'<td>&times;{r["reinforcement_count"]}</td>'
                       f'<td>{_esc(r.get("project") or "global")}</td></tr>')
        idx.append('</tbody></table>')

    # Recent sessions
    if sessions:
        idx.append('<h2>Recent Sessions</h2>')
        idx.append('<table><thead><tr><th>Date</th><th>Agent</th><th>Model</th><th>Project</th><th>Goal</th><th>Status</th></tr></thead><tbody>')
        for s in sessions[:20]:
            date = (s.get("started_at") or "")[:10]
            sess_slug = session_slugs.get(s["id"], s["id"])
            idx.append(f'<tr><td>{_esc(date)}</td><td>{_esc(s["agent_type"])}</td><td>{_esc(s["model"])}</td>'
                       f'<td>{_esc(s.get("project") or "-")}</td>'
                       f'<td><a href="sessions/{sess_slug}.html">{_esc(s.get("goal") or "-")}</a></td>'
                       f'<td>{_esc(s["status"])}</td></tr>')
        idx.append('</tbody></table>')

    # Projects list
    if all_projects:
        idx.append('<h2>Projects</h2>')
        idx.append('<ul>')
        for proj in sorted(all_projects):
            proj_slug = project_slugs.get(proj, proj)
            idx.append(f'<li><a href="projects/{proj_slug}.html">{_esc(proj)}</a></li>')
        idx.append('</ul>')

    index_page = _html_page(
        "Dashboard", "\n".join(idx),
        breadcrumbs=[("Home", "")],
        sidebar_counts=sidebar_counts,
        active_section="home", depth=0,
    )
    (out / "index.html").write_text(index_page, encoding="utf-8")
    file_count += 1

    # ── Sessions ───────────────────────────────────────────────────────

    ss_by_id = {s["session_id"]: s for s in session_sums}
    snap_by_session: dict[str, list] = {}
    for snap in snapshots:
        snap_by_session.setdefault(snap["session_id"], []).append(snap)

    # Sessions index
    si = ['<h1>Sessions</h1>']
    si.append('<table><thead><tr><th>Date</th><th>Agent</th><th>Model</th><th>Project</th><th>Goal</th><th>Status</th><th>Compactions</th></tr></thead><tbody>')
    for s in sessions:
        date = (s.get("started_at") or "")[:10]
        sess_slug = session_slugs.get(s["id"], s["id"])
        si.append(f'<tr><td>{_esc(date)}</td><td>{_esc(s["agent_type"])}</td><td>{_esc(s["model"])}</td>'
                  f'<td>{_esc(s.get("project") or "-")}</td>'
                  f'<td><a href="{sess_slug}.html">{_esc(s.get("goal") or "-")}</a></td>'
                  f'<td>{_esc(s["status"])}</td><td>{s["compaction_count"]}</td></tr>')
    si.append('</tbody></table>')
    page = _html_page("Sessions", "\n".join(si),
                      breadcrumbs=[("Home", "../index.html"), ("Sessions", "")],
                      sidebar_counts=sidebar_counts, active_section="sessions", depth=1)
    (out / "sessions" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    # Individual sessions
    for s in sessions:
        sess_slug = session_slugs.get(s["id"], s["id"])
        h = [f'<h1>Session: {_esc(s.get("goal") or s["id"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(s["id"])}</code>'),
            ("Agent", _esc(s["agent_type"])),
            ("Model", _esc(s["model"])),
            ("Project", _esc(s.get("project") or "-")),
            ("Branch", _esc(s.get("branch") or "-")),
            ("Status", _esc(s["status"])),
            ("Started", _esc(s.get("started_at") or "-")),
            ("Ended", _esc(s.get("ended_at") or "-")),
            ("Compactions", str(s["compaction_count"])),
        ]
        h.append(_html_meta_table(meta))

        if s.get("summary"):
            h.append(f'<h2>Summary</h2><div class="content-block">{_md(s["summary"])}</div>')

        ss = ss_by_id.get(s["id"])
        if ss:
            h.append('<h2>Session Summary</h2>')
            if ss.get("outcome"):
                h.append(f'<p><strong>Outcome:</strong> {_esc(ss["outcome"])}</p>')
            decisions = _json_list(ss.get("decisions_made"))
            if decisions:
                h.append('<p><strong>Decisions:</strong></p><ul>' + "".join(f"<li>{_esc(d)}</li>" for d in decisions) + "</ul>")
            files = _json_list(ss.get("files_modified"))
            if files:
                h.append('<p><strong>Files Modified:</strong></p><ul>' + "".join(f"<li><code>{_esc(f)}</code></li>" for f in files) + "</ul>")
            unresolved = _json_list(ss.get("unresolved_items"))
            if unresolved:
                h.append('<p><strong>Unresolved:</strong></p><ul>' + "".join(f"<li>{_esc(u)}</li>" for u in unresolved) + "</ul>")
            if ss.get("next_session_hints"):
                h.append(f'<p><strong>Next Session Hints:</strong> {_esc(ss["next_session_hints"])}</p>')

        snaps = snap_by_session.get(s["id"], [])
        if snaps:
            h.append('<h2>Compaction Snapshots</h2>')
            for snap in sorted(snaps, key=lambda x: x["sequence_num"]):
                h.append(f'<h3>Snapshot #{snap["sequence_num"]} ({_esc(snap["created_at"][:19])})</h3>')
                if snap.get("current_goal"):
                    h.append(f'<p><strong>Goal:</strong> {_esc(snap["current_goal"])}</p>')
                if snap.get("progress_summary"):
                    h.append(f'<p><strong>Progress:</strong> {_esc(snap["progress_summary"])}</p>')
                ns = _json_list(snap.get("next_steps"))
                if ns:
                    h.append('<p><strong>Next Steps:</strong></p><ul>' + "".join(f"<li>{_esc(n)}</li>" for n in ns) + "</ul>")
                bl = _json_list(snap.get("blockers"))
                if bl:
                    h.append('<p><strong>Blockers:</strong></p><ul>' + "".join(f"<li>{_esc(b)}</li>" for b in bl) + "</ul>")
                oq = _json_list(snap.get("open_questions"))
                if oq:
                    h.append('<p><strong>Open Questions:</strong></p><ul>' + "".join(f"<li>{_esc(q)}</li>" for q in oq) + "</ul>")

        page = _html_page(
            f"Session: {s.get('goal') or s['id']}", "\n".join(h),
            breadcrumbs=[("Home", "../index.html"), ("Sessions", "index.html"), (s.get("goal") or s["id"][:12], "")],
            sidebar_counts=sidebar_counts, active_section="sessions", depth=1,
        )
        (out / "sessions" / f"{sess_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Thoughts ───────────────────────────────────────────────────────

    # Thoughts index
    ti = ['<h1>Thoughts</h1>']
    ti.append('<table><thead><tr><th>Type</th><th>Summary</th><th>Project</th><th>Agent</th><th>Created</th><th>Accessed</th></tr></thead><tbody>')
    for t in thoughts:
        t_slug = thought_slugs.get(t["id"], t["id"])
        pin = _html_tag("pinned", "pinned") + " " if t["pinned"] else ""
        ti.append(f'<tr><td>{_esc(t["type"])}</td>'
                  f'<td>{pin}<a href="{t_slug}.html">{_esc(t["summary"])}</a></td>'
                  f'<td>{_esc(t.get("project") or "-")}</td>'
                  f'<td>{_esc(t.get("agent_type") or "-")}</td>'
                  f'<td>{_esc((t["created_at"] or "")[:10])}</td>'
                  f'<td>{t["access_count"]}</td></tr>')
    ti.append('</tbody></table>')
    page = _html_page("Thoughts", "\n".join(ti),
                      breadcrumbs=[("Home", "../index.html"), ("Thoughts", "")],
                      sidebar_counts=sidebar_counts, active_section="thoughts", depth=1)
    (out / "thoughts" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    # Individual thoughts
    for t in thoughts:
        t_slug = thought_slugs.get(t["id"], t["id"])
        h = [f'<h1>{_esc(t["summary"])}</h1>']
        tags = []
        if t["pinned"]:
            tags.append(_html_tag("pinned", "pinned"))
        if t["archived"]:
            tags.append(_html_tag("archived", "archived"))
        if tags:
            h.append('<div style="margin-bottom:12px">' + " ".join(tags) + "</div>")

        meta = [
            ("ID", f'<code>{_esc(t["id"])}</code>'),
            ("Type", _esc(t["type"])),
            ("Project", _esc(t.get("project") or "-")),
            ("Branch", _esc(t.get("branch") or "-")),
            ("Created", _esc(t["created_at"])),
            ("Accessed", f'{t["access_count"]} times'),
        ]
        if t.get("agent_type"):
            meta.append(("Agent", _esc(t["agent_type"])))
        if t.get("agent_model"):
            meta.append(("Model", _esc(t["agent_model"])))
        kw_html = _html_keyword_tags(t.get("keywords"))
        if kw_html:
            meta.append(("Keywords", kw_html))
        files = _json_list(t.get("associated_files"))
        if files:
            meta.append(("Files", ", ".join(f"<code>{_esc(f)}</code>" for f in files)))
        if t.get("session_id"):
            sess_slug = session_slugs.get(str(t["session_id"]), str(t["session_id"]))
            meta.append(("Session", f'<a href="../sessions/{sess_slug}.html">{_esc(t["session_id"])}</a>'))
        h.append(_html_meta_table(meta))

        if t.get("content"):
            h.append(f'<h2>Content</h2><div class="content-block">{_md(t["content"])}</div>')

        page = _html_page(
            t["summary"], "\n".join(h),
            breadcrumbs=[("Home", "../index.html"), ("Thoughts", "index.html"), (t["summary"][:50], "")],
            sidebar_counts=sidebar_counts, active_section="thoughts", depth=1,
        )
        (out / "thoughts" / f"{t_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Rules ──────────────────────────────────────────────────────────

    # Rules index
    ri = ['<h1>Rules</h1>']
    ri.append('<table><thead><tr><th>Severity</th><th>Type</th><th>Summary</th><th>Reinforced</th><th>Project</th></tr></thead><tbody>')
    for r in rules:
        r_slug = rule_slugs.get(r["id"], r["id"])
        sev_cls = r["severity"] if r["severity"] in ("critical", "preference") else ""
        pin = _html_tag("pinned", "pinned") + " " if r["pinned"] else ""
        ri.append(f'<tr><td>{_html_tag(r["severity"], sev_cls)}</td><td>{_html_tag(r["type"], r["type"])}</td>'
                  f'<td>{pin}<a href="{r_slug}.html">{_esc(r["summary"])}</a></td>'
                  f'<td>&times;{r["reinforcement_count"]}</td>'
                  f'<td>{_esc(r.get("project") or "global")}</td></tr>')
    ri.append('</tbody></table>')
    page = _html_page("Rules", "\n".join(ri),
                      breadcrumbs=[("Home", "../index.html"), ("Rules", "")],
                      sidebar_counts=sidebar_counts, active_section="rules", depth=1)
    (out / "rules" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    # Individual rules
    for r in rules:
        r_slug = rule_slugs.get(r["id"], r["id"])
        h = [f'<h1>{_esc(r["summary"])}</h1>']
        tags = []
        if r["pinned"]:
            tags.append(_html_tag("pinned", "pinned"))
        if r["archived"]:
            tags.append(_html_tag("archived", "archived"))
        sev_cls = r["severity"] if r["severity"] in ("critical", "preference") else ""
        tags.append(_html_tag(r["severity"], sev_cls))
        tags.append(_html_tag(r["type"], r["type"]))
        h.append('<div style="margin-bottom:12px">' + " ".join(tags) + "</div>")

        meta = [
            ("ID", f'<code>{_esc(r["id"])}</code>'),
            ("Reinforced", f'&times;{r["reinforcement_count"]}'),
            ("Project", _esc(r.get("project") or "global")),
            ("Branch", _esc(r.get("branch") or "-")),
            ("Created", _esc(r["created_at"])),
        ]
        if r.get("agent_type"):
            meta.append(("Agent", _esc(r["agent_type"])))
        if r.get("agent_model"):
            meta.append(("Model", _esc(r["agent_model"])))
        if r.get("condition"):
            meta.append(("Condition", _esc(r["condition"])))
        kw_html = _html_keyword_tags(r.get("keywords"))
        if kw_html:
            meta.append(("Keywords", kw_html))
        files = _json_list(r.get("associated_files"))
        if files:
            meta.append(("Files", ", ".join(f"<code>{_esc(f)}</code>" for f in files)))
        if r.get("session_id"):
            sess_slug = session_slugs.get(str(r["session_id"]), str(r["session_id"]))
            meta.append(("Session", f'<a href="../sessions/{sess_slug}.html">{_esc(r["session_id"])}</a>'))
        h.append(_html_meta_table(meta))

        if r.get("content"):
            h.append(f'<h2>Details</h2><div class="content-block">{_md(r["content"])}</div>')

        page = _html_page(
            r["summary"], "\n".join(h),
            breadcrumbs=[("Home", "../index.html"), ("Rules", "index.html"), (r["summary"][:50], "")],
            sidebar_counts=sidebar_counts, active_section="rules", depth=1,
        )
        (out / "rules" / f"{r_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Errors ─────────────────────────────────────────────────────────

    # Errors index
    ei = ['<h1>Error Patterns</h1>']
    ei.append('<table><thead><tr><th>Description</th><th>Project</th><th>Agent</th><th>Created</th><th>Prevention Rule</th></tr></thead><tbody>')
    for e in errors:
        e_slug = error_slugs.get(e["id"], e["id"])
        rule_link = "-"
        if e.get("prevention_rule_id"):
            rs = rule_slugs.get(str(e["prevention_rule_id"]), str(e["prevention_rule_id"]))
            rule_link = f'<a href="../rules/{rs}.html">View</a>'
        ei.append(f'<tr><td><a href="{e_slug}.html">{_esc(e["error_description"][:80])}</a></td>'
                  f'<td>{_esc(e.get("project") or "-")}</td>'
                  f'<td>{_esc(e.get("agent_type") or "-")}</td>'
                  f'<td>{_esc((e["created_at"] or "")[:10])}</td>'
                  f'<td>{rule_link}</td></tr>')
    ei.append('</tbody></table>')
    page = _html_page("Error Patterns", "\n".join(ei),
                      breadcrumbs=[("Home", "../index.html"), ("Errors", "")],
                      sidebar_counts=sidebar_counts, active_section="errors", depth=1)
    (out / "errors" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    # Individual errors
    for e in errors:
        e_slug = error_slugs.get(e["id"], e["id"])
        h = [f'<h1>Error: {_esc(e["error_description"][:80])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(e["id"])}</code>'),
            ("Project", _esc(e.get("project") or "-")),
            ("Branch", _esc(e.get("branch") or "-")),
            ("Created", _esc(e["created_at"])),
        ]
        if e.get("agent_type"):
            meta.append(("Agent", _esc(e["agent_type"])))
        if e.get("agent_model"):
            meta.append(("Model", _esc(e["agent_model"])))
        kw_html = _html_keyword_tags(e.get("keywords"))
        if kw_html:
            meta.append(("Keywords", kw_html))
        files = _json_list(e.get("associated_files"))
        if files:
            meta.append(("Files", ", ".join(f"<code>{_esc(f)}</code>" for f in files)))
        if e.get("prevention_rule_id"):
            rs = rule_slugs.get(str(e["prevention_rule_id"]), str(e["prevention_rule_id"]))
            meta.append(("Prevention Rule", f'<a href="../rules/{rs}.html">{_esc(e["prevention_rule_id"])}</a>'))
        if e.get("session_id"):
            sess_slug = session_slugs.get(str(e["session_id"]), str(e["session_id"]))
            meta.append(("Session", f'<a href="../sessions/{sess_slug}.html">{_esc(e["session_id"])}</a>'))
        h.append(_html_meta_table(meta))

        h.append(f'<h2>Error</h2><div class="content-block">{_md(e["error_description"])}</div>')
        if e.get("cause"):
            h.append(f'<h2>Cause</h2><div class="content-block">{_md(e["cause"])}</div>')
        if e.get("fix"):
            h.append(f'<h2>Fix</h2><div class="content-block">{_md(e["fix"])}</div>')

        page = _html_page(
            f"Error: {e['error_description'][:60]}", "\n".join(h),
            breadcrumbs=[("Home", "../index.html"), ("Errors", "index.html"), (e["error_description"][:40], "")],
            sidebar_counts=sidebar_counts, active_section="errors", depth=1,
        )
        (out / "errors" / f"{e_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Groups ─────────────────────────────────────────────────────────

    # Groups index
    gi = ['<h1>Groups</h1>']
    gi.append('<table><thead><tr><th>Name</th><th>Project</th><th>Description</th><th>Updated</th></tr></thead><tbody>')
    for g in groups:
        g_slug = group_slugs.get(g["id"], g["id"])
        gi.append(f'<tr><td><a href="{g_slug}.html">{_esc(g["name"])}</a></td>'
                  f'<td>{_esc(g.get("project") or "-")}</td>'
                  f'<td>{_esc((g.get("description") or "-")[:80])}</td>'
                  f'<td>{_esc((g["updated_at"] or "")[:10])}</td></tr>')
    gi.append('</tbody></table>')
    page = _html_page("Groups", "\n".join(gi),
                      breadcrumbs=[("Home", "../index.html"), ("Groups", "")],
                      sidebar_counts=sidebar_counts, active_section="groups", depth=1)
    (out / "groups" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    # Individual groups
    for g in groups:
        g_slug = group_slugs.get(g["id"], g["id"])
        members = db.backend.fetchall(
            f"SELECT * FROM group_members WHERE group_id={p}", (g["id"],),
        )
        h = [f'<h1>Group: {_esc(g["name"])}</h1>']
        if g.get("description"):
            h.append(f'<p>{_esc(g["description"])}</p>')
        meta = [
            ("ID", f'<code>{_esc(g["id"])}</code>'),
            ("Project", _esc(g.get("project") or "-")),
            ("Branch", _esc(g.get("branch") or "-")),
            ("Members", str(len(members))),
            ("Updated", _esc(g["updated_at"])),
        ]
        h.append(_html_meta_table(meta))

        if members:
            h.append('<h2>Members</h2><ul>')
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
                h.append(f'<li>{_html_tag(m["item_type"])} <a href="../{d}/{item_slug}.html">{_esc(summary)}</a></li>')
            h.append('</ul>')

        page = _html_page(
            f"Group: {g['name']}", "\n".join(h),
            breadcrumbs=[("Home", "../index.html"), ("Groups", "index.html"), (g["name"][:40], "")],
            sidebar_counts=sidebar_counts, active_section="groups", depth=1,
        )
        (out / "groups" / f"{g_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Plans ──────────────────────────────────────────────────────────

    pli = ['<h1>Plans</h1>']
    pli.append('<table><thead><tr><th>Title</th><th>Status</th><th>Priority</th><th>Scope</th><th>Progress</th><th>Project</th><th>Due</th></tr></thead><tbody>')
    for pl in plans:
        pl_slug = plan_slugs.get(pl["id"], pl["id"])
        progress = f'{pl["completed_tasks"]}/{pl["total_tasks"]}'
        pli.append(f'<tr><td><a href="{pl_slug}.html">{_esc(pl["title"])}</a></td>'
                   f'<td>{_html_tag(pl["status"])}</td><td>{_html_tag(pl["priority"], pl["priority"])}</td>'
                   f'<td>{_esc(pl["scope"])}</td><td>{_esc(progress)}</td>'
                   f'<td>{_esc(pl.get("project") or "-")}</td><td>{_esc(pl.get("due_date") or "-")}</td></tr>')
    pli.append('</tbody></table>')
    page = _html_page("Plans", "\n".join(pli),
                      breadcrumbs=[("Home", "../index.html"), ("Plans", "")],
                      sidebar_counts=sidebar_counts, active_section="plans", depth=1)
    (out / "plans" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for pl in plans:
        pl_slug = plan_slugs.get(pl["id"], pl["id"])
        h = [f'<h1>Plan: {_esc(pl["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(pl["id"])}</code>'),
            ("Status", _esc(pl["status"])),
            ("Scope", _esc(pl["scope"])),
            ("Priority", _esc(pl["priority"])),
            ("Project", _esc(pl.get("project") or "-")),
            ("Due", _esc(pl.get("due_date") or "-")),
            ("Progress", f'{pl["completed_tasks"]}/{pl["total_tasks"]} tasks'),
            ("Created", _esc(pl["created_at"])),
        ]
        tags = _json_list(pl.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if pl.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(pl["description"])}</div>')
        ptasks = tasks_by_plan.get(pl["id"], [])
        if ptasks:
            h.append('<h2>Tasks</h2><table><thead><tr><th>#</th><th>Task</th><th>Status</th><th>Assignee</th><th>Completed</th></tr></thead><tbody>')
            for t in sorted(ptasks, key=lambda x: x["position"]):
                status_cls = "do" if t["status"] == "completed" else ("dont" if t["status"] == "blocked" else "")
                h.append(f'<tr><td>{t["position"]}</td><td>{_esc(t["title"])}</td>'
                         f'<td>{_html_tag(t["status"], status_cls)}</td>'
                         f'<td>{_esc(t.get("assignee") or "-")}</td>'
                         f'<td>{_esc(t.get("completed_at") or "-")}</td></tr>')
            h.append('</tbody></table>')
        page = _html_page(f'Plan: {pl["title"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Plans", "index.html"), (pl["title"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="plans", depth=1)
        (out / "plans" / f"{pl_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Specs ──────────────────────────────────────────────────────────

    spi = ['<h1>Specs</h1>']
    spi.append('<table><thead><tr><th>Title</th><th>Status</th><th>Priority</th><th>Project</th><th>Updated</th></tr></thead><tbody>')
    for sp in specs:
        sp_slug = spec_slugs.get(sp["id"], sp["id"])
        spi.append(f'<tr><td><a href="{sp_slug}.html">{_esc(sp["title"])}</a></td>'
                   f'<td>{_html_tag(sp["status"])}</td><td>{_html_tag(sp["priority"], sp["priority"])}</td>'
                   f'<td>{_esc(sp.get("project") or "-")}</td><td>{_esc((sp["updated_at"] or "")[:10])}</td></tr>')
    spi.append('</tbody></table>')
    page = _html_page("Specs", "\n".join(spi),
                      breadcrumbs=[("Home", "../index.html"), ("Specs", "")],
                      sidebar_counts=sidebar_counts, active_section="specs", depth=1)
    (out / "specs" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for sp in specs:
        sp_slug = spec_slugs.get(sp["id"], sp["id"])
        h = [f'<h1>Spec: {_esc(sp["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(sp["id"])}</code>'),
            ("Status", _esc(sp["status"])),
            ("Priority", _esc(sp["priority"])),
            ("Project", _esc(sp.get("project") or "-")),
            ("Created", _esc(sp["created_at"])),
        ]
        if sp.get("author_id"):
            a_slug = people_slugs.get(sp["author_id"], sp["author_id"])
            meta.append(("Author", f'<a href="../people/{a_slug}.html">{_esc(sp["author_id"])}</a>'))
        tags = _json_list(sp.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if sp.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(sp["description"])}</div>')
        ac = _json_list(sp.get("acceptance_criteria"))
        if ac:
            h.append('<h2>Acceptance Criteria</h2><ul>' + "".join(f"<li>{_esc(c)}</li>" for c in ac) + "</ul>")
        spec_features = [f for f in features if f.get("spec_id") == sp["id"]]
        if spec_features:
            h.append('<h2>Features</h2><ul>')
            for f in spec_features:
                f_slug = feature_slugs.get(f["id"], f["id"])
                h.append(f'<li><a href="../features/{f_slug}.html">{_esc(f["name"])}</a> &mdash; {_esc(f["status"])}</li>')
            h.append('</ul>')
        page = _html_page(f'Spec: {sp["title"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Specs", "index.html"), (sp["title"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="specs", depth=1)
        (out / "specs" / f"{sp_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Features ───────────────────────────────────────────────────────

    fti = ['<h1>Features</h1>']
    fti.append('<table><thead><tr><th>Name</th><th>Status</th><th>Priority</th><th>Project</th><th>Updated</th></tr></thead><tbody>')
    for ft in features:
        ft_slug = feature_slugs.get(ft["id"], ft["id"])
        fti.append(f'<tr><td><a href="{ft_slug}.html">{_esc(ft["name"])}</a></td>'
                   f'<td>{_html_tag(ft["status"])}</td><td>{_html_tag(ft["priority"], ft["priority"])}</td>'
                   f'<td>{_esc(ft.get("project") or "-")}</td><td>{_esc((ft["updated_at"] or "")[:10])}</td></tr>')
    fti.append('</tbody></table>')
    page = _html_page("Features", "\n".join(fti),
                      breadcrumbs=[("Home", "../index.html"), ("Features", "")],
                      sidebar_counts=sidebar_counts, active_section="features", depth=1)
    (out / "features" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for ft in features:
        ft_slug = feature_slugs.get(ft["id"], ft["id"])
        h = [f'<h1>Feature: {_esc(ft["name"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(ft["id"])}</code>'),
            ("Status", _esc(ft["status"])),
            ("Priority", _esc(ft["priority"])),
            ("Project", _esc(ft.get("project") or "-")),
            ("Created", _esc(ft["created_at"])),
        ]
        if ft.get("spec_id"):
            sp_slug = spec_slugs.get(ft["spec_id"], ft["spec_id"])
            meta.append(("Spec", f'<a href="../specs/{sp_slug}.html">{_esc(ft["spec_id"])}</a>'))
        if ft.get("lead_id"):
            l_slug = people_slugs.get(ft["lead_id"], ft["lead_id"])
            meta.append(("Lead", f'<a href="../people/{l_slug}.html">{_esc(ft["lead_id"])}</a>'))
        tags = _json_list(ft.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if ft.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(ft["description"])}</div>')
        ft_links = [l for l in links if l["from_id"] == ft["id"] or l["to_id"] == ft["id"]]
        if ft_links:
            h.append('<h2>Related</h2><ul>')
            for l in ft_links:
                other_id = l["to_id"] if l["from_id"] == ft["id"] else l["from_id"]
                other_type = l["to_type"] if l["from_id"] == ft["id"] else l["from_type"]
                h.append(f'<li>{_html_tag(l["link_type"])} &rarr; [{_esc(other_type)}] <code>{_esc(other_id)}</code></li>')
            h.append('</ul>')
        page = _html_page(f'Feature: {ft["name"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Features", "index.html"), (ft["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="features", depth=1)
        (out / "features" / f"{ft_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Components ─────────────────────────────────────────────────────

    ci = ['<h1>Components</h1>']
    ci.append('<table><thead><tr><th>Name</th><th>Type</th><th>Project</th><th>Tech Stack</th></tr></thead><tbody>')
    for cp in components:
        cp_slug = component_slugs.get(cp["id"], cp["id"])
        ts = ", ".join(_json_list(cp.get("tech_stack"))) or "-"
        ci.append(f'<tr><td><a href="{cp_slug}.html">{_esc(cp["name"])}</a></td>'
                  f'<td>{_html_tag(cp["type"])}</td>'
                  f'<td>{_esc(cp.get("project") or "-")}</td><td>{_esc(ts)}</td></tr>')
    ci.append('</tbody></table>')
    page = _html_page("Components", "\n".join(ci),
                      breadcrumbs=[("Home", "../index.html"), ("Components", "")],
                      sidebar_counts=sidebar_counts, active_section="components", depth=1)
    (out / "components" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for cp in components:
        cp_slug = component_slugs.get(cp["id"], cp["id"])
        h = [f'<h1>Component: {_esc(cp["name"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(cp["id"])}</code>'),
            ("Type", _esc(cp["type"])),
            ("Project", _esc(cp.get("project") or "-")),
            ("Created", _esc(cp["created_at"])),
        ]
        if cp.get("owner_id"):
            o_slug = people_slugs.get(cp["owner_id"], cp["owner_id"])
            meta.append(("Owner", f'<a href="../people/{o_slug}.html">{_esc(cp["owner_id"])}</a>'))
        ts = _json_list(cp.get("tech_stack"))
        if ts:
            meta.append(("Tech Stack", " ".join(_html_tag(t) for t in ts)))
        tags = _json_list(cp.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if cp.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(cp["description"])}</div>')
        page = _html_page(f'Component: {cp["name"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Components", "index.html"), (cp["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="components", depth=1)
        (out / "components" / f"{cp_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── People ─────────────────────────────────────────────────────────

    pei = ['<h1>People</h1>']
    pei.append('<table><thead><tr><th>Name</th><th>Type</th><th>Role</th><th>GitHub</th><th>Skills</th></tr></thead><tbody>')
    for pr in people:
        pr_slug = people_slugs.get(pr["id"], pr["id"])
        sk = ", ".join(_json_list(pr.get("skills"))) or "-"
        pei.append(f'<tr><td><a href="{pr_slug}.html">{_esc(pr["name"])}</a></td>'
                   f'<td>{_html_tag(pr.get("type", "individual"))}</td>'
                   f'<td>{_esc(pr.get("role") or "-")}</td>'
                   f'<td>{_esc(pr.get("github") or "-")}</td><td>{_esc(sk)}</td></tr>')
    pei.append('</tbody></table>')
    page = _html_page("People", "\n".join(pei),
                      breadcrumbs=[("Home", "../index.html"), ("People", "")],
                      sidebar_counts=sidebar_counts, active_section="people", depth=1)
    (out / "people" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for pr in people:
        pr_slug = people_slugs.get(pr["id"], pr["id"])
        h = [f'<h1>{_esc(pr["name"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(pr["id"])}</code>'),
            ("Type", _esc(pr.get("type", "individual"))),
            ("Role", _esc(pr.get("role") or "-")),
        ]
        if pr.get("email"):
            meta.append(("Email", _esc(pr["email"])))
        if pr.get("github"):
            meta.append(("GitHub", _esc(pr["github"])))
        sk = _json_list(pr.get("skills"))
        if sk:
            meta.append(("Skills", " ".join(_html_tag(s) for s in sk)))
        h.append(_html_meta_table(meta))
        if pr.get("notes"):
            h.append(f'<div class="content-block">{_md(pr["notes"])}</div>')
        owned = [c for c in components if c.get("owner_id") == pr["id"]]
        if owned:
            h.append('<h2>Owned Components</h2><ul>')
            for c in owned:
                c_slug = component_slugs.get(c["id"], c["id"])
                h.append(f'<li><a href="../components/{c_slug}.html">{_esc(c["name"])}</a> ({_esc(c["type"])})</li>')
            h.append('</ul>')
        led = [f for f in features if f.get("lead_id") == pr["id"]]
        if led:
            h.append('<h2>Led Features</h2><ul>')
            for f in led:
                f_slug = feature_slugs.get(f["id"], f["id"])
                h.append(f'<li><a href="../features/{f_slug}.html">{_esc(f["name"])}</a> &mdash; {_esc(f["status"])}</li>')
            h.append('</ul>')
        authored = [s for s in specs if s.get("author_id") == pr["id"]]
        if authored:
            h.append('<h2>Authored Specs</h2><ul>')
            for s in authored:
                s_slug = spec_slugs.get(s["id"], s["id"])
                h.append(f'<li><a href="../specs/{s_slug}.html">{_esc(s["title"])}</a> &mdash; {_esc(s["status"])}</li>')
            h.append('</ul>')
        person_teams = db.backend.fetchall(
            f"SELECT t.*, tm.role AS member_role FROM team_members tm JOIN teams t ON tm.team_id=t.id WHERE tm.person_id={p}",
            (pr["id"],),
        )
        if person_teams:
            h.append('<h2>Teams</h2><ul>')
            for t in person_teams:
                t_slug = team_slugs.get(t["id"], t["id"])
                h.append(f'<li><a href="../teams/{t_slug}.html">{_esc(t["name"])}</a> ({_esc(t["member_role"])})</li>')
            h.append('</ul>')
        page = _html_page(pr["name"][:60], "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("People", "index.html"), (pr["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="people", depth=1)
        (out / "people" / f"{pr_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Teams ──────────────────────────────────────────────────────────

    tmi = ['<h1>Teams</h1>']
    tmi.append('<table><thead><tr><th>Name</th><th>Project</th><th>Description</th></tr></thead><tbody>')
    for tm in teams_data:
        tm_slug = team_slugs.get(tm["id"], tm["id"])
        tmi.append(f'<tr><td><a href="{tm_slug}.html">{_esc(tm["name"])}</a></td>'
                   f'<td>{_esc(tm.get("project") or "-")}</td>'
                   f'<td>{_esc((tm.get("description") or "-")[:80])}</td></tr>')
    tmi.append('</tbody></table>')
    page = _html_page("Teams", "\n".join(tmi),
                      breadcrumbs=[("Home", "../index.html"), ("Teams", "")],
                      sidebar_counts=sidebar_counts, active_section="teams", depth=1)
    (out / "teams" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for tm in teams_data:
        tm_slug = team_slugs.get(tm["id"], tm["id"])
        members = db.backend.fetchall(
            f"SELECT p.*, tmm.role AS member_role FROM team_members tmm JOIN people p ON tmm.person_id=p.id WHERE tmm.team_id={p}",
            (tm["id"],),
        )
        h = [f'<h1>Team: {_esc(tm["name"])}</h1>']
        if tm.get("description"):
            h.append(f'<p>{_esc(tm["description"])}</p>')
        meta = [
            ("ID", f'<code>{_esc(tm["id"])}</code>'),
            ("Project", _esc(tm.get("project") or "-")),
            ("Members", str(len(members))),
        ]
        if tm.get("lead_id"):
            l_slug = people_slugs.get(tm["lead_id"], tm["lead_id"])
            meta.append(("Lead", f'<a href="../people/{l_slug}.html">{_esc(tm["lead_id"])}</a>'))
        tags = _json_list(tm.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if members:
            h.append('<h2>Members</h2>')
            h.append('<table><thead><tr><th>Name</th><th>Type</th><th>Role</th><th>Team Role</th></tr></thead><tbody>')
            for m in members:
                m_slug = people_slugs.get(m["id"], m["id"])
                h.append(f'<tr><td><a href="../people/{m_slug}.html">{_esc(m["name"])}</a></td>'
                         f'<td>{_html_tag(m.get("type", "individual"))}</td>'
                         f'<td>{_esc(m.get("role") or "-")}</td><td>{_esc(m["member_role"])}</td></tr>')
            h.append('</tbody></table>')
        page = _html_page(f'Team: {tm["name"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Teams", "index.html"), (tm["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="teams", depth=1)
        (out / "teams" / f"{tm_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Projects ───────────────────────────────────────────────────────

    ps_by_name = {ps["project"]: ps for ps in project_sums}

    # Projects index
    pi = ['<h1>Projects</h1>']
    pi.append('<table><thead><tr><th>Project</th><th>Summary</th><th>Sessions</th><th>Thoughts</th><th>Rules</th></tr></thead><tbody>')
    for proj in sorted(all_projects):
        proj_slug = project_slugs.get(proj, proj)
        ps = ps_by_name.get(proj)
        summary = _esc(ps["summary"][:80]) if ps and ps.get("summary") else "-"
        ts = ps["total_sessions"] if ps else "-"
        tt = ps["total_thoughts"] if ps else "-"
        tr_ = ps["total_rules"] if ps else "-"
        pi.append(f'<tr><td><a href="{proj_slug}.html">{_esc(proj)}</a></td>'
                  f'<td>{summary}</td><td>{ts}</td><td>{tt}</td><td>{tr_}</td></tr>')
    pi.append('</tbody></table>')
    page = _html_page("Projects", "\n".join(pi),
                      breadcrumbs=[("Home", "../index.html"), ("Projects", "")],
                      sidebar_counts=sidebar_counts, active_section="projects", depth=1)
    (out / "projects" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    # Individual projects
    for proj in sorted(all_projects):
        proj_slug = project_slugs.get(proj, proj)
        h = [f'<h1>Project: {_esc(proj)}</h1>']
        ps = ps_by_name.get(proj)
        if ps:
            if ps.get("summary"):
                h.append(f'<p>{_esc(ps["summary"])}</p>')
            ts = _json_list(ps.get("tech_stack"))
            if ts:
                h.append(f'<p><strong>Tech Stack:</strong> {", ".join(_esc(t) for t in ts)}</p>')
            kp = _json_list(ps.get("key_patterns"))
            if kp:
                h.append('<p><strong>Key Patterns:</strong></p><ul>' + "".join(f"<li>{_esc(k)}</li>" for k in kp) + "</ul>")
            ag = _json_list(ps.get("active_goals"))
            if ag:
                h.append('<p><strong>Active Goals:</strong></p><ul>' + "".join(f"<li>{_esc(a)}</li>" for a in ag) + "</ul>")
            h.append(f'<p><strong>Stats:</strong> {ps["total_sessions"]} sessions, {ps["total_thoughts"]} thoughts, {ps["total_rules"]} rules</p>')

        proj_rules = [r for r in rules if r.get("project") == proj]
        if proj_rules:
            h.append('<h2>Rules</h2><ul>')
            for r in proj_rules:
                r_slug = rule_slugs.get(r["id"], r["id"])
                sev_cls = r["severity"] if r["severity"] in ("critical", "preference") else ""
                pin = _html_tag("pinned", "pinned") + " " if r["pinned"] else ""
                h.append(f'<li>{_html_tag(r["severity"], sev_cls)} {_html_tag(r["type"], r["type"])} {pin}'
                         f'<a href="../rules/{r_slug}.html">{_esc(r["summary"])}</a> (&times;{r["reinforcement_count"]})</li>')
            h.append('</ul>')

        proj_thoughts = [t for t in thoughts if t.get("project") == proj]
        if proj_thoughts:
            h.append('<h2>Thoughts</h2><ul>')
            for t in proj_thoughts[:50]:
                t_slug = thought_slugs.get(t["id"], t["id"])
                pin = _html_tag("pinned", "pinned") + " " if t["pinned"] else ""
                h.append(f'<li>{_html_tag(t["type"])} {pin}<a href="../thoughts/{t_slug}.html">{_esc(t["summary"])}</a></li>')
            h.append('</ul>')

        proj_errors = [e for e in errors if e.get("project") == proj]
        if proj_errors:
            h.append('<h2>Error Patterns</h2><ul>')
            for e in proj_errors:
                e_slug = error_slugs.get(e["id"], e["id"])
                h.append(f'<li><a href="../errors/{e_slug}.html">{_esc(e["error_description"][:60])}</a></li>')
            h.append('</ul>')

        proj_sessions = [s for s in sessions if s.get("project") == proj]
        if proj_sessions:
            h.append('<h2>Sessions</h2>')
            h.append('<table><thead><tr><th>Date</th><th>Agent</th><th>Goal</th><th>Status</th></tr></thead><tbody>')
            for s in proj_sessions[:20]:
                date = (s.get("started_at") or "")[:10]
                sess_slug = session_slugs.get(s["id"], s["id"])
                h.append(f'<tr><td>{_esc(date)}</td><td>{_esc(s["agent_type"])}/{_esc(s["model"])}</td>'
                         f'<td><a href="../sessions/{sess_slug}.html">{_esc(s.get("goal") or "-")}</a></td>'
                         f'<td>{_esc(s["status"])}</td></tr>')
            h.append('</tbody></table>')

        page = _html_page(
            f"Project: {proj}", "\n".join(h),
            breadcrumbs=[("Home", "../index.html"), ("Projects", "index.html"), (proj, "")],
            sidebar_counts=sidebar_counts, active_section="projects", depth=1,
        )
        (out / "projects" / f"{proj_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Agents ─────────────────────────────────────────────────────────

    ai = ['<h1>Agent Stats</h1>']
    ai.append('<table><thead><tr><th>Agent</th><th>Model</th><th>Sessions</th><th>Thoughts</th><th>Rules</th><th>Errors</th><th>First Seen</th><th>Last Seen</th></tr></thead><tbody>')
    total_s = total_t = total_r = total_e = 0
    for _key, rec in sorted(agent_stats.items()):
        total_s += rec["sessions"]
        total_t += rec["thoughts"]
        total_r += rec["rules"]
        total_e += rec["errors"]
        ai.append(f'<tr><td>{_esc(rec["agent_type"])}</td><td>{_esc(rec["model"])}</td>'
                  f'<td>{rec["sessions"]}</td><td>{rec["thoughts"]}</td><td>{rec["rules"]}</td><td>{rec["errors"]}</td>'
                  f'<td>{_esc(rec["first_seen"][:10] if rec["first_seen"] else "-")}</td>'
                  f'<td>{_esc(rec["last_seen"][:10] if rec["last_seen"] else "-")}</td></tr>')
    ai.append(f'<tr style="font-weight:700"><td colspan="2">Totals</td>'
              f'<td>{total_s}</td><td>{total_t}</td><td>{total_r}</td><td>{total_e}</td><td></td><td></td></tr>')
    ai.append('</tbody></table>')
    page = _html_page("Agent Stats", "\n".join(ai),
                      breadcrumbs=[("Home", "../index.html"), ("Agents", "")],
                      sidebar_counts=sidebar_counts, active_section="agents", depth=1)
    (out / "agents" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    # ── Search Index ───────────────────────────────────────────────────

    search_items = []
    for t in thoughts:
        t_slug = thought_slugs.get(t["id"], t["id"])
        search_items.append({
            "type": "thought", "id": t["id"],
            "title": t["summary"],
            "content": (t.get("content") or "")[:300],
            "keywords": _json_list(t.get("keywords")),
            "url": f"thoughts/{t_slug}.html",
        })
    for r in rules:
        r_slug = rule_slugs.get(r["id"], r["id"])
        search_items.append({
            "type": "rule", "id": r["id"],
            "title": r["summary"],
            "content": (r.get("content") or "")[:300],
            "keywords": _json_list(r.get("keywords")),
            "url": f"rules/{r_slug}.html",
        })
    for e in errors:
        e_slug = error_slugs.get(e["id"], e["id"])
        search_items.append({
            "type": "error", "id": e["id"],
            "title": e["error_description"][:120],
            "content": ((e.get("cause") or "") + " " + (e.get("fix") or ""))[:300],
            "keywords": _json_list(e.get("keywords")),
            "url": f"errors/{e_slug}.html",
        })
    for s in sessions:
        sess_slug = session_slugs.get(s["id"], s["id"])
        search_items.append({
            "type": "session", "id": s["id"],
            "title": s.get("goal") or s["id"],
            "content": (s.get("summary") or "")[:300],
            "keywords": [],
            "url": f"sessions/{sess_slug}.html",
        })
    for g in groups:
        g_slug = group_slugs.get(g["id"], g["id"])
        search_items.append({
            "type": "group", "id": g["id"],
            "title": g["name"],
            "content": (g.get("description") or "")[:300],
            "keywords": [],
            "url": f"groups/{g_slug}.html",
        })
    for pl in plans:
        pl_slug = plan_slugs.get(pl["id"], pl["id"])
        search_items.append({
            "type": "plan", "id": pl["id"],
            "title": pl["title"],
            "content": (pl.get("description") or "")[:300],
            "keywords": _json_list(pl.get("tags")),
            "url": f"plans/{pl_slug}.html",
        })
    for sp in specs:
        sp_slug = spec_slugs.get(sp["id"], sp["id"])
        search_items.append({
            "type": "spec", "id": sp["id"],
            "title": sp["title"],
            "content": (sp.get("description") or "")[:300],
            "keywords": _json_list(sp.get("tags")),
            "url": f"specs/{sp_slug}.html",
        })
    for ft in features:
        ft_slug = feature_slugs.get(ft["id"], ft["id"])
        search_items.append({
            "type": "feature", "id": ft["id"],
            "title": ft["name"],
            "content": (ft.get("description") or "")[:300],
            "keywords": _json_list(ft.get("tags")),
            "url": f"features/{ft_slug}.html",
        })
    for cp in components:
        cp_slug = component_slugs.get(cp["id"], cp["id"])
        search_items.append({
            "type": "component", "id": cp["id"],
            "title": cp["name"],
            "content": (cp.get("description") or "")[:300],
            "keywords": _json_list(cp.get("tags")) + _json_list(cp.get("tech_stack")),
            "url": f"components/{cp_slug}.html",
        })
    for pr in people:
        pr_slug = people_slugs.get(pr["id"], pr["id"])
        search_items.append({
            "type": "person", "id": pr["id"],
            "title": pr["name"],
            "content": (pr.get("role") or "") + " " + (pr.get("notes") or ""),
            "keywords": _json_list(pr.get("skills")),
            "url": f"people/{pr_slug}.html",
        })
    for tm in teams_data:
        tm_slug = team_slugs.get(tm["id"], tm["id"])
        search_items.append({
            "type": "team", "id": tm["id"],
            "title": tm["name"],
            "content": (tm.get("description") or "")[:300],
            "keywords": _json_list(tm.get("tags")),
            "url": f"teams/{tm_slug}.html",
        })

    (out / "search-index.json").write_text(json.dumps(search_items, ensure_ascii=False, indent=None), encoding="utf-8")
    file_count += 1

    db.close()

    return Path(output_dir), file_count


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
                        choices=["markdown", "jekyll", "html"],
                        help="Export format: markdown (plain), jekyll (GitHub Pages site), or html (static website)")
    parser.add_argument("-p", "--project", type=str, default=None,
                        help="Export only a single project (by name)")
    args = parser.parse_args()

    if args.format == "jekyll":
        output_dir = args.output or "memgram-jekyll"
        out_path, count = export_jekyll(db_path=args.db_path, output_dir=output_dir, project=args.project)
        print(f"Exported {count} files as Jekyll site to {out_path.resolve()}")
        print(f"To deploy: push to GitHub and enable Pages from Settings > Pages")
    elif args.format == "html":
        output_dir = args.output or "memgram-web"
        out_path, count = export_html(db_path=args.db_path, output_dir=output_dir, project=args.project)
        print(f"Exported {count} files as static HTML site to {out_path.resolve()}")
        print(f"Open {out_path.resolve()}/index.html in a browser or serve with any static file server")
    else:
        output_dir = args.output or "memgram-export"
        out_path, count = export_markdown(db_path=args.db_path, output_dir=output_dir, project=args.project)
        print(f"Exported {count} files to {out_path.resolve()}")
