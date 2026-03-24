"""Tests for memgram database and MCP tools."""

import asyncio
import json
import os
import tempfile

import pytest

from memgram.db import create_db
from memgram.export import _slugify, export_markdown, rename_existing_exports
from memgram.server import create_server

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    d = create_db("sqlite", db_path=tmp_path / "test.db")
    yield d
    d.close()


@pytest.fixture
def mcp(tmp_path):
    server, d = create_server(db_path=tmp_path / "test_mcp.db")
    from mcp.types import CallToolRequest, CallToolRequestParams

    async def call(name, args=None):
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name=name, arguments=args or {}),
        )
        handler = server.request_handlers.get(CallToolRequest)
        r = await handler(req)
        return json.loads(r.root.content[0].text)

    yield call
    d.close()


# ── DB Tests ────────────────────────────────────────────────────────────────


class TestSessions:
    def test_create_and_get(self, db):
        s = db.create_session("copilot", "claude-sonnet", project="test", goal="test goal")
        assert s["id"]
        assert s["agent_type"] == "copilot"
        assert s["status"] == "active"

        fetched = db.get_session(s["id"])
        assert fetched["id"] == s["id"]

    def test_end_session(self, db):
        s = db.create_session("copilot", "claude-sonnet")
        ended = db.end_session(s["id"], summary="Done")
        assert ended["status"] == "completed"
        assert ended["summary"] == "Done"
        assert ended["ended_at"] is not None

    def test_list_sessions(self, db):
        db.create_session("copilot", "gpt-4", project="a")
        db.create_session("claude", "claude-sonnet", project="b")
        db.create_session("copilot", "gpt-4", project="a")

        all_sessions = db.list_sessions()
        assert len(all_sessions) == 3

        proj_a = db.list_sessions(project="a")
        assert len(proj_a) == 2

        copilot_only = db.list_sessions(agent_type="copilot")
        assert len(copilot_only) == 2


class TestThoughts:
    def test_add_and_get(self, db):
        t = db.add_thought("Test thought", content="Details", type="decision",
                           keywords=["test", "demo"], associated_files=["a.py"])
        assert t["id"]
        assert t["summary"] == "Test thought"
        assert t["type"] == "decision"
        assert json.loads(t["keywords"]) == ["test", "demo"]

        fetched = db.get_thought(t["id"])
        assert fetched["access_count"] == 1  # incremented on get

    def test_update(self, db):
        t = db.add_thought("Original")
        updated = db.update_thought(t["id"], summary="Updated", pinned=1)
        assert updated["summary"] == "Updated"
        assert updated["pinned"] == 1

    def test_pin_and_archive(self, db):
        t = db.add_thought("Pinnable", project="x")
        db.pin_item(t["id"])
        fetched = db.get_thought(t["id"])
        assert fetched["pinned"] == 1

        db.archive_item(t["id"])
        fetched = db.get_thought(t["id"])
        assert fetched["archived"] == 1


class TestRules:
    def test_add_and_get(self, db):
        r = db.add_rule("Use type hints", type="do", severity="critical",
                        keywords=["python", "types"])
        assert r["type"] == "do"
        assert r["severity"] == "critical"
        assert r["reinforcement_count"] == 1

    def test_reinforce(self, db):
        r = db.add_rule("Test rule", type="do", severity="preference")
        reinforced = db.reinforce_rule(r["id"], note="Confirmed again")
        assert reinforced["reinforcement_count"] == 2
        assert "Confirmed again" in reinforced["content"]

    def test_get_rules_filtered(self, db):
        db.add_rule("Global rule", type="do", severity="critical")
        db.add_rule("Project rule", type="dont", severity="preference",
                    project="myapp", keywords=["auth"])
        db.add_rule("Other project", type="do", severity="preference",
                    project="other")

        # Project + global
        rules = db.get_rules(project="myapp")
        assert len(rules) == 2

        # Keyword filter
        rules = db.get_rules(project="myapp", keywords=["auth"])
        assert len(rules) == 1
        assert rules[0]["summary"] == "Project rule"


class TestSnapshots:
    def test_save_and_get(self, db):
        s = db.create_session("copilot", "gpt-4")
        snap = db.save_snapshot(s["id"], current_goal="Build auth",
                                next_steps=["Login", "Logout"])
        assert snap["sequence_num"] == 1
        assert json.loads(snap["next_steps"]) == ["Login", "Logout"]

        snap2 = db.save_snapshot(s["id"], current_goal="Test auth")
        assert snap2["sequence_num"] == 2

        latest = db.get_latest_snapshot(s["id"])
        assert latest["sequence_num"] == 2


class TestSearch:
    def test_fts_search(self, db):
        db.add_thought("JWT authentication design", project="myapp",
                       keywords=["auth", "jwt"])
        db.add_rule("Validate JWT tokens", type="do", severity="critical",
                    project="myapp", keywords=["auth", "jwt"])
        db.add_error_pattern("Token expired silently", cause="No check",
                             project="myapp", keywords=["auth"])

        results = db.search("JWT")
        assert len(results) >= 2  # thought + rule at minimum

        # Type filter
        rules_only = db.search("JWT", type_filter="rule")
        assert all(r["_type"] == "rule" for r in rules_only)

        # Project filter
        results = db.search("JWT", project="myapp")
        assert all(r.get("project") == "myapp" for r in results)

    def test_search_scoring(self, db):
        # Pinned items should score higher
        t1 = db.add_thought("JWT auth", pinned=True)
        t2 = db.add_thought("JWT tokens")
        results = db.search("JWT")
        if len(results) >= 2:
            scores = {r["id"]: r["_score"] for r in results}
            assert scores.get(t1["id"], 0) >= scores.get(t2["id"], 0)


