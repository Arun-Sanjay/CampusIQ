"""Tests for the live voice interview — ElevenLabs agent + transcript grading.

The live conversation itself is handled by ElevenLabs in the browser, so here we
mock the agent boundary (signed-URL mint + finished-transcript fetch) and the
Claude grader, then exercise the server-side flow: start a round → finalize it →
background grade the transcript → roll up to round/overall scores + debrief.
"""
from __future__ import annotations


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _signup(client, signup_payload, role):
    r = client.post("/api/v1/auth/signup", json=signup_payload(role))
    assert r.status_code in (200, 201), r.text
    return r.json()


def _start_voice_session(client, stok):
    r = client.post(
        "/api/v1/interviews/",
        headers=_auth(stok),
        json={
            "company_target": "Google",
            "role_target": "SWE",
            "interviewer_persona": "tough",
            "mode": "voice",
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _fake_convo():
    """A finished ElevenLabs conversation with 2 graded candidate answers."""
    return {
        "status": "done",
        "transcript": [
            {"role": "agent", "message": "Walk me through reversing a linked list."},
            {"role": "user", "message": "Iterate flipping next pointers; O(n) time, O(1) space."},
            {"role": "agent", "message": "Good. What about detecting a cycle?"},
            {"role": "user", "message": "Um, I'm not totally sure."},
        ],
    }


def _fake_generate_completion(*args, **kwargs):
    system = kwargs.get("system", "") or (args[0] if args else "")
    if "hire_verdict" in system:  # the debrief generator
        return (
            '{"hire_verdict": "hire", "headline": "Solid candidate.",'
            ' "strengths": ["Clear complexity analysis"],'
            ' "improvements": ["Tighten graph fundamentals"],'
            ' "standout_answer": "Linked-list reversal", "biggest_gap": "Cycles"}'
        )
    # the per-round transcript grader
    return (
        '{"answers": [{"index": 0, "score": 8.0, "reason": "Correct with complexity."},'
        ' {"index": 1, "score": 4.0, "reason": "Unsure."}]}'
    )


def _patch_agent(monkeypatch):
    from app.services import claude_client, elevenlabs_agent

    monkeypatch.setattr(elevenlabs_agent, "is_configured", lambda: True)
    monkeypatch.setattr(
        elevenlabs_agent,
        "get_signed_url",
        lambda *a, **k: "wss://api.elevenlabs.io/v1/convai/conversation?token=test",
    )
    monkeypatch.setattr(
        elevenlabs_agent, "poll_conversation_until_done", lambda *a, **k: _fake_convo()
    )
    monkeypatch.setattr(claude_client, "is_available", lambda: True)
    monkeypatch.setattr(claude_client, "generate_completion", _fake_generate_completion)


def test_voice_session_skips_text_opening(client, signup_payload):
    student = _signup(client, signup_payload, "student")
    s = _start_voice_session(client, student["access_token"])
    assert s["mode"] == "voice"
    # The live agent speaks the opener; the transcript fills in only on grading.
    assert s["transcript"] == []


def test_start_requires_configured_agent(client, signup_payload):
    # No agent configured by default in tests → 503 (graceful degradation).
    student = _signup(client, signup_payload, "student")
    s = _start_voice_session(client, student["access_token"])
    r = client.post(
        f"/api/v1/interviews/{s['id']}/live/rounds/1/start",
        headers=_auth(student["access_token"]),
    )
    assert r.status_code == 503


def test_live_round_start_and_grade(client, signup_payload, monkeypatch):
    _patch_agent(monkeypatch)
    student = _signup(client, signup_payload, "student")
    stok = student["access_token"]
    s = _start_voice_session(client, stok)

    # Start round 1 → signed url + per-round overrides.
    r = client.post(f"/api/v1/interviews/{s['id']}/live/rounds/1/start", headers=_auth(stok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["signed_url"].startswith("wss://")
    assert body["round_number"] == 1
    assert body["system_prompt"] and body["first_message"] and body["voice_id"]

    # Finalize round 1 → the TestClient runs the background grading task inline.
    r = client.post(
        f"/api/v1/interviews/{s['id']}/live/rounds/1/finalize",
        headers=_auth(stok),
        json={"conversation_id": "conv_test_1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["grading"] is True
    assert r.json()["interview_completing"] is False

    # The graded round now shows scored turns + an average.
    got = client.get(f"/api/v1/interviews/{s['id']}", headers=_auth(stok)).json()
    r1 = next(rs for rs in got["round_summaries"] if rs["round_number"] == 1)
    assert r1["avg_score"] == 6.0  # (8 + 4) / 2
    user_turns = [t for t in got["transcript"] if t["role"] == "user"]
    assert len(user_turns) == 2
    assert user_turns[0]["score"] == 8.0
    assert user_turns[1]["score"] == 4.0
    assert user_turns[0]["score_reason"]


def test_live_full_five_rounds_completes_and_debriefs(client, signup_payload, monkeypatch):
    _patch_agent(monkeypatch)
    student = _signup(client, signup_payload, "student")
    stok = student["access_token"]
    s = _start_voice_session(client, stok)

    for rnd in range(1, 6):
        rs = client.post(
            f"/api/v1/interviews/{s['id']}/live/rounds/{rnd}/start", headers=_auth(stok)
        )
        assert rs.status_code == 200, rs.text
        rf = client.post(
            f"/api/v1/interviews/{s['id']}/live/rounds/{rnd}/finalize",
            headers=_auth(stok),
            json={"conversation_id": f"conv_{rnd}"},
        )
        assert rf.status_code == 200, rf.text
        assert rf.json()["interview_completing"] is (rnd == 5)

    got = client.get(f"/api/v1/interviews/{s['id']}", headers=_auth(stok)).json()
    assert got["status"] == "completed"
    assert got["overall_score"] is not None
    assert got["feedback_report"] is not None
    assert got["feedback_report"]["hire_verdict"] in (
        "strong_hire",
        "hire",
        "leaning_no",
        "no_hire",
    )
    assert all(rs["avg_score"] is not None for rs in got["round_summaries"])


def _run_round(client, stok, sid, rnd, cid=None):
    rs = client.post(f"/api/v1/interviews/{sid}/live/rounds/{rnd}/start", headers=_auth(stok))
    assert rs.status_code == 200, rs.text
    rf = client.post(
        f"/api/v1/interviews/{sid}/live/rounds/{rnd}/finalize",
        headers=_auth(stok),
        json={"conversation_id": cid or f"conv_{rnd}"},
    )
    assert rf.status_code == 200, rf.text
    return rf.json()


def test_rounds_run_in_any_order_complete(client, signup_payload, monkeypatch):
    _patch_agent(monkeypatch)
    student = _signup(client, signup_payload, "student")
    stok = student["access_token"]
    s = _start_voice_session(client, stok)

    order = [3, 1, 5, 2, 4]
    for i, rnd in enumerate(order):
        body = _run_round(client, stok, s["id"], rnd)
        # 'completing' fires on the 5th distinct round, whatever its number.
        assert body["interview_completing"] is (i == len(order) - 1)

    got = client.get(f"/api/v1/interviews/{s['id']}", headers=_auth(stok)).json()
    assert got["status"] == "completed"
    assert got["feedback_report"] is not None
    assert all(rs["avg_score"] is not None for rs in got["round_summaries"])
    # Transcript stays grouped by round ascending, regardless of run order.
    rounds_seq = [t["round_number"] for t in got["transcript"]]
    assert rounds_seq == sorted(rounds_seq)


def test_rerun_round_replaces_not_accumulates(client, signup_payload, monkeypatch):
    _patch_agent(monkeypatch)
    student = _signup(client, signup_payload, "student")
    stok = student["access_token"]
    s = _start_voice_session(client, stok)

    _run_round(client, stok, s["id"], 1, cid="conv_a")
    _run_round(client, stok, s["id"], 1, cid="conv_b")  # re-do round 1

    got = client.get(f"/api/v1/interviews/{s['id']}", headers=_auth(stok)).json()
    r1_user_turns = [
        t for t in got["transcript"] if t["round_number"] == 1 and t["role"] == "user"
    ]
    assert len(r1_user_turns) == 2  # replaced, not doubled to 4
    r1 = next(rs for rs in got["round_summaries"] if rs["round_number"] == 1)
    assert r1["avg_score"] == 6.0
