"""Tests for memgram database and MCP tools."""

import asyncio
import json
import os
import tempfile

import pytest

from memgram.db import create_db
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


class TestSessionSummary:
    def test_create(self, db):
        s = db.create_session("copilot", "gpt-4")
        ss = db.add_session_summary(
            s["id"], goal="Build auth", outcome="Completed",
            files_modified=["auth.py"], next_session_hints="Add tests",
        )
        assert ss["session_id"] == s["id"]
        assert ss["next_session_hints"] == "Add tests"


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