class TestVector:
    def test_store_and_search(self, db):
        t = db.add_thought("Vector test thought")
        embedding = [0.1] * 384
        db.store_embedding(t["id"], "thought", t["summary"], embedding, "test-model")
        assert db.backend.has_embeddings()

        results = db.search_by_embedding(embedding, limit=5)
        assert len(results) == 1
        assert results[0]["id"] == t["id"]
        assert results[0]["_distance"] == 0.0

    def test_delete_embedding(self, db):
        t = db.add_thought("Delete test")
        db.store_embedding(t["id"], "thought", "test", [0.5] * 384, "m")
        db.delete_embedding(t["id"])
        assert not db.backend.has_embeddings()


class TestHealth:
    def test_db_health(self, db):
        diag = db.health()
        assert diag["backend"] == "sqlite"
        assert diag["connected"] is True
        assert "journal_mode" in diag
        assert "vec" in diag
        assert "sessions" in diag["counts"]


class TestGroups:
    def test_create_and_populate(self, db):
        t = db.add_thought("Auth thought")
        r = db.add_rule("Auth rule", type="do", severity="preference")
        g = db.create_group("auth-system", project="myapp")

        db.add_to_group(g["id"], t["id"], "thought")
        db.add_to_group(g["id"], r["id"], "rule")

        group = db.get_group(group_id=g["id"])
        assert group["name"] == "auth-system"
        assert len(group["members"]) == 2

    def test_remove_from_group(self, db):
        t = db.add_thought("Remove test")
        g = db.create_group("test-group")
        db.add_to_group(g["id"], t["id"], "thought")
        assert db.remove_from_group(g["id"], t["id"])
        group = db.get_group(group_id=g["id"])
        assert len(group["members"]) == 0

    def test_lookup_by_name(self, db):
        db.create_group("my-group", project="proj")
        g = db.get_group(name="my-group", project="proj")
        assert g is not None
        assert g["name"] == "my-group"


class TestResumeContext:
    def test_full_resume(self, db):
        s = db.create_session("copilot", "gpt-4", project="myapp")
        db.add_thought("Important", project="myapp", pinned=True)
        db.add_rule("Critical rule", type="do", severity="critical", project="myapp")
        db.save_snapshot(s["id"], current_goal="Build thing")
        db.update_project_summary("myapp", summary="A test project")

        ctx = db.get_resume_context(project="myapp")
        assert "last_session" in ctx
        assert "last_snapshot" in ctx
        assert len(ctx["pinned_thoughts"]) == 1
        assert len(ctx["active_rules"]) == 1
        assert "project_summary" in ctx


class TestProjectSummary:
    def test_create_and_update(self, db):
        ps = db.update_project_summary("myapp", summary="Auth app",
                                       tech_stack=["python", "jwt"])
        assert ps["project"] == "myapp"
        assert ps["summary"] == "Auth app"

        ps = db.update_project_summary("myapp", summary="Updated auth app")
        assert ps["summary"] == "Updated auth app"
        assert json.loads(ps["tech_stack"]) == ["python", "jwt"]  # preserved


class TestProjectMerge:
    def test_merge_projects(self, db):
        # target project with existing summary
        db.update_project_summary("correct", summary="Canonical summary", tech_stack=["rust"])
        db.add_thought("Keep", project="correct")

        # source project (typo) with data
        db.add_thought("Typo thought", project="corret")
        db.add_rule("Typo rule", type="do", severity="critical", project="corret")
        db.update_project_summary("corret", summary="Typo summary", tech_stack=["rust", "os"])

        result = db.merge_projects("corret", "correct")
        assert result["source"] == "corret"
        assert result["target"] == "correct"
        assert db.get_project_summary("corret") is None

        ps = db.get_project_summary("correct")
        assert ps["summary"] == "Canonical summary"
        tech_stack = set(json.loads(ps["tech_stack"]))
        assert {"rust", "os"} <= tech_stack

        thoughts = db.search("Typo", project="correct")
        assert any(t["_type"] == "thought" for t in thoughts)

    def test_rename_project(self, db):
        db.add_thought("Old name thought", project="oldname")
        db.update_project_summary("oldname", summary="Old summary")
        db.rename_project("oldname", "newname")

        assert db.get_project_summary("oldname") is None
        ps = db.get_project_summary("newname")
        assert ps["project"] == "newname"
        assert "Old summary" in ps.get("summary", "")


class TestProjectListing:
    def test_list_projects_includes_data_projects(self, db):
        db.add_thought("No summary thought", project="oxide-os-oxide-")
        projects = db.list_projects()
        names = {p["project"] for p in projects}
        assert "oxide-os-oxide-" in names
        proj_entry = next(p for p in projects if p["project"] == "oxide-os-oxide-")
        assert proj_entry["total_thoughts"] >= 1


class TestSessionSummary:
    def test_create(self, db):
        s = db.create_session("copilot", "gpt-4")
        ss = db.add_session_summary(
            s["id"], goal="Build auth", outcome="Completed",
            files_modified=["auth.py"], next_session_hints="Add tests",
        )
        assert ss["session_id"] == s["id"]
        assert ss["next_session_hints"] == "Add tests"


class TestExport:
    def test_export_uses_slug_filenames(self, tmp_path):
        db_path = tmp_path / "exp.db"
        db = create_db("sqlite", db_path=db_path)
        s = db.create_session("copilot", "gpt-4", project="proj", goal="My Session Goal")
        db.add_thought("My Thought Title", session_id=s["id"], project="proj")
        db.close()

        out_dir = tmp_path / "out"
        export_markdown(db_path=db_path, output_dir=out_dir)

        thought_slug = _slugify("My Thought Title")
        session_slug = _slugify("My Session Goal")
        project_slug = _slugify("proj")
        assert (out_dir / "thoughts" / f"{thought_slug}.md").exists()
        assert (out_dir / "sessions" / f"{session_slug}.md").exists()
        assert (out_dir / "projects" / f"{project_slug}.md").exists()

        proj_text = (out_dir / "projects" / f"{project_slug}.md").read_text()
        assert f"thoughts/{thought_slug}.md" in proj_text
        assert f"sessions/{session_slug}.md" in proj_text


