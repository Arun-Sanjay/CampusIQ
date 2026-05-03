"""Dashboard endpoints: student/teacher/admin shapes match schemas."""
from __future__ import annotations


def _signup(client, signup_payload, role: str) -> dict:
    r = client.post("/api/v1/auth/signup", json=signup_payload(role))
    assert r.status_code in (200, 201), r.text
    data = r.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_student_dashboard_shape(client, signup_payload):
    headers = _signup(client, signup_payload, "student")
    r = client.get("/api/v1/dashboard/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "xp" in body and "score" in body and "stats" in body
    assert body["xp"]["current_level"] >= 1
    assert isinstance(body["tasks"], list)


def test_teacher_dashboard_returns_zero_baseline(client, signup_payload):
    headers = _signup(client, signup_payload, "teacher")
    r = client.get("/api/v1/dashboard/teacher", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["students_total"] == 0
    assert body["recent_uploads"] == []
    assert any(s["label"] == "TOTAL STUDENTS" for s in body["stats"])


def test_admin_dashboard_counts_users(client, signup_payload):
    _signup(client, signup_payload, "student")
    _signup(client, signup_payload, "teacher")
    headers = _signup(client, signup_payload, "admin")
    r = client.get("/api/v1/dashboard/admin", headers=headers)
    assert r.status_code == 200
    body = r.json()
    total_users = next(s for s in body["stats"] if s["label"] == "TOTAL USERS")
    assert int(total_users["value"].replace(",", "")) >= 3
    breakdown = {row["role"]: row["count"] for row in body["user_breakdown"]}
    assert breakdown["student"] >= 1 and breakdown["teacher"] >= 1 and breakdown["admin"] >= 1


def test_admin_users_list_filters_by_role(client, signup_payload):
    _signup(client, signup_payload, "student")
    _signup(client, signup_payload, "student")
    headers = _signup(client, signup_payload, "admin")
    r = client.get("/api/v1/admin/users?role=student", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert all(item["role"] == "student" for item in body["items"])


def test_admin_users_search_matches_email(client, signup_payload):
    payload = signup_payload("teacher")
    payload["email"] = "specific-target@campusiq.dev"
    client.post("/api/v1/auth/signup", json=payload)
    headers = _signup(client, signup_payload, "admin")
    r = client.get(
        "/api/v1/admin/users?search=specific-target",
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "specific-target@campusiq.dev"
