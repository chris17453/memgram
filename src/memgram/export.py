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
        "tickets": _build_slug_map(data.get("tickets", []), lambda t: t.get("title")),
        "instructions": _build_slug_map(data.get("instructions", []), lambda i: i.get("title")),
        "attachments": _build_slug_map(data.get("attachments", []), lambda a: a.get("label")),
        "endpoints": _build_slug_map(data.get("endpoints", []), lambda e: f'{e.get("method")} {e.get("path")}'),
        "credentials": _build_slug_map(data.get("credentials", []), lambda c: c.get("name")),
        "environments": _build_slug_map(data.get("environments", []), lambda e: e.get("name")),
        "deployments": _build_slug_map(data.get("deployments", []), lambda d: d.get("version")),
        "builds": _build_slug_map(data.get("builds", []), lambda b: b.get("name")),
        "incidents": _build_slug_map(data.get("incidents", []), lambda i: i.get("title")),
        "dependencies": _build_slug_map(data.get("dependencies", []), lambda d: d.get("name")),
        "runbooks": _build_slug_map(data.get("runbooks", []), lambda r: r.get("title")),
        "decisions": _build_slug_map(data.get("decisions", []), lambda d: d.get("title")),
        "diagrams": _build_slug_map(data.get("diagrams", []), lambda d: d.get("title")),
        "comments": _build_slug_map(data.get("comments", []), lambda c: c.get("content", "")[:40]),
        "audit_log": _build_slug_map(data.get("audit_log", []), lambda a: f'{a.get("action")} {a.get("entity_type")}'),
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
            "tickets": db.backend.fetchall(f"SELECT * FROM tickets WHERE project={p} ORDER BY updated_at DESC", pp),
            "instructions": db.backend.fetchall(f"SELECT * FROM instructions WHERE project={p} ORDER BY position", pp),
            "attachments": db.backend.fetchall("SELECT * FROM attachments ORDER BY position"),
            "endpoints": db.backend.fetchall(f"SELECT * FROM endpoints WHERE project={p} ORDER BY path", pp),
            "credentials": db.backend.fetchall(f"SELECT * FROM credentials WHERE project={p} ORDER BY name", pp),
            "environments": db.backend.fetchall(f"SELECT * FROM environments WHERE project={p} ORDER BY name", pp),
            "deployments": db.backend.fetchall(f"SELECT * FROM deployments WHERE project={p} ORDER BY created_at DESC", pp),
            "builds": db.backend.fetchall(f"SELECT * FROM builds WHERE project={p} ORDER BY created_at DESC", pp),
            "incidents": db.backend.fetchall(f"SELECT * FROM incidents WHERE project={p} ORDER BY created_at DESC", pp),
            "dependencies": db.backend.fetchall(f"SELECT * FROM dependencies WHERE project={p} ORDER BY name", pp),
            "runbooks": db.backend.fetchall(f"SELECT * FROM runbooks WHERE project={p} ORDER BY title", pp),
            "decisions": db.backend.fetchall(f"SELECT * FROM decisions WHERE project={p} ORDER BY created_at DESC", pp),
            "diagrams": db.backend.fetchall(f"SELECT * FROM diagrams WHERE project={p} ORDER BY updated_at DESC", pp),
            "comments": db.backend.fetchall(f"SELECT * FROM comments WHERE project={p} ORDER BY created_at DESC", pp),
            "audit_log": db.backend.fetchall(f"SELECT * FROM audit_log WHERE project={p} ORDER BY created_at DESC", pp),
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
            "tickets": db.backend.fetchall("SELECT * FROM tickets ORDER BY updated_at DESC"),
            "instructions": db.backend.fetchall("SELECT * FROM instructions ORDER BY position"),
            "attachments": db.backend.fetchall("SELECT * FROM attachments ORDER BY position"),
            "endpoints": db.backend.fetchall("SELECT * FROM endpoints ORDER BY path"),
            "credentials": db.backend.fetchall("SELECT * FROM credentials ORDER BY name"),
            "environments": db.backend.fetchall("SELECT * FROM environments ORDER BY name"),
            "deployments": db.backend.fetchall("SELECT * FROM deployments ORDER BY created_at DESC"),
            "builds": db.backend.fetchall("SELECT * FROM builds ORDER BY created_at DESC"),
            "incidents": db.backend.fetchall("SELECT * FROM incidents ORDER BY created_at DESC"),
            "dependencies": db.backend.fetchall("SELECT * FROM dependencies ORDER BY name"),
            "runbooks": db.backend.fetchall("SELECT * FROM runbooks ORDER BY title"),
            "decisions": db.backend.fetchall("SELECT * FROM decisions ORDER BY created_at DESC"),
            "diagrams": db.backend.fetchall("SELECT * FROM diagrams ORDER BY updated_at DESC"),
            "comments": db.backend.fetchall("SELECT * FROM comments ORDER BY created_at DESC"),
            "audit_log": db.backend.fetchall("SELECT * FROM audit_log ORDER BY created_at DESC"),
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
                "plans", "specs", "features", "components", "people", "teams",
                "tickets", "instructions", "attachments", "endpoints", "credentials",
                "environments", "deployments", "builds", "incidents", "dependencies",
                "runbooks", "decisions", "diagrams", "comments", "audit_log"):
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
    tickets = data.get("tickets", [])
    instructions_data = data.get("instructions", [])
    attachments = data.get("attachments", [])
    endpoints = data.get("endpoints", [])
    credentials = data.get("credentials", [])
    environments = data.get("environments", [])
    deployments = data.get("deployments", [])
    builds_data = data.get("builds", [])
    incidents = data.get("incidents", [])
    dependencies = data.get("dependencies", [])
    runbooks = data.get("runbooks", [])
    decisions = data.get("decisions", [])
    diagrams_data = data.get("diagrams", [])
    comments = data.get("comments", [])
    audit_log = data.get("audit_log", [])
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums, plans, specs, features, components, teams_data, tickets, instructions_data, endpoints, credentials, environments, deployments, builds_data, incidents, dependencies, runbooks, decisions, diagrams_data, comments)
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
    ticket_slugs = slug_maps["tickets"]
    instruction_slugs = slug_maps["instructions"]
    attachment_slugs = slug_maps["attachments"]
    endpoint_slugs = slug_maps["endpoints"]
    credential_slugs = slug_maps["credentials"]
    environment_slugs = slug_maps["environments"]
    deployment_slugs = slug_maps["deployments"]
    build_slugs = slug_maps["builds"]
    incident_slugs = slug_maps["incidents"]
    dependency_slugs = slug_maps["dependencies"]
    runbook_slugs = slug_maps["runbooks"]
    decision_slugs = slug_maps["decisions"]
    diagram_slugs = slug_maps["diagrams"]
    comment_slugs = slug_maps["comments"]
    audit_log_slugs = slug_maps["audit_log"]

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
    idx.append(f"| Tickets | {len(tickets)} |")
    idx.append(f"| Instructions | {len(instructions_data)} |")
    idx.append(f"| Endpoints | {len(endpoints)} |")
    idx.append(f"| Credentials | {len(credentials)} |")
    idx.append(f"| Environments | {len(environments)} |")
    idx.append(f"| Deployments | {len(deployments)} |")
    idx.append(f"| Builds | {len(builds_data)} |")
    idx.append(f"| Incidents | {len(incidents)} |")
    idx.append(f"| Dependencies | {len(dependencies)} |")
    idx.append(f"| Runbooks | {len(runbooks)} |")
    idx.append(f"| Decisions | {len(decisions)} |")
    idx.append(f"| Diagrams | {len(diagrams_data)} |")
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
            ss_decisions = _json_list(ss.get("decisions_made"))
            if ss_decisions:
                lines.append("**Decisions:**\n")
                lines.append(_bullet_list(ss_decisions))
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

    # ── Tickets ─────────────────────────────────────────────────────────

    for tk in tickets:
        tk_slug = ticket_slugs.get(tk["id"], tk["id"])
        lines = [f"# Ticket: {tk['ticket_number']} — {tk['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{tk['id']}` |")
        lines.append(f"| Number | {tk['ticket_number']} |")
        lines.append(f"| Status | {tk['status']} |")
        lines.append(f"| Priority | {tk['priority']} |")
        lines.append(f"| Type | {tk['type']} |")
        lines.append(f"| Project | {tk.get('project') or '-'} |")
        if tk.get("assignee_id"):
            a_slug = people_slugs.get(tk["assignee_id"], tk["assignee_id"])
            lines.append(f"| Assignee | [{tk['assignee_id']}](../people/{a_slug}.md) |")
        if tk.get("reporter_id"):
            r_slug = people_slugs.get(tk["reporter_id"], tk["reporter_id"])
            lines.append(f"| Reporter | [{tk['reporter_id']}](../people/{r_slug}.md) |")
        if tk.get("due_date"):
            lines.append(f"| Due | {tk['due_date']} |")
        lines.append(f"| Created | {tk['created_at']} |")
        tags = _json_list(tk.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if tk.get("description"):
            lines.append(f"## Description\n\n{tk['description']}\n")
        (out / "tickets" / f"{tk_slug}.md").write_text("\n".join(lines))

    # ── Instructions ───────────────────────────────────────────────────

    for ins in instructions_data:
        ins_slug = instruction_slugs.get(ins["id"], ins["id"])
        lines = [f"# Instruction: {ins['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{ins['id']}` |")
        lines.append(f"| Section | {ins['section']} |")
        lines.append(f"| Priority | {ins['priority']} |")
        lines.append(f"| Scope | {ins['scope']} |")
        lines.append(f"| Active | {'Yes' if ins.get('active') else 'No'} |")
        lines.append(f"| Position | {ins['position']} |")
        lines.append(f"| Project | {ins.get('project') or '-'} |")
        lines.append(f"| Created | {ins['created_at']} |")
        tags = _json_list(ins.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if ins.get("content"):
            lines.append(f"## Content\n\n{ins['content']}\n")
        (out / "instructions" / f"{ins_slug}.md").write_text("\n".join(lines))

    # ── Attachments ────────────────────────────────────────────────────

    for att in attachments:
        att_slug = attachment_slugs.get(att["id"], att["id"])
        lines = [f"# Attachment: {att.get('label') or att['id']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{att['id']}` |")
        lines.append(f"| Entity | {att['entity_type']} `{att['entity_id']}` |")
        lines.append(f"| URL | {att['url']} |")
        lines.append(f"| Type | {att['type']} |")
        if att.get("mime_type"):
            lines.append(f"| MIME | {att['mime_type']} |")
        lines.append(f"| Position | {att['position']} |")
        lines.append(f"| Created | {att['created_at']} |")
        lines.append("")
        if att.get("description"):
            lines.append(f"## Description\n\n{att['description']}\n")
        (out / "attachments" / f"{att_slug}.md").write_text("\n".join(lines))

    # ── Endpoints ──────────────────────────────────────────────────────

    for ep in endpoints:
        ep_slug = endpoint_slugs.get(ep["id"], ep["id"])
        lines = [f"# {ep['method']} {ep['path']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{ep['id']}` |")
        lines.append(f"| Method | {ep['method']} |")
        lines.append(f"| Path | {ep['path']} |")
        if ep.get("base_url"):
            lines.append(f"| Base URL | {ep['base_url']} |")
        lines.append(f"| Auth | {ep['auth_type']} |")
        lines.append(f"| Status | {ep['status']} |")
        lines.append(f"| Project | {ep.get('project') or '-'} |")
        if ep.get("rate_limit"):
            lines.append(f"| Rate Limit | {ep['rate_limit']} |")
        lines.append(f"| Created | {ep['created_at']} |")
        tags = _json_list(ep.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if ep.get("description"):
            lines.append(f"## Description\n\n{ep['description']}\n")
        (out / "endpoints" / f"{ep_slug}.md").write_text("\n".join(lines))

    # ── Credentials ────────────────────────────────────────────────────

    for cr in credentials:
        cr_slug = credential_slugs.get(cr["id"], cr["id"])
        lines = [f"# Credential: {cr['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{cr['id']}` |")
        lines.append(f"| Type | {cr['type']} |")
        lines.append(f"| Provider | {cr.get('provider') or '-'} |")
        if cr.get("vault_path"):
            lines.append(f"| Vault Path | {cr['vault_path']} |")
        if cr.get("env_var"):
            lines.append(f"| Env Var | {cr['env_var']} |")
        lines.append(f"| Project | {cr.get('project') or '-'} |")
        if cr.get("last_rotated"):
            lines.append(f"| Last Rotated | {cr['last_rotated']} |")
        if cr.get("expires_at"):
            lines.append(f"| Expires | {cr['expires_at']} |")
        lines.append(f"| Created | {cr['created_at']} |")
        tags = _json_list(cr.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if cr.get("description"):
            lines.append(f"## Description\n\n{cr['description']}\n")
        (out / "credentials" / f"{cr_slug}.md").write_text("\n".join(lines))

    # ── Environments ───────────────────────────────────────────────────

    for env in environments:
        env_slug = environment_slugs.get(env["id"], env["id"])
        lines = [f"# Environment: {env['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{env['id']}` |")
        lines.append(f"| Type | {env['type']} |")
        if env.get("url"):
            lines.append(f"| URL | {env['url']} |")
        lines.append(f"| Project | {env.get('project') or '-'} |")
        lines.append(f"| Created | {env['created_at']} |")
        tags = _json_list(env.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if env.get("description"):
            lines.append(f"## Description\n\n{env['description']}\n")
        (out / "environments" / f"{env_slug}.md").write_text("\n".join(lines))

    # ── Deployments ────────────────────────────────────────────────────

    for dep in deployments:
        dep_slug = deployment_slugs.get(dep["id"], dep["id"])
        lines = [f"# Deployment: {dep['version']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{dep['id']}` |")
        lines.append(f"| Version | {dep['version']} |")
        lines.append(f"| Status | {dep['status']} |")
        lines.append(f"| Strategy | {dep['strategy']} |")
        lines.append(f"| Project | {dep.get('project') or '-'} |")
        if dep.get("environment_id"):
            env_s = environment_slugs.get(dep["environment_id"], dep["environment_id"])
            lines.append(f"| Environment | [{dep['environment_id']}](../environments/{env_s}.md) |")
        if dep.get("deployed_by"):
            lines.append(f"| Deployed By | {dep['deployed_by']} |")
        if dep.get("deployed_at"):
            lines.append(f"| Deployed At | {dep['deployed_at']} |")
        lines.append(f"| Created | {dep['created_at']} |")
        tags = _json_list(dep.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if dep.get("description"):
            lines.append(f"## Description\n\n{dep['description']}\n")
        (out / "deployments" / f"{dep_slug}.md").write_text("\n".join(lines))

    # ── Builds ─────────────────────────────────────────────────────────

    for bd in builds_data:
        bd_slug = build_slugs.get(bd["id"], bd["id"])
        lines = [f"# Build: {bd['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{bd['id']}` |")
        lines.append(f"| Pipeline | {bd.get('pipeline') or '-'} |")
        lines.append(f"| Status | {bd['status']} |")
        lines.append(f"| Trigger | {bd['trigger_type']} |")
        if bd.get("commit_sha"):
            lines.append(f"| Commit | `{bd['commit_sha']}` |")
        if bd.get("branch"):
            lines.append(f"| Branch | {bd['branch']} |")
        lines.append(f"| Project | {bd.get('project') or '-'} |")
        if bd.get("duration_seconds"):
            lines.append(f"| Duration | {bd['duration_seconds']}s |")
        if bd.get("artifact_url"):
            lines.append(f"| Artifact | {bd['artifact_url']} |")
        lines.append(f"| Created | {bd['created_at']} |")
        tags = _json_list(bd.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        (out / "builds" / f"{bd_slug}.md").write_text("\n".join(lines))

    # ── Incidents ──────────────────────────────────────────────────────

    for inc in incidents:
        inc_slug = incident_slugs.get(inc["id"], inc["id"])
        lines = [f"# Incident: {inc['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{inc['id']}` |")
        lines.append(f"| Severity | {inc['severity']} |")
        lines.append(f"| Status | {inc['status']} |")
        lines.append(f"| Project | {inc.get('project') or '-'} |")
        if inc.get("lead_id"):
            l_slug = people_slugs.get(inc["lead_id"], inc["lead_id"])
            lines.append(f"| Lead | [{inc['lead_id']}](../people/{l_slug}.md) |")
        if inc.get("started_at"):
            lines.append(f"| Started | {inc['started_at']} |")
        if inc.get("resolved_at"):
            lines.append(f"| Resolved | {inc['resolved_at']} |")
        lines.append(f"| Created | {inc['created_at']} |")
        tags = _json_list(inc.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if inc.get("description"):
            lines.append(f"## Description\n\n{inc['description']}\n")
        if inc.get("root_cause"):
            lines.append(f"## Root Cause\n\n{inc['root_cause']}\n")
        if inc.get("resolution"):
            lines.append(f"## Resolution\n\n{inc['resolution']}\n")
        timeline = _json_list(inc.get("timeline"))
        if timeline:
            lines.append("## Timeline\n")
            lines.append(_bullet_list(timeline))
        (out / "incidents" / f"{inc_slug}.md").write_text("\n".join(lines))

    # ── Dependencies ───────────────────────────────────────────────────

    for dp in dependencies:
        dp_slug = dependency_slugs.get(dp["id"], dp["id"])
        lines = [f"# Dependency: {dp['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{dp['id']}` |")
        lines.append(f"| Version | {dp.get('version') or '-'} |")
        lines.append(f"| Type | {dp['type']} |")
        if dp.get("source"):
            lines.append(f"| Source | {dp['source']} |")
        if dp.get("license"):
            lines.append(f"| License | {dp['license']} |")
        lines.append(f"| Project | {dp.get('project') or '-'} |")
        if dp.get("pinned_version"):
            lines.append(f"| Pinned | {dp['pinned_version']} |")
        if dp.get("latest_version"):
            lines.append(f"| Latest | {dp['latest_version']} |")
        lines.append(f"| Created | {dp['created_at']} |")
        tags = _json_list(dp.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if dp.get("description"):
            lines.append(f"## Description\n\n{dp['description']}\n")
        (out / "dependencies" / f"{dp_slug}.md").write_text("\n".join(lines))

    # ── Runbooks ───────────────────────────────────────────────────────

    for rb in runbooks:
        rb_slug = runbook_slugs.get(rb["id"], rb["id"])
        lines = [f"# Runbook: {rb['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{rb['id']}` |")
        lines.append(f"| Project | {rb.get('project') or '-'} |")
        if rb.get("trigger_conditions"):
            lines.append(f"| Trigger | {rb['trigger_conditions']} |")
        if rb.get("last_executed"):
            lines.append(f"| Last Executed | {rb['last_executed']} |")
        lines.append(f"| Created | {rb['created_at']} |")
        tags = _json_list(rb.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if rb.get("description"):
            lines.append(f"## Description\n\n{rb['description']}\n")
        steps = _json_list(rb.get("steps"))
        if steps:
            lines.append("## Steps\n")
            for i, step in enumerate(steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        (out / "runbooks" / f"{rb_slug}.md").write_text("\n".join(lines))

    # ── Decisions ──────────────────────────────────────────────────────

    for dec in decisions:
        dec_slug = decision_slugs.get(dec["id"], dec["id"])
        lines = [f"# Decision: {dec['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{dec['id']}` |")
        lines.append(f"| Status | {dec['status']} |")
        lines.append(f"| Project | {dec.get('project') or '-'} |")
        if dec.get("author_id"):
            a_slug = people_slugs.get(dec["author_id"], dec["author_id"])
            lines.append(f"| Author | [{dec['author_id']}](../people/{a_slug}.md) |")
        if dec.get("decided_at"):
            lines.append(f"| Decided | {dec['decided_at']} |")
        if dec.get("superseded_by"):
            lines.append(f"| Superseded By | {dec['superseded_by']} |")
        lines.append(f"| Created | {dec['created_at']} |")
        tags = _json_list(dec.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if dec.get("context"):
            lines.append(f"## Context\n\n{dec['context']}\n")
        options = _json_list(dec.get("options"))
        if options:
            lines.append("## Options\n")
            lines.append(_bullet_list(options))
        if dec.get("outcome"):
            lines.append(f"## Outcome\n\n{dec['outcome']}\n")
        if dec.get("consequences"):
            lines.append(f"## Consequences\n\n{dec['consequences']}\n")
        (out / "decisions" / f"{dec_slug}.md").write_text("\n".join(lines))

    # ── Diagrams ──────────────────────────────────────────────────────

    for diag in diagrams_data:
        diag_slug = diagram_slugs.get(diag["id"], diag["id"])
        lines = [f"# Diagram: {diag['title']}\n"]
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| ID | `{diag['id']}` |")
        lines.append(f"| Type | {diag['diagram_type']} |")
        lines.append(f"| Project | {diag.get('project') or '-'} |")
        lines.append(f"| Created | {diag['created_at']} |")
        tags = _json_list(diag.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if diag.get("description"):
            lines.append(f"## Description\n\n{diag['description']}\n")
        if diag.get("definition"):
            dtype = diag["diagram_type"]
            if dtype == "mermaid":
                lines.append(f"## Diagram\n\n```mermaid\n{diag['definition']}\n```\n")
            elif dtype == "table":
                # Render as markdown table if possible
                try:
                    tdata = json.loads(diag["definition"])
                    cols = tdata.get("columns", [])
                    rows = tdata.get("rows", [])
                    if cols and rows:
                        lines.append("## Table\n")
                        lines.append("| " + " | ".join(str(c) for c in cols) + " |")
                        lines.append("| " + " | ".join("---" for _ in cols) + " |")
                        for row in rows:
                            cells = [str(row[c]) if isinstance(row, dict) else str(c) for c in (row if not isinstance(row, dict) else cols)]
                            lines.append("| " + " | ".join(cells) + " |")
                        lines.append("")
                    else:
                        lines.append(f"## Definition\n\n```json\n{diag['definition']}\n```\n")
                except (ValueError, TypeError):
                    lines.append(f"## Definition\n\n```json\n{diag['definition']}\n```\n")
            else:
                # chart, network, servicemap — JSON config
                lines.append(f"## Definition\n\n<!-- {dtype} config -->\n```json\n{diag['definition']}\n```\n")
        (out / "diagrams" / f"{diag_slug}.md").write_text("\n".join(lines))

    # ── Comments ───────────────────────────────────────────────────────

    for cm in comments:
        cm_slug = comment_slugs.get(cm["id"], cm["id"])
        lines = [f"# Comment by {cm.get('author') or 'Unknown'}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{cm['id']}` |")
        lines.append(f"| Entity | {cm['entity_type']} `{cm['entity_id']}` |")
        lines.append(f"| Author | {cm.get('author') or '-'} |")
        lines.append(f"| Project | {cm.get('project') or '-'} |")
        lines.append(f"| Created | {cm['created_at']} |")
        tags = _json_list(cm.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if cm.get("content"):
            lines.append(f"## Content\n\n{cm['content']}\n")
        (out / "comments" / f"{cm_slug}.md").write_text("\n".join(lines))

    # ── Audit Log ──────────────────────────────────────────────────────

    for al in audit_log:
        al_slug = audit_log_slugs.get(al["id"], al["id"])
        lines = [f"# Audit: {al['action']} {al['entity_type']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{al['id']}` |")
        lines.append(f"| Entity | {al['entity_type']} `{al['entity_id']}` |")
        lines.append(f"| Action | {al['action']} |")
        if al.get("field_changed"):
            lines.append(f"| Field Changed | {al['field_changed']} |")
        if al.get("old_value"):
            lines.append(f"| Old Value | {al['old_value']} |")
        if al.get("new_value"):
            lines.append(f"| New Value | {al['new_value']} |")
        if al.get("actor"):
            lines.append(f"| Actor | {al['actor']} |")
        lines.append(f"| Project | {al.get('project') or '-'} |")
        lines.append(f"| Created | {al['created_at']} |")
        lines.append("")
        (out / "audit_log" / f"{al_slug}.md").write_text("\n".join(lines))

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

        # Project tickets
        proj_tickets = [tk for tk in tickets if tk.get("project") == proj]
        if proj_tickets:
            lines.append("## Tickets\n")
            for tk in proj_tickets:
                tk_slug = ticket_slugs.get(tk["id"], tk["id"])
                lines.append(f"- [{tk['ticket_number']}: {tk['title']}](../tickets/{tk_slug}.md) — {tk['status']}")
            lines.append("")

        # Project incidents
        proj_incidents = [inc for inc in incidents if inc.get("project") == proj]
        if proj_incidents:
            lines.append("## Incidents\n")
            for inc in proj_incidents:
                inc_slug = incident_slugs.get(inc["id"], inc["id"])
                lines.append(f"- [{inc['title']}](../incidents/{inc_slug}.md) — {inc['severity']} / {inc['status']}")
            lines.append("")

        # Project decisions
        proj_decisions = [dec for dec in decisions if dec.get("project") == proj]
        if proj_decisions:
            lines.append("## Decisions\n")
            for dec in proj_decisions:
                dec_slug = decision_slugs.get(dec["id"], dec["id"])
                lines.append(f"- [{dec['title']}](../decisions/{dec_slug}.md) — {dec['status']}")
            lines.append("")

        # Project deployments
        proj_deployments = [dep for dep in deployments if dep.get("project") == proj]
        if proj_deployments:
            lines.append("## Deployments\n")
            for dep in proj_deployments:
                dep_slug = deployment_slugs.get(dep["id"], dep["id"])
                lines.append(f"- [{dep['version']}](../deployments/{dep_slug}.md) — {dep['status']}")
            lines.append("")

        # Project dependencies
        proj_deps = [dp for dp in dependencies if dp.get("project") == proj]
        if proj_deps:
            lines.append("## Dependencies\n")
            for dp in proj_deps:
                dp_slug = dependency_slugs.get(dp["id"], dp["id"])
                lines.append(f"- [{dp['name']}](../dependencies/{dp_slug}.md) v{dp.get('version') or '?'}")
            lines.append("")

        (out / "projects" / f"{proj_slug}.md").write_text("\n".join(lines))

    db.close()

    total = (len(sessions) + len(thoughts) + len(rules) + len(errors) + len(groups)
             + len(plans) + len(specs) + len(features) + len(components) + len(people)
             + len(teams_data) + len(tickets) + len(instructions_data) + len(attachments)
             + len(endpoints) + len(credentials) + len(environments) + len(deployments)
             + len(builds_data) + len(incidents) + len(dependencies) + len(runbooks)
             + len(decisions) + len(comments) + len(audit_log) + len(all_projects) + 1)
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
                "plans", "specs", "features", "components", "people", "teams",
                "tickets", "instructions", "attachments", "endpoints", "credentials",
                "environments", "deployments", "builds", "incidents", "dependencies",
                "runbooks", "decisions", "diagrams", "comments", "audit_log"):
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
    tickets = data.get("tickets", [])
    instructions_data = data.get("instructions", [])
    attachments = data.get("attachments", [])
    endpoints = data.get("endpoints", [])
    credentials = data.get("credentials", [])
    environments = data.get("environments", [])
    deployments = data.get("deployments", [])
    builds_data = data.get("builds", [])
    incidents = data.get("incidents", [])
    dependencies = data.get("dependencies", [])
    runbooks = data.get("runbooks", [])
    decisions = data.get("decisions", [])
    diagrams_data = data.get("diagrams", [])
    comments = data.get("comments", [])
    audit_log = data.get("audit_log", [])
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums, plans, specs, features, components, teams_data, tickets, instructions_data, endpoints, credentials, environments, deployments, builds_data, incidents, dependencies, runbooks, decisions, diagrams_data, comments)
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
    ticket_slugs = slug_maps["tickets"]
    instruction_slugs = slug_maps["instructions"]
    attachment_slugs = slug_maps["attachments"]
    endpoint_slugs = slug_maps["endpoints"]
    credential_slugs = slug_maps["credentials"]
    environment_slugs = slug_maps["environments"]
    deployment_slugs = slug_maps["deployments"]
    build_slugs = slug_maps["builds"]
    incident_slugs = slug_maps["incidents"]
    dependency_slugs = slug_maps["dependencies"]
    runbook_slugs = slug_maps["runbooks"]
    decision_slugs = slug_maps["decisions"]
    diagram_slugs = slug_maps["diagrams"]
    comment_slugs = slug_maps["comments"]
    audit_log_slugs = slug_maps["audit_log"]

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
        "tickets": ("Tickets", 14),
        "endpoints": ("Endpoints", 15),
        "credentials": ("Credentials", 16),
        "environments": ("Environments", 17),
        "deployments": ("Deployments", 18),
        "builds": ("Builds", 19),
        "incidents": ("Incidents", 20),
        "dependencies": ("Dependencies", 21),
        "runbooks": ("Runbooks", 22),
        "decisions": ("Decisions", 23),
        "instructions": ("Instructions", 24),
        "attachments": ("Attachments", 25),
        "comments": ("Comments", 26),
        "audit_log": ("Audit Log", 27),
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
            ss_decisions = _json_list(ss.get("decisions_made"))
            if ss_decisions:
                lines.append("**Decisions:**\n")
                lines.append(_bullet_list(ss_decisions))
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

    # ── Tickets ────────────────────────────────────────────────────────

    for i, tk in enumerate(tickets):
        tk_slug = ticket_slugs.get(tk["id"], tk["id"])
        fm = _front_matter(
            layout="default", title=f'{tk["ticket_number"]}: {tk["title"]}',
            parent="Tickets", nav_order=i + 1,
        )
        lines = [fm, f"# Ticket: {tk['ticket_number']} — {tk['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{tk['id']}` |")
        lines.append(f"| Number | {tk['ticket_number']} |")
        lines.append(f"| Status | {tk['status']} |")
        lines.append(f"| Priority | {tk['priority']} |")
        lines.append(f"| Type | {tk['type']} |")
        lines.append(f"| Project | {tk.get('project') or '-'} |")
        lines.append(f"| Created | {tk['created_at']} |")
        tags = _json_list(tk.get("tags"))
        if tags:
            lines.append(f"| Tags | {', '.join(tags)} |")
        lines.append("")
        if tk.get("description"):
            lines.append(f"## Description\n\n{tk['description']}\n")
        (out / "tickets" / f"{tk_slug}.md").write_text("\n".join(lines))

    # ── Endpoints ──────────────────────────────────────────────────────

    for i, ep in enumerate(endpoints):
        ep_slug = endpoint_slugs.get(ep["id"], ep["id"])
        fm = _front_matter(
            layout="default", title=f'{ep["method"]} {ep["path"]}',
            parent="Endpoints", nav_order=i + 1,
        )
        lines = [fm, f"# {ep['method']} {ep['path']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{ep['id']}` |")
        lines.append(f"| Auth | {ep['auth_type']} |")
        lines.append(f"| Status | {ep['status']} |")
        lines.append(f"| Project | {ep.get('project') or '-'} |")
        lines.append(f"| Created | {ep['created_at']} |")
        lines.append("")
        if ep.get("description"):
            lines.append(f"## Description\n\n{ep['description']}\n")
        (out / "endpoints" / f"{ep_slug}.md").write_text("\n".join(lines))

    # ── Credentials ────────────────────────────────────────────────────

    for i, cr in enumerate(credentials):
        cr_slug = credential_slugs.get(cr["id"], cr["id"])
        fm = _front_matter(
            layout="default", title=f'Credential: {cr["name"]}',
            parent="Credentials", nav_order=i + 1,
        )
        lines = [fm, f"# Credential: {cr['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{cr['id']}` |")
        lines.append(f"| Type | {cr['type']} |")
        lines.append(f"| Provider | {cr.get('provider') or '-'} |")
        lines.append(f"| Project | {cr.get('project') or '-'} |")
        lines.append(f"| Created | {cr['created_at']} |")
        lines.append("")
        if cr.get("description"):
            lines.append(f"## Description\n\n{cr['description']}\n")
        (out / "credentials" / f"{cr_slug}.md").write_text("\n".join(lines))

    # ── Environments ───────────────────────────────────────────────────

    for i, env in enumerate(environments):
        env_slug = environment_slugs.get(env["id"], env["id"])
        fm = _front_matter(
            layout="default", title=f'Environment: {env["name"]}',
            parent="Environments", nav_order=i + 1,
        )
        lines = [fm, f"# Environment: {env['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{env['id']}` |")
        lines.append(f"| Type | {env['type']} |")
        lines.append(f"| Project | {env.get('project') or '-'} |")
        lines.append(f"| Created | {env['created_at']} |")
        lines.append("")
        if env.get("description"):
            lines.append(f"## Description\n\n{env['description']}\n")
        (out / "environments" / f"{env_slug}.md").write_text("\n".join(lines))

    # ── Deployments ────────────────────────────────────────────────────

    for i, dep in enumerate(deployments):
        dep_slug = deployment_slugs.get(dep["id"], dep["id"])
        fm = _front_matter(
            layout="default", title=f'Deployment: {dep["version"]}',
            parent="Deployments", nav_order=i + 1,
        )
        lines = [fm, f"# Deployment: {dep['version']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{dep['id']}` |")
        lines.append(f"| Status | {dep['status']} |")
        lines.append(f"| Strategy | {dep['strategy']} |")
        lines.append(f"| Project | {dep.get('project') or '-'} |")
        lines.append(f"| Created | {dep['created_at']} |")
        lines.append("")
        if dep.get("description"):
            lines.append(f"## Description\n\n{dep['description']}\n")
        (out / "deployments" / f"{dep_slug}.md").write_text("\n".join(lines))

    # ── Builds ─────────────────────────────────────────────────────────

    for i, bd in enumerate(builds_data):
        bd_slug = build_slugs.get(bd["id"], bd["id"])
        fm = _front_matter(
            layout="default", title=f'Build: {bd["name"]}',
            parent="Builds", nav_order=i + 1,
        )
        lines = [fm, f"# Build: {bd['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{bd['id']}` |")
        lines.append(f"| Pipeline | {bd.get('pipeline') or '-'} |")
        lines.append(f"| Status | {bd['status']} |")
        lines.append(f"| Trigger | {bd['trigger_type']} |")
        lines.append(f"| Project | {bd.get('project') or '-'} |")
        lines.append(f"| Created | {bd['created_at']} |")
        lines.append("")
        (out / "builds" / f"{bd_slug}.md").write_text("\n".join(lines))

    # ── Incidents ──────────────────────────────────────────────────────

    for i, inc in enumerate(incidents):
        inc_slug = incident_slugs.get(inc["id"], inc["id"])
        fm = _front_matter(
            layout="default", title=f'Incident: {inc["title"]}',
            parent="Incidents", nav_order=i + 1,
        )
        lines = [fm, f"# Incident: {inc['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{inc['id']}` |")
        lines.append(f"| Severity | {inc['severity']} |")
        lines.append(f"| Status | {inc['status']} |")
        lines.append(f"| Project | {inc.get('project') or '-'} |")
        lines.append(f"| Created | {inc['created_at']} |")
        lines.append("")
        if inc.get("description"):
            lines.append(f"## Description\n\n{inc['description']}\n")
        if inc.get("root_cause"):
            lines.append(f"## Root Cause\n\n{inc['root_cause']}\n")
        if inc.get("resolution"):
            lines.append(f"## Resolution\n\n{inc['resolution']}\n")
        (out / "incidents" / f"{inc_slug}.md").write_text("\n".join(lines))

    # ── Dependencies ───────────────────────────────────────────────────

    for i, dp in enumerate(dependencies):
        dp_slug = dependency_slugs.get(dp["id"], dp["id"])
        fm = _front_matter(
            layout="default", title=f'Dependency: {dp["name"]}',
            parent="Dependencies", nav_order=i + 1,
        )
        lines = [fm, f"# Dependency: {dp['name']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{dp['id']}` |")
        lines.append(f"| Version | {dp.get('version') or '-'} |")
        lines.append(f"| Type | {dp['type']} |")
        lines.append(f"| Project | {dp.get('project') or '-'} |")
        lines.append(f"| Created | {dp['created_at']} |")
        lines.append("")
        if dp.get("description"):
            lines.append(f"## Description\n\n{dp['description']}\n")
        (out / "dependencies" / f"{dp_slug}.md").write_text("\n".join(lines))

    # ── Runbooks ───────────────────────────────────────────────────────

    for i, rb in enumerate(runbooks):
        rb_slug = runbook_slugs.get(rb["id"], rb["id"])
        fm = _front_matter(
            layout="default", title=f'Runbook: {rb["title"]}',
            parent="Runbooks", nav_order=i + 1,
        )
        lines = [fm, f"# Runbook: {rb['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{rb['id']}` |")
        lines.append(f"| Project | {rb.get('project') or '-'} |")
        lines.append(f"| Created | {rb['created_at']} |")
        lines.append("")
        if rb.get("description"):
            lines.append(f"## Description\n\n{rb['description']}\n")
        steps = _json_list(rb.get("steps"))
        if steps:
            lines.append("## Steps\n")
            for j, step in enumerate(steps, 1):
                lines.append(f"{j}. {step}")
            lines.append("")
        (out / "runbooks" / f"{rb_slug}.md").write_text("\n".join(lines))

    # ── Decisions ──────────────────────────────────────────────────────

    for i, dec in enumerate(decisions):
        dec_slug = decision_slugs.get(dec["id"], dec["id"])
        fm = _front_matter(
            layout="default", title=f'Decision: {dec["title"]}',
            parent="Decisions", nav_order=i + 1,
        )
        lines = [fm, f"# Decision: {dec['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{dec['id']}` |")
        lines.append(f"| Status | {dec['status']} |")
        lines.append(f"| Project | {dec.get('project') or '-'} |")
        lines.append(f"| Created | {dec['created_at']} |")
        lines.append("")
        if dec.get("context"):
            lines.append(f"## Context\n\n{dec['context']}\n")
        if dec.get("outcome"):
            lines.append(f"## Outcome\n\n{dec['outcome']}\n")
        (out / "decisions" / f"{dec_slug}.md").write_text("\n".join(lines))

    # ── Diagrams ──────────────────────────────────────────────────────

    for i, diag in enumerate(diagrams_data):
        diag_slug = diagram_slugs.get(diag["id"], diag["id"])
        fm = _front_matter(
            layout="default", title=f'Diagram: {diag["title"]}',
            parent="Diagrams", nav_order=i + 1,
        )
        lines = [fm, f"# Diagram: {diag['title']}\n"]
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| ID | `{diag['id']}` |")
        lines.append(f"| Type | {diag['diagram_type']} |")
        lines.append(f"| Project | {diag.get('project') or '-'} |")
        lines.append(f"| Created | {diag['created_at']} |")
        lines.append("")
        if diag.get("description"):
            lines.append(f"## Description\n\n{diag['description']}\n")
        if diag.get("definition"):
            dtype = diag["diagram_type"]
            if dtype == "mermaid":
                lines.append(f"## Diagram\n\n```mermaid\n{diag['definition']}\n```\n")
            else:
                lines.append(f"## Definition\n\n```json\n{diag['definition']}\n```\n")
        (out / "diagrams" / f"{diag_slug}.md").write_text("\n".join(lines))

    # ── Instructions ───────────────────────────────────────────────────

    for i, ins in enumerate(instructions_data):
        ins_slug = instruction_slugs.get(ins["id"], ins["id"])
        fm = _front_matter(
            layout="default", title=f'Instruction: {ins["title"]}',
            parent="Instructions", nav_order=i + 1,
        )
        lines = [fm, f"# Instruction: {ins['title']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{ins['id']}` |")
        lines.append(f"| Section | {ins['section']} |")
        lines.append(f"| Priority | {ins['priority']} |")
        lines.append(f"| Scope | {ins['scope']} |")
        lines.append(f"| Active | {'Yes' if ins.get('active') else 'No'} |")
        lines.append(f"| Created | {ins['created_at']} |")
        lines.append("")
        if ins.get("content"):
            lines.append(f"## Content\n\n{ins['content']}\n")
        (out / "instructions" / f"{ins_slug}.md").write_text("\n".join(lines))

    # ── Attachments ────────────────────────────────────────────────────

    for i, att in enumerate(attachments):
        att_slug = attachment_slugs.get(att["id"], att["id"])
        fm = _front_matter(
            layout="default", title=f'Attachment: {att.get("label") or att["id"]}',
            parent="Attachments", nav_order=i + 1,
        )
        lines = [fm, f"# Attachment: {att.get('label') or att['id']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{att['id']}` |")
        lines.append(f"| Entity | {att['entity_type']} `{att['entity_id']}` |")
        lines.append(f"| URL | {att['url']} |")
        lines.append(f"| Type | {att['type']} |")
        lines.append(f"| Created | {att['created_at']} |")
        lines.append("")
        if att.get("description"):
            lines.append(f"## Description\n\n{att['description']}\n")
        (out / "attachments" / f"{att_slug}.md").write_text("\n".join(lines))

    # ── Comments ───────────────────────────────────────────────────────

    for i, cm in enumerate(comments):
        cm_slug = comment_slugs.get(cm["id"], cm["id"])
        fm = _front_matter(
            layout="default", title=f'Comment by {cm.get("author") or "Unknown"}',
            parent="Comments", nav_order=i + 1,
        )
        lines = [fm, f"# Comment by {cm.get('author') or 'Unknown'}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{cm['id']}` |")
        lines.append(f"| Entity | {cm['entity_type']} `{cm['entity_id']}` |")
        lines.append(f"| Author | {cm.get('author') or '-'} |")
        lines.append(f"| Created | {cm['created_at']} |")
        lines.append("")
        if cm.get("content"):
            lines.append(f"## Content\n\n{cm['content']}\n")
        (out / "comments" / f"{cm_slug}.md").write_text("\n".join(lines))

    # ── Audit Log ──────────────────────────────────────────────────────

    for i, al in enumerate(audit_log):
        al_slug = audit_log_slugs.get(al["id"], al["id"])
        fm = _front_matter(
            layout="default", title=f'{al["action"]} {al["entity_type"]}',
            parent="Audit Log", nav_order=i + 1,
        )
        lines = [fm, f"# Audit: {al['action']} {al['entity_type']}\n"]
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{al['id']}` |")
        lines.append(f"| Entity | {al['entity_type']} `{al['entity_id']}` |")
        lines.append(f"| Action | {al['action']} |")
        if al.get("actor"):
            lines.append(f"| Actor | {al['actor']} |")
        lines.append(f"| Created | {al['created_at']} |")
        lines.append("")
        (out / "audit_log" / f"{al_slug}.md").write_text("\n".join(lines))

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
             + len(teams_data) + len(tickets) + len(instructions_data) + len(attachments)
             + len(endpoints) + len(credentials) + len(environments) + len(deployments)
             + len(builds_data) + len(incidents) + len(dependencies) + len(runbooks)
             + len(decisions) + len(comments) + len(audit_log) + len(all_projects) + 1)
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
/* Diagrams */
.diagram-container {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin: 16px 0;
  min-height: 200px;
  overflow: auto;
}
.diagram-container canvas { max-width: 100%; }
.diagram-container svg { max-width: 100%; height: auto; }
pre.mermaid {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin: 16px 0;
}
.diagram-source { margin-top: 12px; }
.diagram-source summary { cursor: pointer; color: var(--text-muted); font-size: 0.9em; }
.diagram-source pre { margin-top: 8px; }
#network-graph svg { width: 100%; min-height: 400px; }
#network-graph .node circle { stroke: var(--border); stroke-width: 1.5px; }
#network-graph .node text { fill: var(--text); font-size: 11px; }
#network-graph .link { stroke: var(--border); stroke-opacity: 0.6; }
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
    extra_head: str = "",
    extra_body_end: str = "",
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
        ("Tickets", "tickets/index.html", "tickets"),
        ("Endpoints", "endpoints/index.html", "endpoints"),
        ("Credentials", "credentials/index.html", "credentials"),
        ("Environments", "environments/index.html", "environments"),
        ("Deployments", "deployments/index.html", "deployments"),
        ("Builds", "builds/index.html", "builds"),
        ("Incidents", "incidents/index.html", "incidents"),
        ("Dependencies", "dependencies/index.html", "dependencies"),
        ("Runbooks", "runbooks/index.html", "runbooks"),
        ("Decisions", "decisions/index.html", "decisions"),
        ("Diagrams", "diagrams/index.html", "diagrams"),
        ("Instructions", "instructions/index.html", "instructions"),
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
{extra_head}</head>
<body>
<button class="sidebar-toggle" onclick="document.getElementById('sidebar').classList.toggle('open')">&#9776;</button>
{"".join(sidebar_html)}
<div class="main">
<div class="breadcrumbs">{bc_html}</div>
{content}
</div>
<script src="{base}/search.js"></script>
{extra_body_end}</body>
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
                "plans", "specs", "features", "components", "people", "teams",
                "tickets", "instructions", "attachments", "endpoints", "credentials",
                "environments", "deployments", "builds", "incidents", "dependencies",
                "runbooks", "decisions", "diagrams", "comments", "audit_log"):
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
    tickets = data.get("tickets", [])
    instructions_data = data.get("instructions", [])
    attachments = data.get("attachments", [])
    endpoints = data.get("endpoints", [])
    credentials = data.get("credentials", [])
    environments = data.get("environments", [])
    deployments = data.get("deployments", [])
    builds_data = data.get("builds", [])
    incidents = data.get("incidents", [])
    dependencies = data.get("dependencies", [])
    runbooks = data.get("runbooks", [])
    decisions = data.get("decisions", [])
    diagrams_data = data.get("diagrams", [])
    comments = data.get("comments", [])
    audit_log = data.get("audit_log", [])
    all_projects = _collect_projects(thoughts, rules, sessions, project_sums, plans, specs, features, components, teams_data, tickets, instructions_data, endpoints, credentials, environments, deployments, builds_data, incidents, dependencies, runbooks, decisions, diagrams_data, comments)
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
    ticket_slugs = slug_maps["tickets"]
    instruction_slugs = slug_maps["instructions"]
    attachment_slugs = slug_maps["attachments"]
    endpoint_slugs = slug_maps["endpoints"]
    credential_slugs = slug_maps["credentials"]
    environment_slugs = slug_maps["environments"]
    deployment_slugs = slug_maps["deployments"]
    build_slugs = slug_maps["builds"]
    incident_slugs = slug_maps["incidents"]
    dependency_slugs = slug_maps["dependencies"]
    runbook_slugs = slug_maps["runbooks"]
    decision_slugs = slug_maps["decisions"]
    diagram_slugs = slug_maps["diagrams"]
    comment_slugs = slug_maps["comments"]
    audit_log_slugs = slug_maps["audit_log"]

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
        "tickets": len(tickets),
        "instructions": len(instructions_data),
        "attachments": len(attachments),
        "endpoints": len(endpoints),
        "credentials": len(credentials),
        "environments": len(environments),
        "deployments": len(deployments),
        "builds": len(builds_data),
        "incidents": len(incidents),
        "dependencies": len(dependencies),
        "runbooks": len(runbooks),
        "decisions": len(decisions),
        "diagrams": len(diagrams_data),
        "comments": len(comments),
        "audit_log": len(audit_log),
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
            ss_decisions = _json_list(ss.get("decisions_made"))
            if ss_decisions:
                h.append('<p><strong>Decisions:</strong></p><ul>' + "".join(f"<li>{_esc(d)}</li>" for d in ss_decisions) + "</ul>")
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

    # ── Tickets ────────────────────────────────────────────────────────

    tki = ['<h1>Tickets</h1>']
    tki.append('<table><thead><tr><th>Number</th><th>Title</th><th>Status</th><th>Priority</th><th>Type</th><th>Project</th></tr></thead><tbody>')
    for tk in tickets:
        tk_slug = ticket_slugs.get(tk["id"], tk["id"])
        tki.append(f'<tr><td>{_esc(tk["ticket_number"])}</td>'
                   f'<td><a href="{tk_slug}.html">{_esc(tk["title"])}</a></td>'
                   f'<td>{_html_tag(tk["status"])}</td><td>{_html_tag(tk["priority"], tk["priority"])}</td>'
                   f'<td>{_html_tag(tk["type"])}</td>'
                   f'<td>{_esc(tk.get("project") or "-")}</td></tr>')
    tki.append('</tbody></table>')
    page = _html_page("Tickets", "\n".join(tki),
                      breadcrumbs=[("Home", "../index.html"), ("Tickets", "")],
                      sidebar_counts=sidebar_counts, active_section="tickets", depth=1)
    (out / "tickets" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for tk in tickets:
        tk_slug = ticket_slugs.get(tk["id"], tk["id"])
        h = [f'<h1>Ticket: {_esc(tk["ticket_number"])} &mdash; {_esc(tk["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(tk["id"])}</code>'),
            ("Number", _esc(tk["ticket_number"])),
            ("Status", _esc(tk["status"])),
            ("Priority", _esc(tk["priority"])),
            ("Type", _esc(tk["type"])),
            ("Project", _esc(tk.get("project") or "-")),
            ("Created", _esc(tk["created_at"])),
        ]
        if tk.get("assignee_id"):
            a_slug = people_slugs.get(tk["assignee_id"], tk["assignee_id"])
            meta.append(("Assignee", f'<a href="../people/{a_slug}.html">{_esc(tk["assignee_id"])}</a>'))
        if tk.get("reporter_id"):
            r_slug = people_slugs.get(tk["reporter_id"], tk["reporter_id"])
            meta.append(("Reporter", f'<a href="../people/{r_slug}.html">{_esc(tk["reporter_id"])}</a>'))
        if tk.get("due_date"):
            meta.append(("Due", _esc(tk["due_date"])))
        tags = _json_list(tk.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if tk.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(tk["description"])}</div>')
        page = _html_page(f'Ticket: {tk["ticket_number"]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Tickets", "index.html"), (tk["ticket_number"], "")],
                          sidebar_counts=sidebar_counts, active_section="tickets", depth=1)
        (out / "tickets" / f"{tk_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Endpoints ──────────────────────────────────────────────────────

    epi = ['<h1>Endpoints</h1>']
    epi.append('<table><thead><tr><th>Method</th><th>Path</th><th>Auth</th><th>Status</th><th>Project</th></tr></thead><tbody>')
    for ep in endpoints:
        ep_slug = endpoint_slugs.get(ep["id"], ep["id"])
        epi.append(f'<tr><td>{_html_tag(ep["method"])}</td>'
                   f'<td><a href="{ep_slug}.html">{_esc(ep["path"])}</a></td>'
                   f'<td>{_esc(ep["auth_type"])}</td><td>{_html_tag(ep["status"])}</td>'
                   f'<td>{_esc(ep.get("project") or "-")}</td></tr>')
    epi.append('</tbody></table>')
    page = _html_page("Endpoints", "\n".join(epi),
                      breadcrumbs=[("Home", "../index.html"), ("Endpoints", "")],
                      sidebar_counts=sidebar_counts, active_section="endpoints", depth=1)
    (out / "endpoints" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for ep in endpoints:
        ep_slug = endpoint_slugs.get(ep["id"], ep["id"])
        h = [f'<h1>{_esc(ep["method"])} {_esc(ep["path"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(ep["id"])}</code>'),
            ("Method", _esc(ep["method"])),
            ("Path", _esc(ep["path"])),
            ("Base URL", _esc(ep.get("base_url") or "-")),
            ("Auth", _esc(ep["auth_type"])),
            ("Status", _esc(ep["status"])),
            ("Project", _esc(ep.get("project") or "-")),
            ("Created", _esc(ep["created_at"])),
        ]
        if ep.get("rate_limit"):
            meta.append(("Rate Limit", _esc(ep["rate_limit"])))
        tags = _json_list(ep.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if ep.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(ep["description"])}</div>')
        page = _html_page(f'{ep["method"]} {ep["path"]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Endpoints", "index.html"), (f'{ep["method"]} {ep["path"][:30]}', "")],
                          sidebar_counts=sidebar_counts, active_section="endpoints", depth=1)
        (out / "endpoints" / f"{ep_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Credentials ────────────────────────────────────────────────────

    cri = ['<h1>Credentials</h1>']
    cri.append('<table><thead><tr><th>Name</th><th>Type</th><th>Provider</th><th>Project</th><th>Expires</th></tr></thead><tbody>')
    for cr in credentials:
        cr_slug = credential_slugs.get(cr["id"], cr["id"])
        cri.append(f'<tr><td><a href="{cr_slug}.html">{_esc(cr["name"])}</a></td>'
                   f'<td>{_html_tag(cr["type"])}</td>'
                   f'<td>{_esc(cr.get("provider") or "-")}</td>'
                   f'<td>{_esc(cr.get("project") or "-")}</td>'
                   f'<td>{_esc(cr.get("expires_at") or "-")}</td></tr>')
    cri.append('</tbody></table>')
    page = _html_page("Credentials", "\n".join(cri),
                      breadcrumbs=[("Home", "../index.html"), ("Credentials", "")],
                      sidebar_counts=sidebar_counts, active_section="credentials", depth=1)
    (out / "credentials" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for cr in credentials:
        cr_slug = credential_slugs.get(cr["id"], cr["id"])
        h = [f'<h1>Credential: {_esc(cr["name"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(cr["id"])}</code>'),
            ("Type", _esc(cr["type"])),
            ("Provider", _esc(cr.get("provider") or "-")),
            ("Project", _esc(cr.get("project") or "-")),
            ("Created", _esc(cr["created_at"])),
        ]
        if cr.get("vault_path"):
            meta.append(("Vault Path", _esc(cr["vault_path"])))
        if cr.get("env_var"):
            meta.append(("Env Var", f'<code>{_esc(cr["env_var"])}</code>'))
        if cr.get("last_rotated"):
            meta.append(("Last Rotated", _esc(cr["last_rotated"])))
        if cr.get("expires_at"):
            meta.append(("Expires", _esc(cr["expires_at"])))
        tags = _json_list(cr.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if cr.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(cr["description"])}</div>')
        page = _html_page(f'Credential: {cr["name"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Credentials", "index.html"), (cr["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="credentials", depth=1)
        (out / "credentials" / f"{cr_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Environments ───────────────────────────────────────────────────

    evi = ['<h1>Environments</h1>']
    evi.append('<table><thead><tr><th>Name</th><th>Type</th><th>URL</th><th>Project</th></tr></thead><tbody>')
    for env in environments:
        env_slug = environment_slugs.get(env["id"], env["id"])
        evi.append(f'<tr><td><a href="{env_slug}.html">{_esc(env["name"])}</a></td>'
                   f'<td>{_html_tag(env["type"])}</td>'
                   f'<td>{_esc(env.get("url") or "-")}</td>'
                   f'<td>{_esc(env.get("project") or "-")}</td></tr>')
    evi.append('</tbody></table>')
    page = _html_page("Environments", "\n".join(evi),
                      breadcrumbs=[("Home", "../index.html"), ("Environments", "")],
                      sidebar_counts=sidebar_counts, active_section="environments", depth=1)
    (out / "environments" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for env in environments:
        env_slug = environment_slugs.get(env["id"], env["id"])
        h = [f'<h1>Environment: {_esc(env["name"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(env["id"])}</code>'),
            ("Type", _esc(env["type"])),
            ("URL", _esc(env.get("url") or "-")),
            ("Project", _esc(env.get("project") or "-")),
            ("Created", _esc(env["created_at"])),
        ]
        tags = _json_list(env.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if env.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(env["description"])}</div>')
        page = _html_page(f'Environment: {env["name"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Environments", "index.html"), (env["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="environments", depth=1)
        (out / "environments" / f"{env_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Deployments ────────────────────────────────────────────────────

    dpi = ['<h1>Deployments</h1>']
    dpi.append('<table><thead><tr><th>Version</th><th>Status</th><th>Strategy</th><th>Project</th><th>Deployed</th></tr></thead><tbody>')
    for dep in deployments:
        dep_slug = deployment_slugs.get(dep["id"], dep["id"])
        dpi.append(f'<tr><td><a href="{dep_slug}.html">{_esc(dep["version"])}</a></td>'
                   f'<td>{_html_tag(dep["status"])}</td><td>{_esc(dep["strategy"])}</td>'
                   f'<td>{_esc(dep.get("project") or "-")}</td>'
                   f'<td>{_esc((dep.get("deployed_at") or "")[:10])}</td></tr>')
    dpi.append('</tbody></table>')
    page = _html_page("Deployments", "\n".join(dpi),
                      breadcrumbs=[("Home", "../index.html"), ("Deployments", "")],
                      sidebar_counts=sidebar_counts, active_section="deployments", depth=1)
    (out / "deployments" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for dep in deployments:
        dep_slug = deployment_slugs.get(dep["id"], dep["id"])
        h = [f'<h1>Deployment: {_esc(dep["version"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(dep["id"])}</code>'),
            ("Version", _esc(dep["version"])),
            ("Status", _esc(dep["status"])),
            ("Strategy", _esc(dep["strategy"])),
            ("Project", _esc(dep.get("project") or "-")),
            ("Created", _esc(dep["created_at"])),
        ]
        if dep.get("environment_id"):
            env_s = environment_slugs.get(dep["environment_id"], dep["environment_id"])
            meta.append(("Environment", f'<a href="../environments/{env_s}.html">{_esc(dep["environment_id"])}</a>'))
        if dep.get("deployed_by"):
            meta.append(("Deployed By", _esc(dep["deployed_by"])))
        if dep.get("deployed_at"):
            meta.append(("Deployed At", _esc(dep["deployed_at"])))
        tags = _json_list(dep.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if dep.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(dep["description"])}</div>')
        page = _html_page(f'Deployment: {dep["version"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Deployments", "index.html"), (dep["version"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="deployments", depth=1)
        (out / "deployments" / f"{dep_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Builds ─────────────────────────────────────────────────────────

    bdi = ['<h1>Builds</h1>']
    bdi.append('<table><thead><tr><th>Name</th><th>Pipeline</th><th>Status</th><th>Trigger</th><th>Project</th><th>Duration</th></tr></thead><tbody>')
    for bd in builds_data:
        bd_slug = build_slugs.get(bd["id"], bd["id"])
        dur = f'{bd["duration_seconds"]}s' if bd.get("duration_seconds") else "-"
        bdi.append(f'<tr><td><a href="{bd_slug}.html">{_esc(bd["name"])}</a></td>'
                   f'<td>{_esc(bd.get("pipeline") or "-")}</td>'
                   f'<td>{_html_tag(bd["status"])}</td><td>{_esc(bd["trigger_type"])}</td>'
                   f'<td>{_esc(bd.get("project") or "-")}</td><td>{_esc(dur)}</td></tr>')
    bdi.append('</tbody></table>')
    page = _html_page("Builds", "\n".join(bdi),
                      breadcrumbs=[("Home", "../index.html"), ("Builds", "")],
                      sidebar_counts=sidebar_counts, active_section="builds", depth=1)
    (out / "builds" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for bd in builds_data:
        bd_slug = build_slugs.get(bd["id"], bd["id"])
        h = [f'<h1>Build: {_esc(bd["name"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(bd["id"])}</code>'),
            ("Pipeline", _esc(bd.get("pipeline") or "-")),
            ("Status", _esc(bd["status"])),
            ("Trigger", _esc(bd["trigger_type"])),
            ("Project", _esc(bd.get("project") or "-")),
            ("Created", _esc(bd["created_at"])),
        ]
        if bd.get("commit_sha"):
            meta.append(("Commit", f'<code>{_esc(bd["commit_sha"])}</code>'))
        if bd.get("branch"):
            meta.append(("Branch", _esc(bd["branch"])))
        if bd.get("duration_seconds"):
            meta.append(("Duration", f'{bd["duration_seconds"]}s'))
        if bd.get("artifact_url"):
            meta.append(("Artifact", _esc(bd["artifact_url"])))
        tags = _json_list(bd.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        page = _html_page(f'Build: {bd["name"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Builds", "index.html"), (bd["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="builds", depth=1)
        (out / "builds" / f"{bd_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Incidents ──────────────────────────────────────────────────────

    ini = ['<h1>Incidents</h1>']
    ini.append('<table><thead><tr><th>Title</th><th>Severity</th><th>Status</th><th>Project</th><th>Started</th></tr></thead><tbody>')
    for inc in incidents:
        inc_slug = incident_slugs.get(inc["id"], inc["id"])
        ini.append(f'<tr><td><a href="{inc_slug}.html">{_esc(inc["title"])}</a></td>'
                   f'<td>{_html_tag(inc["severity"], inc["severity"])}</td>'
                   f'<td>{_html_tag(inc["status"])}</td>'
                   f'<td>{_esc(inc.get("project") or "-")}</td>'
                   f'<td>{_esc((inc.get("started_at") or "")[:10])}</td></tr>')
    ini.append('</tbody></table>')
    page = _html_page("Incidents", "\n".join(ini),
                      breadcrumbs=[("Home", "../index.html"), ("Incidents", "")],
                      sidebar_counts=sidebar_counts, active_section="incidents", depth=1)
    (out / "incidents" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for inc in incidents:
        inc_slug = incident_slugs.get(inc["id"], inc["id"])
        h = [f'<h1>Incident: {_esc(inc["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(inc["id"])}</code>'),
            ("Severity", _esc(inc["severity"])),
            ("Status", _esc(inc["status"])),
            ("Project", _esc(inc.get("project") or "-")),
            ("Created", _esc(inc["created_at"])),
        ]
        if inc.get("lead_id"):
            l_slug = people_slugs.get(inc["lead_id"], inc["lead_id"])
            meta.append(("Lead", f'<a href="../people/{l_slug}.html">{_esc(inc["lead_id"])}</a>'))
        if inc.get("started_at"):
            meta.append(("Started", _esc(inc["started_at"])))
        if inc.get("resolved_at"):
            meta.append(("Resolved", _esc(inc["resolved_at"])))
        tags = _json_list(inc.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if inc.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(inc["description"])}</div>')
        if inc.get("root_cause"):
            h.append(f'<h2>Root Cause</h2><div class="content-block">{_md(inc["root_cause"])}</div>')
        if inc.get("resolution"):
            h.append(f'<h2>Resolution</h2><div class="content-block">{_md(inc["resolution"])}</div>')
        timeline = _json_list(inc.get("timeline"))
        if timeline:
            h.append('<h2>Timeline</h2><ul>' + "".join(f"<li>{_esc(t)}</li>" for t in timeline) + "</ul>")
        page = _html_page(f'Incident: {inc["title"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Incidents", "index.html"), (inc["title"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="incidents", depth=1)
        (out / "incidents" / f"{inc_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Dependencies ───────────────────────────────────────────────────

    ddi = ['<h1>Dependencies</h1>']
    ddi.append('<table><thead><tr><th>Name</th><th>Version</th><th>Type</th><th>License</th><th>Project</th></tr></thead><tbody>')
    for dp in dependencies:
        dp_slug = dependency_slugs.get(dp["id"], dp["id"])
        ddi.append(f'<tr><td><a href="{dp_slug}.html">{_esc(dp["name"])}</a></td>'
                   f'<td>{_esc(dp.get("version") or "-")}</td>'
                   f'<td>{_html_tag(dp["type"])}</td>'
                   f'<td>{_esc(dp.get("license") or "-")}</td>'
                   f'<td>{_esc(dp.get("project") or "-")}</td></tr>')
    ddi.append('</tbody></table>')
    page = _html_page("Dependencies", "\n".join(ddi),
                      breadcrumbs=[("Home", "../index.html"), ("Dependencies", "")],
                      sidebar_counts=sidebar_counts, active_section="dependencies", depth=1)
    (out / "dependencies" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for dp in dependencies:
        dp_slug = dependency_slugs.get(dp["id"], dp["id"])
        h = [f'<h1>Dependency: {_esc(dp["name"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(dp["id"])}</code>'),
            ("Version", _esc(dp.get("version") or "-")),
            ("Type", _esc(dp["type"])),
            ("Project", _esc(dp.get("project") or "-")),
            ("Created", _esc(dp["created_at"])),
        ]
        if dp.get("source"):
            meta.append(("Source", _esc(dp["source"])))
        if dp.get("license"):
            meta.append(("License", _esc(dp["license"])))
        if dp.get("pinned_version"):
            meta.append(("Pinned", _esc(dp["pinned_version"])))
        if dp.get("latest_version"):
            meta.append(("Latest", _esc(dp["latest_version"])))
        tags = _json_list(dp.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if dp.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(dp["description"])}</div>')
        page = _html_page(f'Dependency: {dp["name"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Dependencies", "index.html"), (dp["name"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="dependencies", depth=1)
        (out / "dependencies" / f"{dp_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Runbooks ───────────────────────────────────────────────────────

    rbi = ['<h1>Runbooks</h1>']
    rbi.append('<table><thead><tr><th>Title</th><th>Project</th><th>Last Executed</th></tr></thead><tbody>')
    for rb in runbooks:
        rb_slug = runbook_slugs.get(rb["id"], rb["id"])
        rbi.append(f'<tr><td><a href="{rb_slug}.html">{_esc(rb["title"])}</a></td>'
                   f'<td>{_esc(rb.get("project") or "-")}</td>'
                   f'<td>{_esc(rb.get("last_executed") or "-")}</td></tr>')
    rbi.append('</tbody></table>')
    page = _html_page("Runbooks", "\n".join(rbi),
                      breadcrumbs=[("Home", "../index.html"), ("Runbooks", "")],
                      sidebar_counts=sidebar_counts, active_section="runbooks", depth=1)
    (out / "runbooks" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for rb in runbooks:
        rb_slug = runbook_slugs.get(rb["id"], rb["id"])
        h = [f'<h1>Runbook: {_esc(rb["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(rb["id"])}</code>'),
            ("Project", _esc(rb.get("project") or "-")),
            ("Created", _esc(rb["created_at"])),
        ]
        if rb.get("trigger_conditions"):
            meta.append(("Trigger", _esc(rb["trigger_conditions"])))
        if rb.get("last_executed"):
            meta.append(("Last Executed", _esc(rb["last_executed"])))
        tags = _json_list(rb.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if rb.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(rb["description"])}</div>')
        steps = _json_list(rb.get("steps"))
        if steps:
            h.append('<h2>Steps</h2><ol>' + "".join(f"<li>{_esc(s)}</li>" for s in steps) + "</ol>")
        page = _html_page(f'Runbook: {rb["title"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Runbooks", "index.html"), (rb["title"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="runbooks", depth=1)
        (out / "runbooks" / f"{rb_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Decisions ──────────────────────────────────────────────────────

    dci = ['<h1>Decisions</h1>']
    dci.append('<table><thead><tr><th>Title</th><th>Status</th><th>Project</th><th>Decided</th></tr></thead><tbody>')
    for dec in decisions:
        dec_slug = decision_slugs.get(dec["id"], dec["id"])
        dci.append(f'<tr><td><a href="{dec_slug}.html">{_esc(dec["title"])}</a></td>'
                   f'<td>{_html_tag(dec["status"])}</td>'
                   f'<td>{_esc(dec.get("project") or "-")}</td>'
                   f'<td>{_esc((dec.get("decided_at") or "")[:10])}</td></tr>')
    dci.append('</tbody></table>')
    page = _html_page("Decisions", "\n".join(dci),
                      breadcrumbs=[("Home", "../index.html"), ("Decisions", "")],
                      sidebar_counts=sidebar_counts, active_section="decisions", depth=1)
    (out / "decisions" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for dec in decisions:
        dec_slug = decision_slugs.get(dec["id"], dec["id"])
        h = [f'<h1>Decision: {_esc(dec["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(dec["id"])}</code>'),
            ("Status", _esc(dec["status"])),
            ("Project", _esc(dec.get("project") or "-")),
            ("Created", _esc(dec["created_at"])),
        ]
        if dec.get("author_id"):
            a_slug = people_slugs.get(dec["author_id"], dec["author_id"])
            meta.append(("Author", f'<a href="../people/{a_slug}.html">{_esc(dec["author_id"])}</a>'))
        if dec.get("decided_at"):
            meta.append(("Decided", _esc(dec["decided_at"])))
        if dec.get("superseded_by"):
            meta.append(("Superseded By", _esc(dec["superseded_by"])))
        tags = _json_list(dec.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if dec.get("context"):
            h.append(f'<h2>Context</h2><div class="content-block">{_md(dec["context"])}</div>')
        options = _json_list(dec.get("options"))
        if options:
            h.append('<h2>Options</h2><ul>' + "".join(f"<li>{_esc(o)}</li>" for o in options) + "</ul>")
        if dec.get("outcome"):
            h.append(f'<h2>Outcome</h2><div class="content-block">{_md(dec["outcome"])}</div>')
        if dec.get("consequences"):
            h.append(f'<h2>Consequences</h2><div class="content-block">{_md(dec["consequences"])}</div>')
        page = _html_page(f'Decision: {dec["title"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Decisions", "index.html"), (dec["title"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="decisions", depth=1)
        (out / "decisions" / f"{dec_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Diagrams ──────────────────────────────────────────────────────

    dgi = ['<h1>Diagrams</h1>']
    dgi.append('<table><thead><tr><th>Title</th><th>Type</th><th>Project</th><th>Updated</th></tr></thead><tbody>')
    for diag in diagrams_data:
        diag_slug = diagram_slugs.get(diag["id"], diag["id"])
        dgi.append(f'<tr><td><a href="{diag_slug}.html">{_esc(diag["title"])}</a></td>'
                   f'<td>{_html_tag(diag["diagram_type"])}</td>'
                   f'<td>{_esc(diag.get("project") or "-")}</td>'
                   f'<td>{_esc(diag["updated_at"][:10])}</td></tr>')
    dgi.append('</tbody></table>')
    page = _html_page("Diagrams", "\n".join(dgi),
                      breadcrumbs=[("Home", "../index.html"), ("Diagrams", "")],
                      sidebar_counts=sidebar_counts, active_section="diagrams", depth=1)
    (out / "diagrams" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for diag in diagrams_data:
        diag_slug = diagram_slugs.get(diag["id"], diag["id"])
        dtype = diag["diagram_type"]
        h = [f'<h1>Diagram: {_esc(diag["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(diag["id"])}</code>'),
            ("Type", _html_tag(dtype)),
            ("Project", _esc(diag.get("project") or "-")),
            ("Created", _esc(diag["created_at"])),
            ("Updated", _esc(diag["updated_at"])),
        ]
        tags = _json_list(diag.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if diag.get("description"):
            h.append(f'<h2>Description</h2><div class="content-block">{_md(diag["description"])}</div>')

        defn = diag.get("definition", "")
        extra_head = ""
        extra_body_end = ""
        safe_id = diag["id"].replace("-", "").replace("_", "")[:16]

        if defn:
            if dtype == "mermaid":
                h.append(f'<h2>Diagram</h2><pre class="mermaid">{defn}</pre>')
                extra_head = '<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>'
                extra_body_end = '<script>mermaid.initialize({startOnLoad:true, theme:"dark"});</script>'
            elif dtype == "chart":
                h.append(f'<h2>Chart</h2><div class="diagram-container"><canvas id="chart-{safe_id}"></canvas></div>')
                extra_head = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>'
                extra_body_end = f'<script>new Chart(document.getElementById("chart-{safe_id}"), {defn});</script>'
            elif dtype in ("network", "servicemap"):
                h.append(f'<h2>{"Service Map" if dtype == "servicemap" else "Network Graph"}</h2>'
                         f'<div class="diagram-container" id="network-graph"></div>')
                extra_head = '<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>'
                extra_body_end = f"""<script>
(function() {{
  var data = {defn};
  var nodes = data.nodes || [];
  var links = (data.edges || data.links || []).map(function(e) {{
    return {{source: e.source || e.from, target: e.target || e.to, label: e.label || ""}};
  }});
  var container = document.getElementById("network-graph");
  var width = container.clientWidth || 800;
  var height = Math.max(400, nodes.length * 20);
  var svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  var sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(function(d) {{ return d.id; }}).distance(120))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width/2, height/2));
  var link = svg.append("g").selectAll("line").data(links).join("line")
    .attr("class", "link").attr("stroke", "#555").attr("stroke-opacity", 0.6);
  var node = svg.append("g").selectAll("g").data(nodes).join("g").call(
    d3.drag().on("start", function(e,d) {{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
      .on("drag", function(e,d) {{ d.fx=e.x; d.fy=e.y; }})
      .on("end", function(e,d) {{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }})
  );
  node.append("circle").attr("r", 8).attr("fill", function(d) {{ return d.color || "#58a6ff"; }});
  node.append("text").text(function(d) {{ return d.label || d.id; }})
    .attr("dx", 12).attr("dy", 4).attr("fill", "#c9d1d9").style("font-size", "11px");
  sim.on("tick", function() {{
    link.attr("x1",function(d){{return d.source.x;}}).attr("y1",function(d){{return d.source.y;}})
        .attr("x2",function(d){{return d.target.x;}}).attr("y2",function(d){{return d.target.y;}});
    node.attr("transform", function(d) {{ return "translate("+d.x+","+d.y+")"; }});
  }});
}})();
</script>"""
            elif dtype == "table":
                # Render as HTML table from JSON
                try:
                    tdata = json.loads(defn)
                    cols = tdata.get("columns", [])
                    rows = tdata.get("rows", [])
                    th = "<tr>" + "".join(f"<th>{_esc(str(c))}</th>" for c in cols) + "</tr>"
                    tbody = ""
                    for row in rows:
                        if isinstance(row, dict):
                            cells = "".join(f"<td>{_esc(str(row.get(c, '')))}</td>" for c in cols)
                        elif isinstance(row, list):
                            cells = "".join(f"<td>{_esc(str(v))}</td>" for v in row)
                        else:
                            cells = f"<td>{_esc(str(row))}</td>"
                        tbody += f"<tr>{cells}</tr>"
                    h.append(f'<h2>Table</h2><table><thead>{th}</thead><tbody>{tbody}</tbody></table>')
                except (ValueError, TypeError):
                    h.append(f'<h2>Definition</h2><div class="content-block"><pre><code>{_esc(defn)}</code></pre></div>')

            # Show raw source in collapsible details
            h.append(f'<details class="diagram-source"><summary>View source</summary>'
                     f'<pre><code>{_esc(defn)}</code></pre></details>')

        page = _html_page(f'Diagram: {diag["title"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Diagrams", "index.html"), (diag["title"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="diagrams", depth=1,
                          extra_head=extra_head, extra_body_end=extra_body_end)
        (out / "diagrams" / f"{diag_slug}.html").write_text(page, encoding="utf-8")
        file_count += 1

    # ── Instructions ───────────────────────────────────────────────────

    isi = ['<h1>Instructions</h1>']
    isi.append('<table><thead><tr><th>Title</th><th>Section</th><th>Priority</th><th>Scope</th><th>Active</th></tr></thead><tbody>')
    for ins in instructions_data:
        ins_slug = instruction_slugs.get(ins["id"], ins["id"])
        active = "Yes" if ins.get("active") else "No"
        isi.append(f'<tr><td><a href="{ins_slug}.html">{_esc(ins["title"])}</a></td>'
                   f'<td>{_esc(ins["section"])}</td>'
                   f'<td>{_html_tag(ins["priority"], ins["priority"])}</td>'
                   f'<td>{_esc(ins["scope"])}</td><td>{_esc(active)}</td></tr>')
    isi.append('</tbody></table>')
    page = _html_page("Instructions", "\n".join(isi),
                      breadcrumbs=[("Home", "../index.html"), ("Instructions", "")],
                      sidebar_counts=sidebar_counts, active_section="instructions", depth=1)
    (out / "instructions" / "index.html").write_text(page, encoding="utf-8")
    file_count += 1

    for ins in instructions_data:
        ins_slug = instruction_slugs.get(ins["id"], ins["id"])
        h = [f'<h1>Instruction: {_esc(ins["title"])}</h1>']
        meta = [
            ("ID", f'<code>{_esc(ins["id"])}</code>'),
            ("Section", _esc(ins["section"])),
            ("Priority", _esc(ins["priority"])),
            ("Scope", _esc(ins["scope"])),
            ("Active", "Yes" if ins.get("active") else "No"),
            ("Position", str(ins["position"])),
            ("Project", _esc(ins.get("project") or "-")),
            ("Created", _esc(ins["created_at"])),
        ]
        tags = _json_list(ins.get("tags"))
        if tags:
            meta.append(("Tags", " ".join(_html_tag(t) for t in tags)))
        h.append(_html_meta_table(meta))
        if ins.get("content"):
            h.append(f'<h2>Content</h2><div class="content-block">{_md(ins["content"])}</div>')
        page = _html_page(f'Instruction: {ins["title"][:60]}', "\n".join(h),
                          breadcrumbs=[("Home", "../index.html"), ("Instructions", "index.html"), (ins["title"][:40], "")],
                          sidebar_counts=sidebar_counts, active_section="instructions", depth=1)
        (out / "instructions" / f"{ins_slug}.html").write_text(page, encoding="utf-8")
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
    for tk in tickets:
        tk_slug = ticket_slugs.get(tk["id"], tk["id"])
        search_items.append({
            "type": "ticket", "id": tk["id"],
            "title": f'{tk["ticket_number"]}: {tk["title"]}',
            "content": (tk.get("description") or "")[:300],
            "keywords": _json_list(tk.get("tags")),
            "url": f"tickets/{tk_slug}.html",
        })
    for ep in endpoints:
        ep_slug = endpoint_slugs.get(ep["id"], ep["id"])
        search_items.append({
            "type": "endpoint", "id": ep["id"],
            "title": f'{ep["method"]} {ep["path"]}',
            "content": (ep.get("description") or "")[:300],
            "keywords": _json_list(ep.get("tags")),
            "url": f"endpoints/{ep_slug}.html",
        })
    for inc in incidents:
        inc_slug = incident_slugs.get(inc["id"], inc["id"])
        search_items.append({
            "type": "incident", "id": inc["id"],
            "title": inc["title"],
            "content": (inc.get("description") or "")[:300],
            "keywords": _json_list(inc.get("tags")),
            "url": f"incidents/{inc_slug}.html",
        })
    for dec in decisions:
        dec_slug = decision_slugs.get(dec["id"], dec["id"])
        search_items.append({
            "type": "decision", "id": dec["id"],
            "title": dec["title"],
            "content": (dec.get("context") or "")[:300],
            "keywords": _json_list(dec.get("tags")),
            "url": f"decisions/{dec_slug}.html",
        })
    for rb in runbooks:
        rb_slug = runbook_slugs.get(rb["id"], rb["id"])
        search_items.append({
            "type": "runbook", "id": rb["id"],
            "title": rb["title"],
            "content": (rb.get("description") or "")[:300],
            "keywords": _json_list(rb.get("tags")),
            "url": f"runbooks/{rb_slug}.html",
        })
    for ins in instructions_data:
        ins_slug = instruction_slugs.get(ins["id"], ins["id"])
        search_items.append({
            "type": "instruction", "id": ins["id"],
            "title": ins["title"],
            "content": (ins.get("content") or "")[:300],
            "keywords": _json_list(ins.get("tags")),
            "url": f"instructions/{ins_slug}.html",
        })
    for dp in dependencies:
        dp_slug = dependency_slugs.get(dp["id"], dp["id"])
        search_items.append({
            "type": "dependency", "id": dp["id"],
            "title": dp["name"],
            "content": (dp.get("description") or "")[:300],
            "keywords": _json_list(dp.get("tags")),
            "url": f"dependencies/{dp_slug}.html",
        })
    for cr in credentials:
        cr_slug = credential_slugs.get(cr["id"], cr["id"])
        search_items.append({
            "type": "credential", "id": cr["id"],
            "title": cr["name"],
            "content": (cr.get("description") or "")[:300],
            "keywords": _json_list(cr.get("tags")),
            "url": f"credentials/{cr_slug}.html",
        })
    for diag in diagrams_data:
        diag_slug = diagram_slugs.get(diag["id"], diag["id"])
        search_items.append({
            "type": "diagram", "id": diag["id"],
            "title": diag["title"],
            "content": (diag.get("description") or "")[:300],
            "keywords": _json_list(diag.get("tags")),
            "url": f"diagrams/{diag_slug}.html",
        })

    (out / "search-index.json").write_text(json.dumps(search_items, ensure_ascii=False, indent=None), encoding="utf-8")
    file_count += 1

    db.close()

    return Path(output_dir), file_count


def export_pdf(
    db_path: Optional[str] = None,
    output_file: str = "memgram-export.pdf",
    project: Optional[str] = None,
) -> Path:
    """Export memgram database as a spacious, readable PDF report.

    Uses reportlab to generate a landscape PDF with generous sizing for
    charts, diagrams, and tables. Chart.js configs are rendered as native
    bar/line/pie charts via reportlab graphics.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        Image,
        NextPageTemplate,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    PAGE = landscape(letter)
    PAGE_W, PAGE_H = PAGE
    MARGIN = 0.6 * inch

    db, data = _fetch_all_data(db_path, project=project)

    sessions = data["sessions"]
    thoughts = data["thoughts"]
    rules = data["rules"]
    errors = data["errors"]
    groups = data["groups"]
    plans = data.get("plans", [])
    plan_tasks = data.get("plan_tasks", [])
    specs = data.get("specs", [])
    features = data.get("features", [])
    components = data.get("components", [])
    people = data.get("people", [])
    teams_data = data.get("teams", [])
    tickets = data.get("tickets", [])
    instructions_data = data.get("instructions", [])
    endpoints = data.get("endpoints", [])
    credentials = data.get("credentials", [])
    environments = data.get("environments", [])
    deployments = data.get("deployments", [])
    builds_data = data.get("builds", [])
    incidents = data.get("incidents", [])
    dependencies = data.get("dependencies", [])
    runbooks = data.get("runbooks", [])
    decisions = data.get("decisions", [])
    diagrams_data = data.get("diagrams", [])
    comments = data.get("comments", [])
    audit_log = data.get("audit_log", [])

    tasks_by_plan: dict[str, list] = {}
    for t in plan_tasks:
        tasks_by_plan.setdefault(t["plan_id"], []).append(t)

    db.close()

    # ── Styles ────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    # Dark palette
    BG = colors.HexColor("#0d1117")
    SURFACE = colors.HexColor("#161b22")
    BORDER = colors.HexColor("#30363d")
    TEXT = colors.HexColor("#c9d1d9")
    TEXT_MUTED = colors.HexColor("#8b949e")
    ACCENT = colors.HexColor("#58a6ff")
    GREEN = colors.HexColor("#3fb950")
    RED = colors.HexColor("#f85149")
    ORANGE = colors.HexColor("#d29922")
    PURPLE = colors.HexColor("#bc8cff")

    CHART_COLORS = [
        colors.HexColor("#58a6ff"),
        colors.HexColor("#3fb950"),
        colors.HexColor("#f85149"),
        colors.HexColor("#d29922"),
        colors.HexColor("#bc8cff"),
        colors.HexColor("#f778ba"),
        colors.HexColor("#79c0ff"),
        colors.HexColor("#56d364"),
    ]

    sTitle = ParagraphStyle("PDFTitle", fontName="Helvetica-Bold", fontSize=28,
                            textColor=ACCENT, spaceAfter=20, alignment=TA_CENTER)
    sSubtitle = ParagraphStyle("PDFSubtitle", fontName="Helvetica", fontSize=14,
                               textColor=TEXT_MUTED, spaceAfter=30, alignment=TA_CENTER)
    sH1 = ParagraphStyle("PDFH1", fontName="Helvetica-Bold", fontSize=22,
                         textColor=ACCENT, spaceBefore=24, spaceAfter=14)
    sH2 = ParagraphStyle("PDFH2", fontName="Helvetica-Bold", fontSize=16,
                         textColor=colors.HexColor("#79c0ff"), spaceBefore=18, spaceAfter=10)
    sH3 = ParagraphStyle("PDFH3", fontName="Helvetica-Bold", fontSize=13,
                         textColor=TEXT, spaceBefore=12, spaceAfter=6)
    sBody = ParagraphStyle("PDFBody", fontName="Helvetica", fontSize=10,
                           textColor=TEXT, leading=14, spaceAfter=6)
    sBodySmall = ParagraphStyle("PDFBodySmall", fontName="Helvetica", fontSize=9,
                                textColor=TEXT_MUTED, leading=12, spaceAfter=4)
    sCode = ParagraphStyle("PDFCode", fontName="Courier", fontSize=8,
                           textColor=TEXT, leading=10, spaceAfter=6,
                           backColor=SURFACE, borderColor=BORDER,
                           borderWidth=0.5, borderPadding=6)
    sStat = ParagraphStyle("PDFStat", fontName="Helvetica-Bold", fontSize=20,
                           textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2)
    sStatLabel = ParagraphStyle("PDFStatLabel", fontName="Helvetica", fontSize=11,
                                textColor=TEXT_MUTED, alignment=TA_CENTER, spaceAfter=8)

    content_width = PAGE_W - 2 * MARGIN - 12  # 12pt for Frame internal padding (6pt each side)

    def _safe(text: Any) -> str:
        """Escape text for reportlab Paragraph XML."""
        if text is None:
            return ""
        s = str(text)
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return s

    def _md_inline(s: str) -> str:
        """Convert inline markdown to reportlab XML (expects already-escaped text)."""
        # 1. Extract inline code spans first to protect their contents
        code_spans: list[str] = []
        def _stash_code(m):
            code_spans.append(m.group(1))
            return f"\x00CODE{len(code_spans) - 1}\x00"
        s = re.sub(r'`([^`]+?)`', _stash_code, s)
        # 2. Bold: **text** (skip __ to avoid __cplusplus false matches)
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        # 3. Italic: *text* (not inside words)
        s = re.sub(r'(?<!\w)\*([^*]+?)\*(?!\w)', r'<i>\1</i>', s)
        # 4. Restore code spans
        for idx, code in enumerate(code_spans):
            s = s.replace(f"\x00CODE{idx}\x00", f'<font face="Courier" size="9">{code}</font>')
        return s

    def _md_to_story(text: str) -> list:
        """Convert markdown-ish text to a list of reportlab flowables."""
        if not text or not text.strip():
            return []

        elements = []
        lines = text.split('\n')
        i = 0
        para_buf = []  # accumulate regular text lines

        def flush_para():
            if para_buf:
                combined = ' '.join(para_buf)
                combined = _md_inline(_safe(combined))
                elements.append(Paragraph(combined, sBody))
                para_buf.clear()

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Code block
            if stripped.startswith('```'):
                flush_para()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(_safe(lines[i]))
                    i += 1
                if code_lines:
                    code_text = '<br/>'.join(code_lines)
                    elements.append(Paragraph(code_text, sCode))
                i += 1
                continue

            # Headers
            if stripped.startswith('#### '):
                flush_para()
                elements.append(Paragraph(f"<b>{_safe(stripped[5:])}</b>", sBody))
                i += 1
                continue
            if stripped.startswith('### '):
                flush_para()
                elements.append(Paragraph(_safe(stripped[4:]), sH3))
                i += 1
                continue
            if stripped.startswith('## '):
                flush_para()
                elements.append(Paragraph(_safe(stripped[3:]), sH3))
                i += 1
                continue
            if stripped.startswith('# '):
                flush_para()
                elements.append(Paragraph(_safe(stripped[2:]), sH3))
                i += 1
                continue

            # Bullet lists
            if re.match(r'^[-*+]\s', stripped):
                flush_para()
                bullet_text = _md_inline(_safe(stripped[2:]))
                sBullet = ParagraphStyle("Bullet", parent=sBody, leftIndent=16,
                                          bulletIndent=4, bulletFontName="Helvetica",
                                          bulletFontSize=10, bulletColor=TEXT_MUTED,
                                          spaceBefore=2, spaceAfter=2)
                elements.append(Paragraph(bullet_text, sBullet, bulletText='\u2022'))
                i += 1
                continue

            # Numbered lists
            m = re.match(r'^(\d+)[.)]\s+(.*)', stripped)
            if m:
                flush_para()
                num = m.group(1)
                item_text = _md_inline(_safe(m.group(2)))
                sNumbered = ParagraphStyle("Numbered", parent=sBody, leftIndent=20,
                                            bulletIndent=0, spaceBefore=2, spaceAfter=2)
                elements.append(Paragraph(f"<b>{num}.</b> {item_text}", sNumbered))
                i += 1
                continue

            # Horizontal rule
            if stripped in ('---', '***', '___'):
                flush_para()
                from reportlab.platypus import HRFlowable
                elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER,
                                            spaceAfter=6, spaceBefore=6))
                i += 1
                continue

            # Empty line = paragraph break
            if not stripped:
                flush_para()
                elements.append(Spacer(1, 4))
                i += 1
                continue

            # Regular text - accumulate
            para_buf.append(stripped)
            i += 1

        flush_para()
        return elements

    def _trunc(text: Any, maxlen: int = 120) -> str:
        s = _safe(text)
        return s[:maxlen] + "..." if len(s) > maxlen else s

    def _make_table(headers: list[str], rows: list[list], col_widths: list | None = None) -> Table:
        """Build a styled Table with dark theme."""
        header_row = [Paragraph(f"<b>{_safe(h)}</b>", ParagraphStyle("TH", fontName="Helvetica-Bold",
                      fontSize=9, textColor=colors.white, leading=12)) for h in headers]
        data_rows = []
        for row in rows:
            data_rows.append([
                Paragraph(_safe(str(c)), ParagraphStyle("TD", fontName="Helvetica",
                          fontSize=9, textColor=TEXT, leading=12))
                for c in row
            ])

        tdata = [header_row] + data_rows
        t = Table(tdata, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#21262d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 1), (-1, -1), SURFACE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SURFACE, colors.HexColor("#1c2128")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    def _render_chart(defn_str: str, title: str) -> list:
        """Render a Chart.js config as a reportlab Drawing."""
        from reportlab.graphics import renderPDF
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.charts.linecharts import HorizontalLineChart
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.shapes import Drawing, Rect, String

        try:
            cfg = json.loads(defn_str) if isinstance(defn_str, str) else defn_str
        except (json.JSONDecodeError, TypeError):
            return [Paragraph(f"<i>Could not parse chart config</i>", sBodySmall)]

        chart_type = cfg.get("type", "bar").lower()
        chart_data = cfg.get("data", {})
        labels = chart_data.get("labels", [])
        datasets = chart_data.get("datasets", [])

        # Big generous sizing
        draw_w = content_width
        max_draw_h = PAGE_H - 2 * MARGIN - 60
        draw_h = min(400, max_draw_h)

        d = Drawing(draw_w, draw_h)

        # Background
        d.add(Rect(0, 0, draw_w, draw_h, fillColor=SURFACE, strokeColor=BORDER, strokeWidth=1))

        # Chart title
        d.add(String(draw_w / 2, draw_h - 25, title, fontSize=14,
                      fillColor=ACCENT, textAnchor="middle", fontName="Helvetica-Bold"))

        if chart_type in ("bar", "horizontalbar"):
            chart = VerticalBarChart()
            chart.x = 80
            chart.y = 60
            chart.width = draw_w - 160
            chart.height = draw_h - 120
            chart.data = []
            for ds in datasets:
                vals = ds.get("data", [])
                chart.data.append(vals)
            if labels:
                chart.categoryAxis.categoryNames = labels
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 10
            chart.categoryAxis.labels.fillColor = TEXT
            chart.categoryAxis.strokeColor = BORDER
            chart.categoryAxis.tickDown = 0
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 10
            chart.valueAxis.labels.fillColor = TEXT
            chart.valueAxis.strokeColor = BORDER
            chart.valueAxis.gridStrokeColor = BORDER
            chart.valueAxis.gridStrokeWidth = 0.5
            chart.valueAxis.visibleGrid = 1
            for i, ds in enumerate(datasets):
                color = CHART_COLORS[i % len(CHART_COLORS)]
                bg = ds.get("backgroundColor")
                if isinstance(bg, str) and bg.startswith("#"):
                    color = colors.HexColor(bg)
                chart.bars[i].fillColor = color
                chart.bars[i].strokeColor = None
            chart.barWidth = max(8, min(40, int((draw_w - 160) / max(len(labels), 1) / max(len(datasets), 1) * 0.6)))
            d.add(chart)

            # Legend
            leg_y = 30
            leg_x = 80
            for i, ds in enumerate(datasets):
                c = CHART_COLORS[i % len(CHART_COLORS)]
                bg = ds.get("backgroundColor")
                if isinstance(bg, str) and bg.startswith("#"):
                    c = colors.HexColor(bg)
                d.add(Rect(leg_x, leg_y, 12, 12, fillColor=c, strokeColor=None))
                d.add(String(leg_x + 16, leg_y + 2, ds.get("label", f"Dataset {i+1}"),
                             fontSize=10, fillColor=TEXT, fontName="Helvetica"))
                leg_x += 150

        elif chart_type in ("line", "scatter"):
            chart = HorizontalLineChart()
            chart.x = 80
            chart.y = 60
            chart.width = draw_w - 160
            chart.height = draw_h - 120
            chart.data = []
            for ds in datasets:
                vals = ds.get("data", [])
                chart.data.append(vals)
            if labels:
                chart.categoryAxis.categoryNames = labels
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 10
            chart.categoryAxis.labels.fillColor = TEXT
            chart.categoryAxis.strokeColor = BORDER
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 10
            chart.valueAxis.labels.fillColor = TEXT
            chart.valueAxis.strokeColor = BORDER
            chart.valueAxis.gridStrokeColor = BORDER
            chart.valueAxis.gridStrokeWidth = 0.5
            chart.valueAxis.visibleGrid = 1
            for i, ds in enumerate(datasets):
                c = CHART_COLORS[i % len(CHART_COLORS)]
                bc = ds.get("borderColor")
                if isinstance(bc, str) and bc.startswith("#"):
                    c = colors.HexColor(bc)
                chart.lines[i].strokeColor = c
                chart.lines[i].strokeWidth = 2.5
            d.add(chart)

        elif chart_type in ("pie", "doughnut"):
            pie = Pie()
            pie.x = (draw_w - 280) / 2
            pie.y = 60
            pie.width = 280
            pie.height = 280
            if datasets:
                pie.data = datasets[0].get("data", [])
            for i in range(len(pie.data)):
                pie.slices[i].fillColor = CHART_COLORS[i % len(CHART_COLORS)]
                pie.slices[i].strokeColor = SURFACE
                pie.slices[i].strokeWidth = 2
            if labels:
                pie.labels = labels
                pie.sideLabels = 1
                pie.slices.fontName = "Helvetica"
                pie.slices.fontSize = 10
                pie.slices.fontColor = TEXT
            d.add(pie)

        else:
            d.add(String(draw_w / 2, draw_h / 2, f"Unsupported chart type: {chart_type}",
                         fontSize=12, fillColor=TEXT_MUTED, textAnchor="middle"))

        return [d, Spacer(1, 12)]

    def _render_network(defn_str: str, title: str) -> list:
        """Render a network/servicemap as a static node-link diagram."""
        from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String

        try:
            cfg = json.loads(defn_str) if isinstance(defn_str, str) else defn_str
        except (json.JSONDecodeError, TypeError):
            return [Paragraph(f"<i>Could not parse network config</i>", sBodySmall)]

        nodes = cfg.get("nodes", [])
        edges = cfg.get("edges", cfg.get("links", []))

        draw_w = content_width
        max_draw_h = PAGE_H - 2 * MARGIN - 60
        draw_h = min(max_draw_h, max(350, len(nodes) * 60))

        d = Drawing(draw_w, draw_h)
        d.add(Rect(0, 0, draw_w, draw_h, fillColor=SURFACE, strokeColor=BORDER, strokeWidth=1))
        d.add(String(draw_w / 2, draw_h - 25, title, fontSize=14,
                      fillColor=ACCENT, textAnchor="middle", fontName="Helvetica-Bold"))

        if not nodes:
            d.add(String(draw_w / 2, draw_h / 2, "(no nodes)", fontSize=12,
                         fillColor=TEXT_MUTED, textAnchor="middle"))
            return [d, Spacer(1, 12)]

        # Simple circular layout
        import math
        cx, cy = draw_w / 2, (draw_h - 50) / 2 + 10
        radius = min(cx - 100, cy - 60)
        n = len(nodes)
        positions = {}
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / n - math.pi / 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            positions[node["id"]] = (x, y)

        # Edges
        for edge in edges:
            src = edge.get("source") or edge.get("from")
            tgt = edge.get("target") or edge.get("to")
            if src in positions and tgt in positions:
                x1, y1 = positions[src]
                x2, y2 = positions[tgt]
                d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#484f58"),
                           strokeWidth=1.5))
                lbl = edge.get("label")
                if lbl:
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    d.add(String(mx, my + 8, str(lbl), fontSize=8,
                                 fillColor=TEXT_MUTED, textAnchor="middle"))

        # Nodes
        for node in nodes:
            nid = node["id"]
            x, y = positions[nid]
            nc = node.get("color")
            fill = colors.HexColor(nc) if nc and nc.startswith("#") else ACCENT
            d.add(Circle(x, y, 16, fillColor=fill, strokeColor=BORDER, strokeWidth=1.5))
            label = node.get("label") or nid
            d.add(String(x, y - 28, str(label), fontSize=10, fillColor=TEXT,
                         textAnchor="middle", fontName="Helvetica-Bold"))

        return [d, Spacer(1, 12)]

    def _render_mermaid(defn: str, title: str = "") -> list:
        """Render mermaid diagram – try mmdc CLI first, fall back to source."""
        import subprocess
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix='.mmd', mode='w', delete=False) as f:
                f.write(defn)
                mmd_path = f.name
            png_path = mmd_path.replace('.mmd', '.png')
            result = subprocess.run(
                ['mmdc', '-i', mmd_path, '-o', png_path, '-t', 'dark',
                 '-b', '#0d1117', '-w', '1600'],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(png_path):
                from reportlab.lib.utils import ImageReader
                ir = ImageReader(png_path)
                iw, ih = ir.getSize()
                aspect = ih / iw
                img_w = min(content_width, iw)
                img_h = img_w * aspect
                max_h = PAGE_H - 2 * MARGIN - 80
                if img_h > max_h:
                    img_h = max_h
                    img_w = img_h / aspect
                img = Image(png_path, width=img_w, height=img_h)
                return [img, Spacer(1, 12)]
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        # Fallback: show full source as styled code block
        lines = defn.strip().split("\n")
        code = "<br/>".join(_safe(l) for l in lines)
        return [
            Paragraph("<b>Mermaid Diagram Source</b>", sH3),
            Paragraph(code, sCode),
            Spacer(1, 8),
        ]

    # ── Build story ───────────────────────────────────────────────────
    story: list = []

    # Cover page
    story.append(Spacer(1, 100))
    story.append(Paragraph("Memgram Export", sTitle))
    proj_label = f"Project: {project}" if project else "All Projects"
    story.append(Paragraph(proj_label, sSubtitle))

    from datetime import datetime
    story.append(Paragraph(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", sSubtitle))
    story.append(Spacer(1, 40))

    # Stats grid on cover
    stat_items = []
    for label, count in [
        ("Sessions", len(sessions)),
        ("Thoughts", len(thoughts)),
        ("Rules", len(rules)),
        ("Errors", len(errors)),
        ("Plans", len(plans)),
        ("Specs", len(specs)),
        ("Features", len(features)),
        ("Components", len(components)),
        ("People", len(people)),
        ("Teams", len(teams_data)),
        ("Tickets", len(tickets)),
        ("Diagrams", len(diagrams_data)),
        ("Instructions", len(instructions_data)),
        ("Endpoints", len(endpoints)),
        ("Decisions", len(decisions)),
        ("Incidents", len(incidents)),
        ("Dependencies", len(dependencies)),
        ("Deployments", len(deployments)),
        ("Builds", len(builds_data)),
        ("Runbooks", len(runbooks)),
    ]:
        if count > 0:
            stat_items.append((label, count))
    stat_rows = []
    nums = []
    labels_row = []
    for label, count in stat_items:
        nums.append(Paragraph(f"<b>{count}</b>", sStat))
        labels_row.append(Paragraph(label, sStatLabel))
    cols_per_row = 5
    for row_start in range(0, len(nums), cols_per_row):
        chunk_n = nums[row_start:row_start + cols_per_row]
        chunk_l = labels_row[row_start:row_start + cols_per_row]
        while len(chunk_n) < cols_per_row:
            chunk_n.append(Paragraph("", sBody))
            chunk_l.append(Paragraph("", sBody))
        stat_rows.append(chunk_n)
        stat_rows.append(chunk_l)

    cw = content_width / cols_per_row
    st = Table(stat_rows, colWidths=[cw] * cols_per_row)
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(st)
    story.append(PageBreak())

    # ── Table of Contents ─────────────────────────────────────────────
    story.append(Paragraph("Contents", sH1))
    toc_items = []
    if sessions: toc_items.append(("Sessions", "sessions"))
    if thoughts: toc_items.append(("Thoughts", "thoughts"))
    if rules: toc_items.append(("Rules", "rules"))
    if errors: toc_items.append(("Error Patterns", "errors"))
    if plans: toc_items.append(("Plans", "plans"))
    if specs: toc_items.append(("Specs", "specs"))
    if features: toc_items.append(("Features", "features"))
    if components: toc_items.append(("Components", "components"))
    if people: toc_items.append(("People", "people"))
    if teams_data: toc_items.append(("Teams", "teams"))
    if tickets: toc_items.append(("Tickets", "tickets"))
    if diagrams_data: toc_items.append(("Diagrams", "diagrams"))
    if instructions_data: toc_items.append(("Instructions", "instructions"))
    if endpoints: toc_items.append(("Endpoints", "endpoints"))
    if decisions: toc_items.append(("Decisions", "decisions"))
    if deployments: toc_items.append(("Deployments", "deployments"))
    if builds_data: toc_items.append(("Builds", "builds"))
    if incidents: toc_items.append(("Incidents", "incidents"))
    if dependencies: toc_items.append(("Dependencies", "dependencies"))
    if runbooks: toc_items.append(("Runbooks", "runbooks"))
    for i, (item, anchor) in enumerate(toc_items, 1):
        story.append(Paragraph(f'{i}. <a href="#{anchor}" color="#58a6ff">{item}</a>', ParagraphStyle(
            "TOC", fontName="Helvetica", fontSize=13, textColor=TEXT,
            leading=20, leftIndent=20)))
    story.append(PageBreak())

    # ── helper: separator line between detail items ─────────────────
    def _detail_sep():
        from reportlab.platypus import HRFlowable
        return HRFlowable(width="100%", thickness=0.5, color=BORDER,
                          spaceBefore=8, spaceAfter=8)

    # ── Sessions ──────────────────────────────────────────────────────
    if sessions:
        story.append(Paragraph(f'<a name="sessions"/>Sessions ({len(sessions)})', sH1))
        rows = []
        for s in sessions:
            rows.append([
                (s.get("started_at") or "")[:10],
                s.get("agent_type") or "-",
                s.get("model") or "-",
                s.get("project") or "-",
                _trunc(s.get("goal") or "-", 200),
                s.get("status") or "-",
            ])
        story.append(_make_table(
            ["Date", "Agent", "Model", "Project", "Goal", "Status"],
            rows,
            col_widths=[1.0*inch, 1.2*inch, 1.8*inch, 1.2*inch, 3.5*inch, 0.9*inch],
        ))
        # Detail: sessions with summaries
        sessions_with_summary = [s for s in sessions if s.get("summary")]
        if sessions_with_summary:
            story.append(Spacer(1, 16))
            story.append(Paragraph("Session Summaries", sH2))
            for s in sessions_with_summary:
                story.append(_detail_sep())
                goal = _safe(s.get("goal") or "Untitled Session")
                date = (s.get("started_at") or "")[:10]
                story.append(Paragraph(f"{goal}", sH3))
                story.extend(_md_to_story(s["summary"]))
                story.append(Paragraph(
                    f"Date: {date} | Project: {_safe(s.get('project') or 'global')} | "
                    f"Model: {_safe(s.get('model') or '-')}",
                    sBodySmall))
        story.append(PageBreak())

    # ── Thoughts ──────────────────────────────────────────────────────
    if thoughts:
        story.append(Paragraph(f'<a name="thoughts"/>Thoughts ({len(thoughts)})', sH1))
        rows = []
        for t in thoughts:
            rows.append([
                t.get("type") or "-",
                _trunc(t.get("summary") or "-", 250),
                t.get("project") or "global",
                (t.get("created_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Type", "Summary", "Project", "Created"],
            rows,
            col_widths=[1.2*inch, 5.5*inch, 1.5*inch, 1.0*inch],
        ))
        # Detail: full thought content
        thoughts_with_content = [t for t in thoughts if t.get("content")]
        if thoughts_with_content:
            story.append(PageBreak())
            story.append(Paragraph("Thought Details", sH2))
            for t in thoughts_with_content:
                story.append(_detail_sep())
                story.append(Paragraph(_safe(t.get("summary") or "Untitled Thought"), sH3))
                story.extend(_md_to_story(t["content"]))
                story.append(Paragraph(
                    f"Type: {_safe(t.get('type') or '-')} | "
                    f"Project: {_safe(t.get('project') or 'global')} | "
                    f"Created: {(t.get('created_at') or '')[:10]}",
                    sBodySmall))
        story.append(PageBreak())

    # ── Rules ─────────────────────────────────────────────────────────
    if rules:
        story.append(Paragraph(f'<a name="rules"/>Rules ({len(rules)})', sH1))
        rows = []
        for r in rules:
            pin = "[P] " if r.get("pinned") else ""
            rows.append([
                r.get("severity") or "-",
                r.get("type") or "-",
                f"{pin}{_trunc(r.get('summary') or '-', 220)}",
                str(r.get("reinforcement_count", 0)),
                r.get("project") or "global",
            ])
        story.append(_make_table(
            ["Severity", "Type", "Summary", "Reinforced", "Project"],
            rows,
            col_widths=[1.0*inch, 1.2*inch, 4.8*inch, 1.0*inch, 1.2*inch],
        ))
        # Detail: full rule content
        rules_with_content = [r for r in rules if r.get("content")]
        if rules_with_content:
            story.append(PageBreak())
            story.append(Paragraph("Rule Details", sH2))
            for r in rules_with_content:
                story.append(_detail_sep())
                pin = "[Pinned] " if r.get("pinned") else ""
                story.append(Paragraph(f"{pin}{_safe(r.get('summary') or 'Untitled Rule')}", sH3))
                story.extend(_md_to_story(r["content"]))
                story.append(Paragraph(
                    f"Severity: {_safe(r.get('severity') or '-')} | "
                    f"Type: {_safe(r.get('type') or '-')} | "
                    f"Project: {_safe(r.get('project') or 'global')} | "
                    f"Condition: {_safe(r.get('condition') or '-')}",
                    sBodySmall))
        story.append(PageBreak())

    # ── Errors ────────────────────────────────────────────────────────
    if errors:
        story.append(Paragraph(f'<a name="errors"/>Error Patterns ({len(errors)})', sH1))
        rows = []
        for e in errors:
            rows.append([
                _trunc(e.get("error_description") or "-", 200),
                _trunc(e.get("root_cause") or "-", 200),
                _trunc(e.get("fix") or "-", 200),
                str(e.get("occurrence_count", 0)),
                (e.get("created_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Error", "Root Cause", "Fix", "Count", "First Seen"],
            rows,
            col_widths=[2.8*inch, 2.3*inch, 2.3*inch, 0.7*inch, 1.0*inch],
        ))
        # Detail: full error descriptions
        story.append(PageBreak())
        story.append(Paragraph("Error Pattern Details", sH2))
        for e in errors:
            story.append(_detail_sep())
            story.append(Paragraph(
                _safe(e.get("error_description") or "Unknown Error"), sH3))
            if e.get("error_description"):
                story.append(Paragraph("<b>Description:</b>", sBody))
                story.extend(_md_to_story(e['error_description']))
            if e.get("cause"):
                story.append(Paragraph("<b>Cause:</b>", sBody))
                story.extend(_md_to_story(e['cause']))
            if e.get("root_cause"):
                story.append(Paragraph("<b>Root Cause:</b>", sBody))
                story.extend(_md_to_story(e['root_cause']))
            if e.get("fix"):
                story.append(Paragraph("<b>Fix:</b>", sBody))
                story.extend(_md_to_story(e['fix']))
            story.append(Paragraph(
                f"Occurrences: {e.get('occurrence_count', 0)} | "
                f"First seen: {(e.get('created_at') or '')[:10]} | "
                f"Project: {_safe(e.get('project') or 'global')}",
                sBodySmall))
        story.append(PageBreak())

    # ── Plans ─────────────────────────────────────────────────────────
    if plans:
        story.append(Paragraph(f'<a name="plans"/>Plans ({len(plans)})', sH1))
        for plan in plans:
            story.append(Paragraph(_safe(plan.get("title") or "Untitled Plan"), sH2))
            meta = [
                ("Status", plan.get("status") or "-"),
                ("Project", plan.get("project") or "global"),
                ("Created", (plan.get("created_at") or "")[:10]),
            ]
            meta_rows = [[k, v] for k, v in meta]
            story.append(_make_table(["Field", "Value"], meta_rows,
                         col_widths=[1.5*inch, 4*inch]))
            if plan.get("description"):
                story.append(Spacer(1, 6))
                story.extend(_md_to_story(plan["description"]))
            ptasks = tasks_by_plan.get(plan["id"], [])
            if ptasks:
                story.append(Spacer(1, 6))
                story.append(Paragraph("Tasks", sH3))
                task_rows = []
                for pt in ptasks:
                    done = "Done" if pt.get("done") else "Open"
                    task_rows.append([
                        str(pt.get("position", "")),
                        _trunc(pt.get("title") or "-", 60),
                        done,
                    ])
                story.append(_make_table(["#", "Task", "Status"], task_rows,
                             col_widths=[0.5*inch, 5*inch, 1*inch]))
            story.append(Spacer(1, 14))
        story.append(PageBreak())

    # ── Specs ─────────────────────────────────────────────────────────
    if specs:
        story.append(Paragraph(f'<a name="specs"/>Specs ({len(specs)})', sH1))
        rows = []
        for s in specs:
            rows.append([
                _trunc(s.get("title") or "-", 50),
                s.get("status") or "-",
                s.get("project") or "global",
                (s.get("updated_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Title", "Status", "Project", "Updated"],
            rows,
            col_widths=[4.5*inch, 1.2*inch, 1.5*inch, 1.0*inch],
        ))
        story.append(PageBreak())

    # ── Features ──────────────────────────────────────────────────────
    if features:
        story.append(Paragraph(f'<a name="features"/>Features ({len(features)})', sH1))
        rows = []
        for f in features:
            rows.append([
                _trunc(f.get("name") or "-", 50),
                f.get("status") or "-",
                f.get("project") or "global",
                (f.get("updated_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Feature", "Status", "Project", "Updated"],
            rows,
            col_widths=[4.5*inch, 1.2*inch, 1.5*inch, 1.0*inch],
        ))
        story.append(PageBreak())

    # ── Components ────────────────────────────────────────────────────
    if components:
        story.append(Paragraph(f'<a name="components"/>Components ({len(components)})', sH1))
        rows = []
        for c in components:
            rows.append([
                _trunc(c.get("name") or "-", 40),
                c.get("component_type") or "-",
                _trunc(c.get("description") or "-", 50),
                c.get("project") or "global",
            ])
        story.append(_make_table(
            ["Component", "Type", "Description", "Project"],
            rows,
            col_widths=[2.2*inch, 1.2*inch, 3.8*inch, 1.2*inch],
        ))
        if len(components) >= 5:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 20))

    # ── People ────────────────────────────────────────────────────────
    if people:
        story.append(Paragraph(f'<a name="people"/>People ({len(people)})', sH1))
        rows = []
        for p in people:
            rows.append([
                _trunc(p.get("name") or "-", 30),
                p.get("role") or "-",
                p.get("email") or "-",
                _trunc(p.get("notes") or "-", 50),
            ])
        story.append(_make_table(
            ["Name", "Role", "Email", "Notes"],
            rows,
            col_widths=[2.0*inch, 2.0*inch, 2.5*inch, 2.7*inch],
        ))
        if len(people) >= 5:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 20))

    # ── Teams ─────────────────────────────────────────────────────────
    if teams_data:
        story.append(Paragraph(f'<a name="teams"/>Teams ({len(teams_data)})', sH1))
        rows = []
        for t in teams_data:
            rows.append([
                _trunc(t.get("name") or "-", 30),
                _trunc(t.get("description") or "-", 200),
                t.get("project") or "global",
            ])
        story.append(_make_table(
            ["Team", "Description", "Project"],
            rows,
            col_widths=[2.0*inch, 5.0*inch, 1.5*inch],
        ))
        if len(teams_data) >= 5:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 20))

    # ── Tickets ───────────────────────────────────────────────────────
    if tickets:
        story.append(Paragraph(f'<a name="tickets"/>Tickets ({len(tickets)})', sH1))
        rows = []
        for t in tickets:
            rows.append([
                _trunc(t.get("title") or "-", 50),
                t.get("status") or "-",
                t.get("priority") or "-",
                t.get("project") or "-",
                (t.get("updated_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Title", "Status", "Priority", "Project", "Updated"],
            rows,
            col_widths=[4.0*inch, 1.0*inch, 1.0*inch, 1.2*inch, 1.0*inch],
        ))
        story.append(PageBreak())

    # ── Diagrams ──────────────────────────────────────────────────────
    if diagrams_data:
        story.append(Paragraph(f'<a name="diagrams"/>Diagrams ({len(diagrams_data)})', sH1))
        story.append(Spacer(1, 12))
        for diag in diagrams_data:
            story.append(Paragraph(_safe(diag.get("title") or "Untitled"), sH2))
            dtype = (diag.get("diagram_type") or "").lower()
            if diag.get("description"):
                story.extend(_md_to_story(diag["description"]))
                story.append(Spacer(1, 8))

            defn = diag.get("definition", "")
            if defn:
                if dtype == "chart":
                    story.extend(_render_chart(defn, diag.get("title", "Chart")))
                elif dtype in ("network", "servicemap"):
                    story.extend(_render_network(defn, diag.get("title", "Network")))
                elif dtype == "mermaid":
                    story.extend(_render_mermaid(defn, diag.get("title", "Diagram")))
                elif dtype == "table":
                    try:
                        tdata = json.loads(defn)
                        cols = tdata.get("columns", [])
                        trows = tdata.get("rows", [])
                        rendered_rows = []
                        for row in trows:
                            if isinstance(row, dict):
                                rendered_rows.append([str(row.get(c, "")) for c in cols])
                            elif isinstance(row, list):
                                rendered_rows.append([str(v) for v in row])
                            else:
                                rendered_rows.append([str(row)])
                        story.append(_make_table(
                            [str(c) for c in cols], rendered_rows))
                    except (ValueError, TypeError):
                        story.append(Paragraph(_safe(defn), sCode))
                else:
                    story.append(Paragraph(_safe(defn), sCode))

            story.append(Spacer(1, 20))
        story.append(PageBreak())

    # ── Instructions ──────────────────────────────────────────────────
    if instructions_data:
        story.append(Paragraph(f'<a name="instructions"/>Instructions ({len(instructions_data)})', sH1))
        rows = []
        for ins in instructions_data:
            active = "Yes" if ins.get("active") else "No"
            rows.append([
                _trunc(ins.get("title") or "-", 200),
                ins.get("section") or "-",
                str(ins.get("priority", "-")),
                ins.get("scope") or "-",
                active,
            ])
        story.append(_make_table(
            ["Title", "Section", "Priority", "Scope", "Active"],
            rows,
            col_widths=[4.0*inch, 1.5*inch, 0.8*inch, 1.0*inch, 0.7*inch],
        ))
        # Detail: full instruction content
        story.append(PageBreak())
        story.append(Paragraph("Instruction Details", sH2))
        for ins in instructions_data:
            story.append(_detail_sep())
            story.append(Paragraph(
                _safe(ins.get("title") or "Untitled Instruction"), sH2))
            if ins.get("content"):
                story.extend(_md_to_story(ins["content"]))
            else:
                story.append(Paragraph("<i>No content body</i>", sBodySmall))
            meta_parts = []
            if ins.get("section"):
                meta_parts.append(f"Section: {_safe(ins['section'])}")
            if ins.get("scope"):
                meta_parts.append(f"Scope: {_safe(ins['scope'])}")
            if ins.get("priority") is not None:
                meta_parts.append(f"Priority: {ins['priority']}")
            active = "Active" if ins.get("active") else "Inactive"
            meta_parts.append(active)
            story.append(Paragraph(" | ".join(meta_parts), sBodySmall))
        story.append(PageBreak())

    # ── Endpoints ─────────────────────────────────────────────────────
    if endpoints:
        story.append(Paragraph(f'<a name="endpoints"/>Endpoints ({len(endpoints)})', sH1))
        rows = []
        for e in endpoints:
            rows.append([
                e.get("method") or "-",
                _trunc(e.get("path") or "-", 50),
                _trunc(e.get("description") or "-", 40),
                e.get("project") or "-",
            ])
        story.append(_make_table(
            ["Method", "Path", "Description", "Project"],
            rows,
            col_widths=[1.0*inch, 3.5*inch, 3.0*inch, 1.2*inch],
        ))
        story.append(PageBreak())

    # ── Decisions ─────────────────────────────────────────────────────
    if decisions:
        story.append(Paragraph(f'<a name="decisions"/>Decisions ({len(decisions)})', sH1))
        rows = []
        for d in decisions:
            rows.append([
                _trunc(d.get("title") or "-", 200),
                d.get("status") or "-",
                d.get("project") or "global",
                (d.get("created_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Decision", "Status", "Project", "Date"],
            rows,
            col_widths=[4.5*inch, 1.2*inch, 1.5*inch, 1.0*inch],
        ))
        # Detail: full decision context
        story.append(PageBreak())
        story.append(Paragraph("Decision Details", sH2))
        for d in decisions:
            story.append(_detail_sep())
            story.append(Paragraph(
                _safe(d.get("title") or "Untitled Decision"), sH3))
            if d.get("context"):
                story.append(Paragraph("<b>Context:</b>", sBody))
                story.extend(_md_to_story(d['context']))
            if d.get("options"):
                opts = _json_list(d["options"])
                if opts:
                    story.append(Paragraph("<b>Options:</b>", sBody))
                    for i, opt in enumerate(opts, 1):
                        story.append(Paragraph(
                            f"  {i}. {_safe(opt)}", sBody))
                else:
                    story.append(Paragraph(
                        f"<b>Options:</b> {_safe(d['options'])}", sBody))
            if d.get("outcome"):
                story.append(Paragraph("<b>Outcome:</b>", sBody))
                story.extend(_md_to_story(d['outcome']))
            if d.get("consequences"):
                story.append(Paragraph("<b>Consequences:</b>", sBody))
                story.extend(_md_to_story(d['consequences']))
            story.append(Paragraph(
                f"Status: {_safe(d.get('status') or '-')} | "
                f"Project: {_safe(d.get('project') or 'global')} | "
                f"Date: {(d.get('created_at') or '')[:10]}",
                sBodySmall))
        story.append(PageBreak())

    # ── Deployments ───────────────────────────────────────────────────
    if deployments:
        story.append(Paragraph(f'<a name="deployments"/>Deployments ({len(deployments)})', sH1))
        rows = []
        for d in deployments:
            rows.append([
                _trunc(d.get("version") or d.get("id", "-"), 30),
                d.get("environment") or "-",
                d.get("status") or "-",
                d.get("project") or "-",
                (d.get("created_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Version", "Environment", "Status", "Project", "Date"],
            rows,
            col_widths=[2.0*inch, 1.8*inch, 1.2*inch, 1.5*inch, 1.0*inch],
        ))
        if len(deployments) >= 5:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 20))

    # ── Builds ────────────────────────────────────────────────────────
    if builds_data:
        story.append(Paragraph(f'<a name="builds"/>Builds ({len(builds_data)})', sH1))
        rows = []
        for b in builds_data:
            rows.append([
                _trunc(b.get("version") or b.get("id", "-"), 30),
                b.get("status") or "-",
                b.get("project") or "-",
                (b.get("created_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Version", "Status", "Project", "Date"],
            rows,
            col_widths=[3.0*inch, 1.5*inch, 2.0*inch, 1.0*inch],
        ))
        if len(builds_data) >= 5:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 20))

    # ── Incidents ─────────────────────────────────────────────────────
    if incidents:
        story.append(Paragraph(f'<a name="incidents"/>Incidents ({len(incidents)})', sH1))
        rows = []
        for inc in incidents:
            rows.append([
                _trunc(inc.get("title") or "-", 50),
                inc.get("severity") or "-",
                inc.get("status") or "-",
                inc.get("project") or "-",
                (inc.get("created_at") or "")[:10],
            ])
        story.append(_make_table(
            ["Incident", "Severity", "Status", "Project", "Date"],
            rows,
            col_widths=[4.0*inch, 1.0*inch, 1.0*inch, 1.2*inch, 1.0*inch],
        ))
        story.append(PageBreak())

    # ── Dependencies ──────────────────────────────────────────────────
    if dependencies:
        story.append(Paragraph(f'<a name="dependencies"/>Dependencies ({len(dependencies)})', sH1))
        rows = []
        for dep in dependencies:
            rows.append([
                _trunc(dep.get("name") or "-", 30),
                dep.get("version") or "-",
                dep.get("dep_type") or "-",
                dep.get("project") or "-",
            ])
        story.append(_make_table(
            ["Dependency", "Version", "Type", "Project"],
            rows,
            col_widths=[3.0*inch, 1.5*inch, 1.5*inch, 1.5*inch],
        ))
        if len(dependencies) >= 5:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 20))

    # ── Runbooks ──────────────────────────────────────────────────────
    if runbooks:
        story.append(Paragraph(f'<a name="runbooks"/>Runbooks ({len(runbooks)})', sH1))
        for rb in runbooks:
            story.append(Paragraph(_safe(rb.get("title") or "Untitled"), sH2))
            if rb.get("description"):
                story.extend(_md_to_story(rb["description"]))
            steps = _json_list(rb.get("steps"))
            if steps:
                for i, step in enumerate(steps, 1):
                    story.append(Paragraph(f"{i}. {_safe(step)}", sBody))
            story.append(Spacer(1, 14))
        story.append(PageBreak())

    # ── Build the PDF ─────────────────────────────────────────────────
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _page_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        # Footer
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(PAGE_W / 2, 20,
                                 f"Memgram Export — Page {doc.page}")
        canvas.restoreState()

    frame = Frame(MARGIN, MARGIN + 10, content_width, PAGE_H - 2 * MARGIN - 10,
                  id="main", showBoundary=0)
    template = PageTemplate(id="main", frames=[frame], onPage=_page_bg,
                            pagesize=PAGE)

    doc = BaseDocTemplate(str(out_path), pagesize=PAGE,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN)
    doc.addPageTemplates([template])
    doc.build(story)

    return out_path


def main_export():
    """CLI entry point for export."""
    import argparse
    from .db.sqlite import DEFAULT_DB_PATH

    default_db = os.environ.get("MEMGRAM_DB_PATH", str(DEFAULT_DB_PATH))
    parser = argparse.ArgumentParser(description="Export memgram database as markdown files")
    parser.add_argument("--db-path", type=str, default=default_db,
                        help=f"Path to SQLite database (default: {default_db})")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output directory or file (default: memgram-export or memgram-jekyll)")
    parser.add_argument("-f", "--format", type=str, default="markdown",
                        choices=["markdown", "jekyll", "html", "pdf"],
                        help="Export format: markdown (plain), jekyll (GitHub Pages site), html (static website), or pdf (report)")
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
    elif args.format == "pdf":
        output_file = args.output or "memgram-export.pdf"
        out_path = export_pdf(db_path=args.db_path, output_file=output_file, project=args.project)
        print(f"Exported PDF report to {out_path.resolve()}")
    else:
        output_dir = args.output or "memgram-export"
        out_path, count = export_markdown(db_path=args.db_path, output_dir=output_dir, project=args.project)
        print(f"Exported {count} files to {out_path.resolve()}")