class TestExportMigration:
    def test_rename_existing_exports(self, tmp_path):
        root = tmp_path / "memgram-export"
        (root / "sessions").mkdir(parents=True)
        (root / "thoughts").mkdir(parents=True)
        (root / "rules").mkdir(parents=True)

        session_id = "abcd1234"
        session_md = root / "sessions" / f"{session_id}.md"
        session_md.write_text(
            "# Session: Demo Goal\n\n"
            "| Field | Value |\n"
            "|-------|-------|\n"
            f"| ID | `{session_id}` |\n"
            "| Agent | test |\n"
            "| Model | test |\n",
            encoding="utf-8",
        )

        thought_id = "t1"
        thought_md = root / "thoughts" / f"{thought_id}.md"
        thought_md.write_text(
            "# Thought about Demo\n\n"
            "| Field | Value |\n"
            "|-------|-------|\n"
            f"| ID | `{thought_id}` |\n"
            "| Type | observation |\n"
            f"| Session | [{session_id}](../sessions/{session_id}.md) |\n"
            "\nDetails here\n",
            encoding="utf-8",
        )

        rule_id = "r1"
        rule_md = root / "rules" / f"{rule_id}.md"
        rule_md.write_text(
            "# Rule Title\n\n"
            "| Field | Value |\n"
            "|-------|-------|\n"
            f"| ID | `{rule_id}` |\n"
            f"| Session | [{session_id}](../sessions/{session_id}.md) |\n",
            encoding="utf-8",
        )

        index_md = root / "index.md"
        index_md.write_text(
            "# Index\n\n"
            f"- Session: [link](sessions/{session_id}.md)\n"
            f"- Rule: [link](rules/{rule_id}.md)\n"
            f"- Thought: [link](thoughts/{thought_id}.md)\n",
            encoding="utf-8",
        )

        result = rename_existing_exports(output_dir=root)
        assert result["renamed"] == 3

        session_slug = _slugify("Demo Goal")
        thought_slug = _slugify("Thought about Demo")
        rule_slug = _slugify("Rule Title")

        assert (root / "sessions" / f"{session_slug}.md").exists()
        assert not session_md.exists()

        updated_thought = (root / "thoughts" / f"{thought_slug}.md").read_text()
        assert f"../sessions/{session_slug}.md" in updated_thought
        assert "[Demo Goal]" in updated_thought

        updated_index = index_md.read_text()
        assert f"sessions/{session_slug}.md" in updated_index
        assert f"rules/{rule_slug}.md" in updated_index
        assert f"thoughts/{thought_slug}.md" in updated_index


# ── MCP Tool Tests ──────────────────────────────────────────────────────────


class TestMCPTools:
    def test_full_workflow(self, mcp):
        async def run():
            # Start session
            d = await mcp("start_session", {"agent_type": "test", "model": "test-model",
                                            "project": "proj", "goal": "test"})
            assert "session" in d
            sid = d["session"]["id"]

            # Add thought
            d = await mcp("add_thought", {"summary": "Test thought", "session_id": sid,
                                          "project": "proj", "keywords": ["test"]})
            assert d["id"]
            tid = d["id"]

            # Add rule
            d = await mcp("add_rule", {"summary": "Test rule", "type": "do",
                                       "severity": "critical", "session_id": sid, "project": "proj"})
            assert d["id"]
            rid = d["id"]

            # Search
            d = await mcp("search", {"query": "test"})
            assert d["count"] >= 2

            # Get rules
            d = await mcp("get_rules", {"project": "proj"})
            assert d["count"] >= 1

            # Pin
            d = await mcp("pin_item", {"item_id": tid})
            assert d["pinned"] == 1

            # End session
            d = await mcp("end_session", {"session_id": sid, "summary": "Done"})
            assert d["session"]["status"] == "completed"

            # Resume context
            d = await mcp("get_resume_context", {"project": "proj"})
            assert "last_session" in d
            assert len(d["active_rules"]) >= 1

        asyncio.get_event_loop().run_until_complete(run())

    def test_health_tool(self, mcp):
        async def run():
            d = await mcp("get_health", {})
            assert d.get("backend") == "sqlite"
            assert d.get("connected") is True
            assert "vec" in d
            assert "journal_mode" in d
        asyncio.get_event_loop().run_until_complete(run())

    def test_merge_projects_tool(self, mcp):
        async def run():
            s = await mcp("start_session", {"agent_type": "test", "model": "test-model",
                                            "project": "typo", "goal": "merge test"})
            sid = s["session"]["id"]
            await mcp("add_thought", {"summary": "Typo thought", "project": "typo", "session_id": sid})
            await mcp("add_rule", {"summary": "Typo rule", "type": "do", "severity": "critical",
                                   "project": "typo", "session_id": sid})
            await mcp("merge_projects", {"from_project": "typo", "to_project": "correct"})
            ps = await mcp("get_project_summary", {"project": "correct"})
            assert ps["project"] == "correct"
            # counts should reflect merged data
            assert ps["total_thoughts"] >= 1
            assert ps["total_rules"] >= 1
        asyncio.get_event_loop().run_until_complete(run())

    def test_list_projects_cli(self, tmp_path):
        # exercise CLI list-projects path
        db_path = tmp_path / "cli.db"
        db = create_db("sqlite", db_path=db_path)
        db.add_thought("CLI proj", project="cliproj")
        db.add_thought("Data-only proj", project="oxide-os-oxide-")
        db.update_project_summary("cliproj", summary="CLI summary")
        db.close()

        import subprocess, sys, json, os
        proc = subprocess.run(
            [sys.executable, "-m", "memgram.server", "list-projects", "--db-path", str(db_path)],
            capture_output=True, text=True, env=os.environ.copy(),
        )
        assert proc.returncode == 0
        assert "cliproj" in proc.stdout
        assert "oxide-os-oxide-" in proc.stdout


