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
            await mcp("add_thought", {"summary": "Typo thought", "project": "typo"})
            await mcp("add_rule", {"summary": "Typo rule", "type": "do", "severity": "critical", "project": "typo"})
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
