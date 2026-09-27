"""Tests for quiz practice/test modes + proctoring + marks-based scoring."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone


def _auth(t): return {"Authorization": f"Bearer {t}"}


def _signup(client, signup_payload, role):
    r = client.post("/api/v1/auth/signup", json=signup_payload(role))
    assert r.status_code in (200, 201), r.text
    return r.json()


def _make_test_quiz(db_session, teacher_id, *, mode="test", max_attempts=1,
                    proctored=True, cie_component="test_1", available_until=None):
    from app.models.quiz import (CIEComponent, Difficulty, Question, QuestionType,
                                 Quiz, QuizMode)
    from app.models.user import Subject
    subj = Subject(teacher_id=teacher_id, code=f"QM{uuid.uuid4().hex[:6]}", name="Quiz Modes",
                   category="theory", credits=3, cie_max=100, see_max=100, semester=4)
    db_session.add(subj)
    db_session.flush()
    quiz = Quiz(
        subject_id=subj.id, created_by_id=teacher_id, title="Proctored Test",
        difficulty=Difficulty.MEDIUM, is_published=True, is_ai_generated=False,
        mode=QuizMode(mode), max_attempts=max_attempts, requires_proctoring=proctored,
        cie_component=CIEComponent(cie_component) if cie_component else None,
        total_marks=10, time_limit_minutes=30, available_until=available_until,
    )
    db_session.add(quiz)
    db_session.flush()
    for label, ans, co in [("Q1", "A", "CO1"), ("Q2", "B", "CO2")]:
        db_session.add(Question(
            quiz_id=quiz.id, order_index=int(label[1]), question_text=f"{label}?",
            question_type=QuestionType.MCQ, options=["A", "B", "C", "D"],
            correct_answer=ans, difficulty=Difficulty.MEDIUM, topic="T", marks=5, co=co))
    db_session.commit()
    return subj, quiz


def _enroll(db_session, subject_id, student_id):
    from app.models.user import SubjectEnrollment
    db_session.add(SubjectEnrollment(subject_id=subject_id, student_id=student_id))
    db_session.commit()


def _question_ids(client, quiz_id, stok):
    q = client.get(f"/api/v1/quizzes/{quiz_id}", headers=_auth(stok)).json()
    return {qq["question_text"]: qq["id"] for qq in q["questions"]}, q


def test_proctored_test_full_flow(client, signup_payload, db_session):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid, sid = uuid.UUID(teacher["user"]["id"]), uuid.UUID(student["user"]["id"])
    subj, quiz = _make_test_quiz(db_session, tid)
    _enroll(db_session, subj.id, sid)
    ttok, stok = teacher["access_token"], student["access_token"]

    qids, qview = _question_ids(client, str(quiz.id), stok)
    assert qview["mode"] == "test"
    assert qview["requires_proctoring"] is True
    assert qview["questions"][0]["marks"] == 5
    assert qview["can_attempt"] is True

    # Start → server-stamped attempt.
    start = client.post(f"/api/v1/quizzes/{quiz.id}/attempts/start", headers=_auth(stok))
    assert start.status_code == 200, start.text
    attempt_id = start.json()["attempt_id"]
    assert start.json()["requires_proctoring"] is True
    assert start.json()["time_limit_seconds"] == 1800

    # Proctor event during the attempt.
    ev = client.post(f"/api/v1/quizzes/{quiz.id}/proctor-events", headers=_auth(stok),
                     json={"type": "tab_switch"})
    assert ev.status_code == 204

    # Submit: Q1 correct (A), Q2 wrong → 5/10 marks, score 50%.
    sub = client.post(f"/api/v1/quizzes/{quiz.id}/attempts", headers=_auth(stok), json={
        "answers": [{"question_id": qids["Q1?"], "student_answer": "A"},
                    {"question_id": qids["Q2?"], "student_answer": "C"}],
        "started_attempt_id": attempt_id,
        "proctor": {"tab_switch_count": 1, "fullscreen_exits": 2, "auto_submitted": True},
        "violations": [{"type": "fullscreen_exit"}],
    })
    assert sub.status_code in (200, 201), sub.text
    body = sub.json()
    assert body["marks_obtained"] == 5.0
    assert body["marks_possible"] == 10.0
    assert body["score"] == 50.0
    assert body["is_proctored"] is True
    assert body["auto_submitted"] is True
    co = {c["co"]: c for c in body["co_attainment"]}
    assert co["CO1"]["obtained"] == 5.0 and co["CO1"]["pct"] == 100.0
    assert co["CO2"]["obtained"] == 0.0

    # Single attempt: a second start is rejected.
    again = client.post(f"/api/v1/quizzes/{quiz.id}/attempts/start", headers=_auth(stok))
    assert again.status_code == 409

    # Proctor report (teacher).
    rep = client.get(f"/api/v1/quizzes/{quiz.id}/proctor-report", headers=_auth(ttok)).json()
    assert len(rep["rows"]) == 1
    row = rep["rows"][0]
    assert row["fullscreen_exits"] == 2
    assert row["auto_submitted"] is True
    assert row["marks_obtained"] == 5.0

    # CIE feed: a quiz-sourced ExamResult now exists for the subject.
    from app.models.grading import Exam, ExamResult
    from sqlalchemy import select
    res = db_session.scalar(
        select(ExamResult).join(Exam, Exam.id == ExamResult.exam_id)
        .where(Exam.subject_id == subj.id, ExamResult.student_id == sid)
    )
    assert res is not None
    assert float(res.total_obtained) == 5.0
    assert res.source.value == "quiz"


def test_availability_window_blocks_start(client, signup_payload, db_session):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid, sid = uuid.UUID(teacher["user"]["id"]), uuid.UUID(student["user"]["id"])
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    subj, quiz = _make_test_quiz(db_session, tid, available_until=past)
    _enroll(db_session, subj.id, sid)
    r = client.post(f"/api/v1/quizzes/{quiz.id}/attempts/start", headers=_auth(student["access_token"]))
    assert r.status_code == 403


def test_practice_mode_unlimited(client, signup_payload, db_session):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid, sid = uuid.UUID(teacher["user"]["id"]), uuid.UUID(student["user"]["id"])
    subj, quiz = _make_test_quiz(db_session, tid, mode="practice", max_attempts=0,
                                 proctored=False, cie_component=None)
    _enroll(db_session, subj.id, sid)
    stok = student["access_token"]
    qids, qview = _question_ids(client, str(quiz.id), stok)
    assert qview["mode"] == "practice"
    # Two practice submissions both succeed (unlimited).
    for _ in range(2):
        r = client.post(f"/api/v1/quizzes/{quiz.id}/attempts", headers=_auth(stok), json={
            "answers": [{"question_id": qids["Q1?"], "student_answer": "A"},
                        {"question_id": qids["Q2?"], "student_answer": "B"}]})
        assert r.status_code in (200, 201), r.text
        assert r.json()["score"] == 100.0