# ── Branch Scoping Tests ─────────────────────────────────────────────────────


class TestBranchScoping:
    def test_create_session_with_branch(self, db):
        s = db.create_session("copilot", "gpt-4", project="myapp", branch="featureauth")
        assert s["branch"] == "featureauth"
        assert s["project"] == "myapp"

    def test_list_sessions_by_branch(self, db):
        db.create_session("copilot", "gpt-4", project="myapp", branch="featureauth")
        db.create_session("copilot", "gpt-4", project="myapp", branch="fixbug")
        db.create_session("copilot", "gpt-4", project="myapp")

        all_sessions = db.list_sessions(project="myapp")
        assert len(all_sessions) == 3

        branch_sessions = db.list_sessions(project="myapp", branch="featureauth")
        assert len(branch_sessions) == 1
        assert branch_sessions[0]["branch"] == "featureauth"

    def test_add_thought_with_branch(self, db):
        t = db.add_thought("Branch thought", project="myapp", branch="featureauth")
        assert t["branch"] == "featureauth"

    def test_get_rules_branch_scoped(self, db):
        """Branch-specific + branch-global (NULL) rules should be returned."""
        db.add_rule("Global rule", type="do", severity="critical", project="myapp")
        db.add_rule("Branch rule", type="do", severity="preference",
                    project="myapp", branch="featureauth")
        db.add_rule("Other branch rule", type="do", severity="preference",
                    project="myapp", branch="fixbug")

        rules = db.get_rules(project="myapp", branch="featureauth")
        summaries = {r["summary"] for r in rules}
        assert "Global rule" in summaries
        assert "Branch rule" in summaries
        assert "Other branch rule" not in summaries

    def test_fts_search_branch_filter(self, db):
        db.add_thought("JWT auth design", project="myapp", branch="featureauth",
                       keywords=["auth"])
        db.add_thought("JWT token rotation", project="myapp", branch="fixbug",
                       keywords=["auth"])

        results = db.search("JWT", project="myapp", branch="featureauth")
        assert len(results) == 1
        assert results[0]["branch"] == "featureauth"

    def test_resume_context_with_branch(self, db):
        """Resume context should return branch-scoped + global (NULL branch) items."""
        db.create_session("copilot", "gpt-4", project="myapp", branch="featureauth")
        db.add_thought("Branch pinned", project="myapp", branch="featureauth", pinned=True)
        db.add_thought("Global pinned", project="myapp", pinned=True)
        db.add_thought("Other branch pinned", project="myapp", branch="fixbug", pinned=True)
        db.add_rule("Branch critical", type="do", severity="critical",
                    project="myapp", branch="featureauth")
        db.add_rule("Global critical", type="do", severity="critical", project="myapp")

        ctx = db.get_resume_context(project="myapp", branch="featureauth")
        assert "last_session" in ctx
        pinned_summaries = {t["summary"] for t in ctx["pinned_thoughts"]}
        assert "Branch pinned" in pinned_summaries
        assert "Global pinned" in pinned_summaries
        assert "Other branch pinned" not in pinned_summaries

        rule_summaries = {r["summary"] for r in ctx["active_rules"]}
        assert "Branch critical" in rule_summaries
        assert "Global critical" in rule_summaries

    def test_branch_normalization(self, db):
        """Branch names like 'feature/auth-flow' should normalize to 'featureauthflow'."""
        from memgram.utils import normalize_name
        assert normalize_name("feature/auth-flow") == "featureauthflow"
        assert normalize_name("Feature_Auth") == "featureauth"

        s = db.create_session("copilot", "gpt-4", branch="featureauthflow")
        assert s["branch"] == "featureauthflow"


# ── Agent Attribution Tests ─────────────────────────────────────────────────


