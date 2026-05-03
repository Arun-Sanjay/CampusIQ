"""Algorithm endpoint smoke tests: schedule generation and inclusion-exclusion.

These verify that the branch-and-bound + Dijkstra-style code paths produce
shaped output, not specific values (the algorithms have stochastic priorities
seeded by the user's data).
"""
from __future__ import annotations


def _student_headers(client, signup_payload) -> dict:
    r = client.post("/api/v1/auth/signup", json=signup_payload("student"))
    assert r.status_code in (200, 201)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_generate_schedule_returns_slots(client, signup_payload):
    headers = _student_headers(client, signup_payload)
    payload = {
        "tasks": [
            {"topic": "Arrays", "hours": 2, "priority": 9, "subject_code": "DAA"},
            {"topic": "Trees", "hours": 3, "priority": 7, "subject_code": "DAA"},
            {"topic": "Soft Skills", "hours": 2, "priority": 4, "subject_code": None},
        ],
        "days": 3,
    }
    r = client.post("/api/v1/algorithms/schedule/generate", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "slots" in body
    assert "scheduled_tasks" in body
    assert "explored_nodes" in body
    assert body["total_value"] >= 0


def test_generate_schedule_rejects_empty(client, signup_payload):
    headers = _student_headers(client, signup_payload)
    r = client.post(
        "/api/v1/algorithms/schedule/generate",
        json={"tasks": [], "days": 3},
        headers=headers,
    )
    # Pydantic / service should reject empty task list with a 4xx.
    assert r.status_code >= 400
