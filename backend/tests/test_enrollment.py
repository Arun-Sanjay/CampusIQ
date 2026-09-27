"""Tests for usernames, login-by-identifier, and per-subject enrollment gating."""
from __future__ import annotations

import uuid


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _signup(client, signup_payload, role: str, username: str | None = None) -> tuple[dict, dict]:
    payload = signup_payload(role)
    if username:
        payload["username"] = username
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code in (200, 201), r.text
    return payload, r.json()


def test_signup_returns_username_and_login_by_username(client, signup_payload):
    payload, body = _signup(client, signup_payload, "student")
    assert body["user"]["username"] == payload["username"]

    # Log in with the username instead of the email.
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": payload["username"], "password": payload["password"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["username"] == payload["username"]


def test_duplicate_username_rejected(client, signup_payload):
    p1 = signup_payload("student")
    p1["username"] = "takenhandle"
    assert client.post("/api/v1/auth/signup", json=p1).status_code in (200, 201)

    p2 = signup_payload("teacher")
    p2["username"] = "TakenHandle"  # case-insensitive collision
    r = client.post("/api/v1/auth/signup", json=p2)
    assert r.status_code == 409, r.text


def test_invalid_username_rejected(client, signup_payload):
    p = signup_payload("student")
    p["username"] = "has spaces!"
    assert client.post("/api/v1/auth/signup", json=p).status_code == 422


def test_enrollment_gates_quiz_visibility(client, signup_payload, db_session):
    from app.models.quiz import Difficulty, Question, QuestionType, Quiz
    from app.models.user import Subject

    # Teacher + two students.
    _, tbody = _signup(client, signup_payload, "teacher")
    teacher_id = uuid.UUID(tbody["user"]["id"])
    teacher_token = tbody["access_token"]
    _, a_body = _signup(client, signup_payload, "student", username="enrolledstud")
    _, b_body = _signup(client, signup_payload, "student", username="outsiderstud")

    # A published quiz under a teacher-owned subject (inserted directly).
    subject = Subject(teacher_id=teacher_id, code=f"ENR{uuid.uuid4().hex[:6]}", name="Enroll Test")
    db_session.add(subject)
    db_session.flush()
    quiz = Quiz(
        subject_id=subject.id,
        created_by_id=teacher_id,
        title="Gated Quiz",
        difficulty=Difficulty.MEDIUM,
        is_published=True,
        is_ai_generated=False,
    )
    db_session.add(quiz)
    db_session.flush()
    db_session.add(
        Question(
            quiz_id=quiz.id,
            order_index=0,
            question_text="2 + 2 = ?",
            question_type=QuestionType.MCQ,
            options=["3", "4"],
            correct_answer="4",
            difficulty=Difficulty.EASY,
            topic="Math",
        )
    )
    db_session.commit()
    quiz_id = str(quiz.id)

    # Before enrollment, neither student sees the quiz.
    r = client.get("/api/v1/quizzes/", headers=_auth(a_body["access_token"]))
    assert r.status_code == 200
    assert all(x["id"] != quiz_id for x in r.json())

    # Teacher enrolls student A by username.
    r = client.post(
        f"/api/v1/enrollments/subjects/{subject.id}",
        json={"username": "enrolledstud"},
        headers=_auth(teacher_token),
    )
    assert r.status_code == 201, r.text
    assert r.json()["username"] == "enrolledstud"

    # Student A now sees the quiz; student B still does not.
    ra = client.get("/api/v1/quizzes/", headers=_auth(a_body["access_token"]))
    assert any(x["id"] == quiz_id for x in ra.json())
    rb = client.get("/api/v1/quizzes/", headers=_auth(b_body["access_token"]))
    assert all(x["id"] != quiz_id for x in rb.json())

    # Roster lists student A.
    rr = client.get(f"/api/v1/enrollments/subjects/{subject.id}", headers=_auth(teacher_token))
    assert rr.status_code == 200
    assert [s["username"] for s in rr.json()["students"]] == ["enrolledstud"]

    # Enrolling an unknown username 404s.
    r404 = client.post(
        f"/api/v1/enrollments/subjects/{subject.id}",
        json={"username": "nobody.here"},
        headers=_auth(teacher_token),
    )
    assert r404.status_code == 404

    # Unenroll → student A loses visibility again.
    student_a_id = a_body["user"]["id"]
    rd = client.delete(
        f"/api/v1/enrollments/subjects/{subject.id}/students/{student_a_id}",
        headers=_auth(teacher_token),
    )
    assert rd.status_code == 204
    ra2 = client.get("/api/v1/quizzes/", headers=_auth(a_body["access_token"]))
    assert all(x["id"] != quiz_id for x in ra2.json())


def test_student_cannot_manage_enrollment(client, signup_payload):
    _, sbody = _signup(client, signup_payload, "student")
    r = client.get(
        f"/api/v1/enrollments/subjects/{uuid.uuid4()}",
        headers=_auth(sbody["access_token"]),
    )
    assert r.status_code == 403