class TestAgentAttribution:
    def test_thought_explicit_agent(self, db):
        """Explicit agent_type/agent_model on a thought."""
        t = db.add_thought("Test thought", agent_type="claude", agent_model="claude-sonnet-4")
        assert t["agent_type"] == "claude"
        assert t["agent_model"] == "claude-sonnet-4"

    def test_thought_agent_from_session(self, db):
        """Agent info auto-resolved from session when not explicitly provided."""
        s = db.create_session("copilot", "gpt-4", project="myapp")
        t = db.add_thought("Session thought", session_id=s["id"], project="myapp")
        assert t["agent_type"] == "copilot"
        assert t["agent_model"] == "gpt-4"

    def test_rule_agent_from_session(self, db):
        s = db.create_session("claude", "claude-opus-4", project="myapp")
        r = db.add_rule("Always test", type="do", severity="critical",
                        session_id=s["id"], project="myapp")
        assert r["agent_type"] == "claude"
        assert r["agent_model"] == "claude-opus-4"

    def test_error_pattern_agent(self, db):
        s = db.create_session("codex", "codex-mini", project="myapp")
        e = db.add_error_pattern("Something broke", session_id=s["id"], project="myapp")
        assert e["agent_type"] == "codex"
        assert e["agent_model"] == "codex-mini"

    def test_explicit_overrides_session(self, db):
        """Explicit agent_type should take precedence over session lookup."""
        s = db.create_session("copilot", "gpt-4", project="myapp")
        t = db.add_thought("Override thought", session_id=s["id"],
                           agent_type="claude", agent_model="claude-sonnet-4")
        assert t["agent_type"] == "claude"
        assert t["agent_model"] == "claude-sonnet-4"

    def test_no_session_no_agent(self, db):
        """Items created without session or explicit agent have NULL agent fields."""
        t = db.add_thought("Orphan thought")
        assert t["agent_type"] is None
        assert t["agent_model"] is None

    def test_get_agent_stats(self, db):
        """Agent stats should aggregate across sessions, thoughts, rules, errors."""
        s1 = db.create_session("claude", "claude-sonnet-4", project="myapp")
        s2 = db.create_session("copilot", "gpt-4", project="myapp")
        db.add_thought("Claude thought", session_id=s1["id"], project="myapp")
        db.add_thought("Another claude thought", session_id=s1["id"], project="myapp")
        db.add_thought("Copilot thought", session_id=s2["id"], project="myapp")
        db.add_rule("Claude rule", type="do", severity="preference",
                    session_id=s1["id"], project="myapp")
        db.add_error_pattern("Copilot error", session_id=s2["id"], project="myapp")

        stats = db.get_agent_stats()
        assert stats["totals"]["total_agents"] == 2
        assert stats["totals"]["total_sessions"] == 2
        assert stats["totals"]["total_thoughts"] == 3
        assert stats["totals"]["total_rules"] == 1
        assert stats["totals"]["total_errors"] == 1

        # Check per-agent breakdown
        by_agent = {(a["agent_type"], a["agent_model"]): a for a in stats["agents"]}
        claude = by_agent[("claude", "claude-sonnet-4")]
        assert claude["sessions"] == 1
        assert claude["thoughts"] == 2
        assert claude["rules"] == 1

        copilot = by_agent[("copilot", "gpt-4")]
        assert copilot["sessions"] == 1
        assert copilot["thoughts"] == 1
        assert copilot["errors"] == 1

    def test_get_agent_stats_project_filter(self, db):
        """Agent stats should filter by project when provided."""
        db.create_session("claude", "claude-sonnet-4", project="myapp")
        db.create_session("claude", "claude-sonnet-4", project="other")

        stats_all = db.get_agent_stats()
        assert stats_all["totals"]["total_sessions"] == 2

        stats_myapp = db.get_agent_stats(project="myapp")
        assert stats_myapp["totals"]["total_sessions"] == 1


# ── Plan Tests ──────────────────────────────────────────────────────────────


class TestPlans:
    def test_create_plan(self, db):
        plan = db.create_plan("Migration plan", description="Migrate to v2",
                              scope="project", priority="high", project="myapp",
                              tags=["migration", "v2"])
        assert plan["id"]
        assert plan["title"] == "Migration plan"
        assert plan["scope"] == "project"
        assert plan["priority"] == "high"
        assert plan["status"] == "draft"
        assert plan["total_tasks"] == 0
        assert plan["completed_tasks"] == 0
        assert json.loads(plan["tags"]) == ["migration", "v2"]

    def test_update_plan(self, db):
        plan = db.create_plan("Draft plan")
        updated = db.update_plan(plan["id"], status="active", priority="critical",
                                 due_date="2026-04-01T00:00:00Z")
        assert updated["status"] == "active"
        assert updated["priority"] == "critical"
        assert updated["due_date"] == "2026-04-01T00:00:00Z"

    def test_get_plan_with_tasks(self, db):
        plan = db.create_plan("Test plan", project="myapp")
        db.add_plan_task(plan["id"], "Task 1", description="First task")
        db.add_plan_task(plan["id"], "Task 2", description="Second task")

        fetched = db.get_plan(plan["id"])
        assert fetched is not None
        assert len(fetched["tasks"]) == 2
        assert fetched["total_tasks"] == 2
        assert fetched["completed_tasks"] == 0

    def test_list_plans_filtered(self, db):
        db.create_plan("Plan A", project="myapp", priority="high")
        db.create_plan("Plan B", project="other", priority="low")
        db.create_plan("Plan C", project="myapp", priority="medium")

        all_plans = db.list_plans()
        assert len(all_plans) == 3

        myapp_plans = db.list_plans(project="myapp")
        assert len(myapp_plans) == 2

    def test_list_plans_by_status(self, db):
        p1 = db.create_plan("Active plan")
        db.update_plan(p1["id"], status="active")
        db.create_plan("Draft plan")

        active = db.list_plans(status="active")
        assert len(active) == 1
        assert active[0]["title"] == "Active plan"

    def test_plan_pinned_to_session(self, db):
        session = db.create_session("claude", "claude-sonnet", project="myapp")
        plan = db.create_plan("Session plan", session_id=session["id"], project="myapp")
        assert plan["session_id"] == session["id"]

        plans = db.list_plans(session_id=session["id"])
        assert len(plans) == 1

    def test_add_task_auto_position(self, db):
        plan = db.create_plan("Ordered plan")
        t1 = db.add_plan_task(plan["id"], "First")
        t2 = db.add_plan_task(plan["id"], "Second")
        t3 = db.add_plan_task(plan["id"], "Third")
        assert t1["position"] == 0
        assert t2["position"] == 1
        assert t3["position"] == 2

    def test_update_task_status(self, db):
        plan = db.create_plan("Status plan")
        task = db.add_plan_task(plan["id"], "Do something")
        assert task["status"] == "pending"

        updated = db.update_plan_task(task["id"], status="in_progress")
        assert updated["status"] == "in_progress"
        assert updated["completed_at"] is None

        completed = db.update_plan_task(task["id"], status="completed")
        assert completed["status"] == "completed"
        assert completed["completed_at"] is not None

        # Plan counts should reflect completion
        plan = db.get_plan(plan["id"])
        assert plan["total_tasks"] == 1
        assert plan["completed_tasks"] == 1

    def test_task_dependencies(self, db):
        plan = db.create_plan("Dep plan")
        t1 = db.add_plan_task(plan["id"], "Setup DB")
        t2 = db.add_plan_task(plan["id"], "Run migrations", depends_on=t1["id"])
        assert t2["depends_on"] == t1["id"]

    def test_task_assignee(self, db):
        plan = db.create_plan("Team plan")
        task = db.add_plan_task(plan["id"], "Review code", assignee="claude")
        assert task["assignee"] == "claude"

    def test_delete_task(self, db):
        plan = db.create_plan("Delete test")
        t1 = db.add_plan_task(plan["id"], "Keep this")
        t2 = db.add_plan_task(plan["id"], "Remove this")

        deleted = db.delete_plan_task(t2["id"])
        assert deleted is True

        plan = db.get_plan(plan["id"])
        assert plan["total_tasks"] == 1
        assert len(plan["tasks"]) == 1

    def test_plan_progress_tracking(self, db):
        plan = db.create_plan("Progress plan")
        t1 = db.add_plan_task(plan["id"], "Step 1")
        t2 = db.add_plan_task(plan["id"], "Step 2")
        t3 = db.add_plan_task(plan["id"], "Step 3")

        db.update_plan_task(t1["id"], status="completed")
        db.update_plan_task(t2["id"], status="completed")

        plan = db.get_plan(plan["id"])
        assert plan["total_tasks"] == 3
        assert plan["completed_tasks"] == 2


class TestPlansMCP:
    def test_create_plan_mcp(self, mcp):
        result = asyncio.get_event_loop().run_until_complete(
            mcp("create_plan", {"title": "MCP Plan", "project": "test", "priority": "high"})
        )
        assert result["id"]
        assert result["title"] == "MCP Plan"
        assert result["priority"] == "high"

    def test_plan_task_lifecycle_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        # Create plan
        plan = loop.run_until_complete(
            mcp("create_plan", {"title": "Task lifecycle", "project": "test"})
        )

        # Add tasks
        t1 = loop.run_until_complete(
            mcp("add_plan_task", {"plan_id": plan["id"], "title": "Task 1"})
        )
        t2 = loop.run_until_complete(
            mcp("add_plan_task", {"plan_id": plan["id"], "title": "Task 2"})
        )

        # Get plan with tasks
        full = loop.run_until_complete(
            mcp("get_plan", {"plan_id": plan["id"]})
        )
        assert len(full["tasks"]) == 2
        assert full["total_tasks"] == 2

        # Update task status
        loop.run_until_complete(
            mcp("update_plan_task", {"task_id": t1["id"], "status": "completed"})
        )

        # Check progress
        full = loop.run_until_complete(
            mcp("get_plan", {"plan_id": plan["id"]})
        )
        assert full["completed_tasks"] == 1

        # Delete a task
        result = loop.run_until_complete(
            mcp("delete_plan_task", {"task_id": t2["id"]})
        )
        assert result["deleted"] is True

    def test_list_plans_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        loop.run_until_complete(
            mcp("create_plan", {"title": "Plan 1", "project": "test"})
        )
        loop.run_until_complete(
            mcp("create_plan", {"title": "Plan 2", "project": "test"})
        )

        result = loop.run_until_complete(
            mcp("list_plans", {"project": "test"})
        )
        assert result["count"] == 2


# ── Spec Tests ──────────────────────────────────────────────────────────────


class TestSpecs:
    def test_create_spec(self, db):
        spec = db.create_spec(
            "Auth API Spec", description="Define auth endpoints",
            priority="high", project="myapp",
            acceptance_criteria=["JWT tokens", "OAuth2 support", "Rate limiting"],
            tags=["auth", "api"],
        )
        assert spec["id"]
        assert spec["title"] == "Auth API Spec"
        assert spec["status"] == "draft"
        assert json.loads(spec["acceptance_criteria"]) == ["JWT tokens", "OAuth2 support", "Rate limiting"]

    def test_update_spec(self, db):
        spec = db.create_spec("Draft spec")
        updated = db.update_spec(spec["id"], status="approved", priority="critical")
        assert updated["status"] == "approved"
        assert updated["priority"] == "critical"

    def test_get_spec_with_features(self, db):
        spec = db.create_spec("Parent spec", project="myapp")
        db.create_feature("Feature A", spec_id=spec["id"], project="myapp")
        db.create_feature("Feature B", spec_id=spec["id"], project="myapp")

        fetched = db.get_spec(spec["id"])
        assert len(fetched["features"]) == 2

    def test_list_specs_filtered(self, db):
        db.create_spec("Spec 1", project="myapp", priority="high")
        db.create_spec("Spec 2", project="other")
        db.create_spec("Spec 3", project="myapp", status="approved")

        myapp = db.list_specs(project="myapp")
        assert len(myapp) == 2

        approved = db.list_specs(status="approved")
        assert len(approved) == 1

    def test_spec_with_author(self, db):
        person = db.add_person("Alice", role="pm")
        spec = db.create_spec("Authored spec", author_id=person["id"])
        assert spec["author_id"] == person["id"]

        # Person should show authored specs
        fetched_person = db.get_person(person["id"])
        assert len(fetched_person["authored_specs"]) == 1


# ── Feature Tests ───────────────────────────────────────────────────────────


class TestFeatures:
    def test_create_feature(self, db):
        feat = db.create_feature(
            "User Login", description="Email/password login flow",
            priority="high", project="myapp", tags=["auth", "frontend"],
        )
        assert feat["id"]
        assert feat["name"] == "User Login"
        assert feat["status"] == "proposed"

    def test_update_feature(self, db):
        feat = db.create_feature("Draft feature")
        updated = db.update_feature(feat["id"], status="in_progress", priority="critical")
        assert updated["status"] == "in_progress"

    def test_feature_linked_to_spec(self, db):
        spec = db.create_spec("Auth spec")
        feat = db.create_feature("Login", spec_id=spec["id"])
        assert feat["spec_id"] == spec["id"]

        features = db.list_features(spec_id=spec["id"])
        assert len(features) == 1

    def test_feature_with_lead(self, db):
        person = db.add_person("Bob", role="engineer")
        feat = db.create_feature("Feature X", lead_id=person["id"])

        fetched_person = db.get_person(person["id"])
        assert len(fetched_person["led_features"]) == 1

    def test_feature_linked_to_component(self, db):
        feat = db.create_feature("Search", project="myapp")
        comp = db.create_component("Search Engine", project="myapp")

        link = db.link_items(
            from_id=feat["id"], from_type="feature",
            to_id=comp["id"], to_type="component",
            link_type="implements",
        )
        assert link["link_type"] == "implements"

        fetched = db.get_feature(feat["id"])
        assert len(fetched["links"]) == 1


# ── Component Tests ─────────────────────────────────────────────────────────


class TestComponents:
    def test_create_component(self, db):
        comp = db.create_component(
            "Auth Service", description="Handles authentication",
            type="service", project="myapp",
            tech_stack=["python", "fastapi", "postgres"],
            tags=["backend", "auth"],
        )
        assert comp["id"]
        assert comp["name"] == "Auth Service"
        assert comp["type"] == "service"
        assert json.loads(comp["tech_stack"]) == ["python", "fastapi", "postgres"]

    def test_update_component(self, db):
        comp = db.create_component("Old name")
        updated = db.update_component(comp["id"], name="New name", type="api")
        assert updated["name"] == "New name"
        assert updated["type"] == "api"

    def test_component_with_owner(self, db):
        person = db.add_person("Charlie", role="engineer")
        comp = db.create_component("Backend", owner_id=person["id"])

        fetched_person = db.get_person(person["id"])
        assert len(fetched_person["owned_components"]) == 1

    def test_list_components_filtered(self, db):
        db.create_component("Service A", type="service", project="myapp")
        db.create_component("Module B", type="module", project="myapp")
        db.create_component("Service C", type="service", project="other")

        services = db.list_components(type="service")
        assert len(services) == 2

        myapp = db.list_components(project="myapp")
        assert len(myapp) == 2


# ── People Tests ────────────────────────────────────────────────────────────


class TestPeople:
    def test_add_person(self, db):
        person = db.add_person(
            "Alice Smith", role="engineer",
            email="alice@example.com", github="alicesmith",
            skills=["python", "react", "postgres"],
            notes="Senior backend engineer",
        )
        assert person["id"]
        assert person["name"] == "Alice Smith"
        assert person["role"] == "engineer"
        assert person["github"] == "alicesmith"
        assert json.loads(person["skills"]) == ["python", "react", "postgres"]

    def test_update_person(self, db):
        person = db.add_person("Bob")
        updated = db.update_person(person["id"], role="lead", skills=["go", "kubernetes"])
        assert updated["role"] == "lead"
        assert json.loads(updated["skills"]) == ["go", "kubernetes"]

    def test_get_person_with_relationships(self, db):
        person = db.add_person("Alice", role="engineer")
        db.create_component("Auth", owner_id=person["id"], project="myapp")
        db.create_feature("Login", lead_id=person["id"], project="myapp")
        db.create_spec("Auth Spec", author_id=person["id"], project="myapp")

        fetched = db.get_person(person["id"])
        assert len(fetched["owned_components"]) == 1
        assert len(fetched["led_features"]) == 1
        assert len(fetched["authored_specs"]) == 1

    def test_list_people_by_role(self, db):
        db.add_person("Alice", role="engineer")
        db.add_person("Bob", role="designer")
        db.add_person("Charlie", role="engineer")

        engineers = db.list_people(role="engineer")
        assert len(engineers) == 2

        all_people = db.list_people()
        assert len(all_people) == 3


# ── Cross-Entity Linking Tests ──────────────────────────────────────────────


class TestCrossEntityLinks:
    def test_spec_to_feature_to_component_chain(self, db):
        """Full chain: spec -> feature -> component with people."""
        person = db.add_person("Alice", role="engineer")
        spec = db.create_spec("Auth Spec", author_id=person["id"], project="myapp")
        feat = db.create_feature("Login Flow", spec_id=spec["id"], lead_id=person["id"], project="myapp")
        comp = db.create_component("Auth Module", owner_id=person["id"], project="myapp")

        # Link feature to component
        db.link_items(feat["id"], "feature", comp["id"], "component", "implements")

        # Link plan to feature
        plan = db.create_plan("Build login", project="myapp")
        db.link_items(plan["id"], "plan", feat["id"], "feature", "implements")

        # Verify the graph
        feat_links = db.get_related(feat["id"])
        assert len(feat_links) == 2  # component + plan

        person_detail = db.get_person(person["id"])
        assert len(person_detail["owned_components"]) == 1
        assert len(person_detail["led_features"]) == 1
        assert len(person_detail["authored_specs"]) == 1

    def test_thought_linked_to_feature(self, db):
        """Knowledge items can link to project entities."""
        feat = db.create_feature("Search", project="myapp")
        thought = db.add_thought("Search needs caching", project="myapp")
        db.link_items(thought["id"], "thought", feat["id"], "feature", "informs")

        links = db.get_related(thought["id"])
        assert len(links) == 1
        assert links[0]["to_type"] == "feature"

    def test_error_linked_to_component(self, db):
        comp = db.create_component("DB Layer", project="myapp")
        error = db.add_error_pattern("Connection timeout", cause="Pool exhaustion", project="myapp")
        db.link_items(error["id"], "error_pattern", comp["id"], "component", "caused_by")

        links = db.get_related(error["id"])
        assert len(links) == 1


# ── MCP Tests for New Entities ──────────────────────────────────────────────


class TestNewEntitiesMCP:
    def test_spec_lifecycle_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        spec = loop.run_until_complete(
            mcp("create_spec", {"title": "API Spec", "project": "test", "priority": "high"})
        )
        assert spec["title"] == "API Spec"

        updated = loop.run_until_complete(
            mcp("update_spec", {"spec_id": spec["id"], "status": "approved"})
        )
        assert updated["status"] == "approved"

        fetched = loop.run_until_complete(
            mcp("get_spec", {"spec_id": spec["id"]})
        )
        assert fetched["title"] == "API Spec"

        listed = loop.run_until_complete(
            mcp("list_specs", {"project": "test"})
        )
        assert listed["count"] == 1

    def test_feature_lifecycle_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        feat = loop.run_until_complete(
            mcp("create_feature", {"name": "Login", "project": "test"})
        )
        assert feat["name"] == "Login"

        listed = loop.run_until_complete(
            mcp("list_features", {"project": "test"})
        )
        assert listed["count"] == 1

    def test_component_lifecycle_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        comp = loop.run_until_complete(
            mcp("create_component", {"name": "Auth Service", "type": "service", "project": "test"})
        )
        assert comp["type"] == "service"

        listed = loop.run_until_complete(
            mcp("list_components", {"project": "test"})
        )
        assert listed["count"] == 1

    def test_person_lifecycle_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        person = loop.run_until_complete(
            mcp("add_person", {"name": "Alice", "role": "engineer", "skills": ["python"]})
        )
        assert person["name"] == "Alice"

        fetched = loop.run_until_complete(
            mcp("get_person", {"person_id": person["id"]})
        )
        assert fetched["name"] == "Alice"

        listed = loop.run_until_complete(
            mcp("list_people", {})
        )
        assert listed["count"] == 1

    def test_cross_entity_linking_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        person = loop.run_until_complete(
            mcp("add_person", {"name": "Bob", "role": "lead"})
        )
        spec = loop.run_until_complete(
            mcp("create_spec", {"title": "Spec", "project": "test"})
        )
        feat = loop.run_until_complete(
            mcp("create_feature", {"name": "Feature", "spec_id": spec["id"], "project": "test"})
        )
        comp = loop.run_until_complete(
            mcp("create_component", {"name": "Component", "project": "test"})
        )

        # Link feature to component
        loop.run_until_complete(
            mcp("link_items", {
                "from_id": feat["id"], "from_type": "feature",
                "to_id": comp["id"], "to_type": "component",
                "link_type": "implements",
            })
        )

        # Link person to component
        loop.run_until_complete(
            mcp("link_items", {
                "from_id": person["id"], "from_type": "person",
                "to_id": comp["id"], "to_type": "component",
                "link_type": "owns",
            })
        )

        related = loop.run_until_complete(
            mcp("get_related", {"item_id": comp["id"]})
        )
        assert related["count"] == 2


# ── Team Tests ──────────────────────────────────────────────────────────────


class TestTeams:
    def test_create_team(self, db):
        team = db.create_team("Backend Team", description="Backend engineers",
                              project="myapp", tags=["backend"])
        assert team["id"]
        assert team["name"] == "Backend Team"

    def test_team_with_members(self, db):
        lead = db.add_person("Alice", type="individual", role="lead")
        dev = db.add_person("Bob", type="team_member", role="engineer")
        contractor = db.add_person("Charlie", type="contractor", role="engineer")

        team = db.create_team("Platform", lead_id=lead["id"], project="myapp")
        db.add_team_member(team["id"], lead["id"], role="lead")
        db.add_team_member(team["id"], dev["id"], role="member")
        db.add_team_member(team["id"], contractor["id"], role="contributor")

        fetched = db.get_team(team["id"])
        assert len(fetched["members"]) == 3

        # Person should see their teams
        alice = db.get_person(lead["id"])
        assert len(alice["teams"]) == 1
        assert alice["teams"][0]["member_role"] == "lead"

    def test_remove_team_member(self, db):
        person = db.add_person("Alice")
        team = db.create_team("Team X")
        db.add_team_member(team["id"], person["id"])

        removed = db.remove_team_member(team["id"], person["id"])
        assert removed is True

        fetched = db.get_team(team["id"])
        assert len(fetched["members"]) == 0

    def test_list_teams(self, db):
        db.create_team("Team A", project="myapp")
        db.create_team("Team B", project="other")
        db.create_team("Team C", project="myapp")

        all_teams = db.list_teams()
        assert len(all_teams) == 3

        myapp = db.list_teams(project="myapp")
        assert len(myapp) == 2

    def test_person_types(self, db):
        ind = db.add_person("Alice", type="individual")
        con = db.add_person("Bob", type="contractor")
        tm = db.add_person("Charlie", type="team_member")

        assert ind["type"] == "individual"
        assert con["type"] == "contractor"
        assert tm["type"] == "team_member"


class TestTeamsMCP:
    def test_team_lifecycle_mcp(self, mcp):
        loop = asyncio.get_event_loop()

        person = loop.run_until_complete(
            mcp("add_person", {"name": "Alice", "role": "lead"})
        )
        team = loop.run_until_complete(
            mcp("create_team", {"name": "Backend", "project": "test", "lead_id": person["id"]})
        )
        assert team["name"] == "Backend"

        loop.run_until_complete(
            mcp("add_team_member", {"team_id": team["id"], "person_id": person["id"], "role": "lead"})
        )

        fetched = loop.run_until_complete(
            mcp("get_team", {"team_id": team["id"]})
        )
        assert len(fetched["members"]) == 1

        listed = loop.run_until_complete(
            mcp("list_teams", {"project": "test"})
        )
        assert listed["count"] == 1

        loop.run_until_complete(
            mcp("remove_team_member", {"team_id": team["id"], "person_id": person["id"]})
        )
        fetched = loop.run_until_complete(
            mcp("get_team", {"team_id": team["id"]})
        )
        assert len(fetched["members"]) == 0
