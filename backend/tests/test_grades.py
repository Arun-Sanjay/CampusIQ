"""Integration tests for the grade engine orchestrator + grades API."""
from __future__ import annotations

import uuid


def _auth(t): return {"Authorization": f"Bearer {t}"}


def _signup(client, signup_payload, role):
    r = client.post("/api/v1/auth/signup", json=signup_payload(role))
    assert r.status_code in (200, 201), r.text
    return r.json()


def _subject(db_session, teacher_id, **kw):
    from app.models.user import Subject
    s = Subject(teacher_id=teacher_id, code=f"GR{uuid.uuid4().hex[:6]}", name="Test Subject",
                category=kw.get("category", "theory"), credits=kw.get("credits", 4),
                cie_max=kw.get("cie_max", 100), see_max=kw.get("see_max", 100),
                semester=kw.get("semester", 4))
    db_session.add(s)
    db_session.commit()
    return s


def _enroll(db_session, subject_id, student_id):
    from app.models.user import SubjectEnrollment
    db_session.add(SubjectEnrollment(subject_id=subject_id, student_id=student_id))
    db_session.commit()


def _exam(client, ttok, subject_id, *, kind="test", max_marks=100, component_key=None):
    r = client.post("/api/v1/grading/exams", headers=_auth(ttok), json={
        "subject_id": str(subject_id), "title": f"{kind}-{uuid.uuid4().hex[:4]}",
        "kind": kind, "max_marks": max_marks, "component_key": component_key})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _enter(client, ttok, exam_id, student_id, obtained):
    r = client.post(f"/api/v1/grading/exams/{exam_id}/results/bulk", headers=_auth(ttok),
                    json={"results": [{"student_id": str(student_id), "total_obtained": obtained}]})
    assert r.status_code == 200, r.text


def test_proportional_grade_transcript_sgpa(client, signup_payload, db_session):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid, sid = uuid.UUID(teacher["user"]["id"]), uuid.UUID(student["user"]["id"])
    subj = _subject(db_session, tid, credits=4, semester=4)
    _enroll(db_session, subj.id, sid)
    ttok, stok = teacher["access_token"], student["access_token"]

    cie = _exam(client, ttok, subj.id, kind="test", max_marks=100)
    see = _exam(client, ttok, subj.id, kind="see", max_marks=100)
    _enter(client, ttok, cie, sid, 80)   # CIE 80/100
    _enter(client, ttok, see, sid, 70)   # SEE 70/100

    # CIE_50=40, SEE_50=35, final=75 → A (gp 8); SGPA=8, CGPA=8, %=80.
    tr = client.get("/api/v1/grades/me", headers=_auth(stok)).json()
    assert tr["cgpa"] == 8.0
    assert tr["percentage"] == 80.0
    assert len(tr["semesters"]) == 1
    sem = tr["semesters"][0]
    assert sem["semester"] == 4
    assert sem["sgpa"] == 8.0
    row = sem["subjects"][0]
    assert row["final_rounded"] == 75
    assert row["letter_grade"] == "A"
    assert row["grade_point"] == 8
    assert row["passed"] is True


def test_see_gate_failure_is_F(client, signup_payload, db_session):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid, sid = uuid.UUID(teacher["user"]["id"]), uuid.UUID(student["user"]["id"])
    subj = _subject(db_session, tid, credits=3, semester=4)
    _enroll(db_session, subj.id, sid)
    ttok, stok = teacher["access_token"], student["access_token"]
    _enter(client, ttok, _exam(client, ttok, subj.id, kind="test", max_marks=100), sid, 90)  # CIE 90%
    _enter(client, ttok, _exam(client, ttok, subj.id, kind="see", max_marks=100), sid, 30)   # SEE 30% < 35%
    tr = client.get("/api/v1/grades/me", headers=_auth(stok)).json()
    row = tr["semesters"][0]["subjects"][0]
    assert row["letter_grade"] == "F"
    assert row["grade_point"] == 0
    assert row["gate_failed"] == "see"
    assert tr["cgpa"] == 0.0  # F excluded → 0 gradable credits


def test_component_assembly(client, signup_payload, db_session):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid, sid = uuid.UUID(teacher["user"]["id"]), uuid.UUID(student["user"]["id"])
    subj = _subject(db_session, tid, credits=4, semester=4, cie_max=100, see_max=100)
    _enroll(db_session, subj.id, sid)
    ttok, stok = teacher["access_token"], student["access_token"]

    # Configure CIE components: Quizzes 20, Tests 40, Experiential 40.
    client.put(f"/api/v1/grading/subjects/{subj.id}/config", headers=_auth(ttok), json={
        "components": [
            {"key": "quizzes", "label": "Quizzes", "part": "theory", "max": 20, "kind": "quiz"},
            {"key": "tests", "label": "Tests", "part": "theory", "max": 40, "kind": "test"},
            {"key": "exp", "label": "Experiential", "part": "theory", "max": 40, "kind": "experiential"},
        ]})
    q1 = _exam(client, ttok, subj.id, kind="quiz", max_marks=10, component_key="quizzes")
    q2 = _exam(client, ttok, subj.id, kind="quiz", max_marks=10, component_key="quizzes")
    t1 = _exam(client, ttok, subj.id, kind="test", max_marks=50, component_key="tests")
    t2 = _exam(client, ttok, subj.id, kind="test", max_marks=50, component_key="tests")
    ex = _exam(client, ttok, subj.id, kind="experiential", max_marks=40, component_key="exp")
    see = _exam(client, ttok, subj.id, kind="see", max_marks=100)
    for e, m in [(q1, 8), (q2, 9), (t1, 40), (t2, 44), (ex, 35), (see, 70)]:
        _enter(client, ttok, e, sid, m)

    # quizzes 17/20, tests 33.6/40, exp 35/40 → CIE 85.6; see 70 → final 78 → A.
    row = client.get("/api/v1/grades/me", headers=_auth(stok)).json()["semesters"][0]["subjects"][0]
    assert row["cie_obtained"] == 85.6
    assert row["final_rounded"] == 78
    assert row["letter_grade"] == "A"


def test_class_overview(client, signup_payload, db_session):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid, sid = uuid.UUID(teacher["user"]["id"]), uuid.UUID(student["user"]["id"])
    subj = _subject(db_session, tid)
    _enroll(db_session, subj.id, sid)
    ttok = teacher["access_token"]
    _enter(client, ttok, _exam(client, ttok, subj.id, kind="test", max_marks=100), sid, 80)
    _enter(client, ttok, _exam(client, ttok, subj.id, kind="see", max_marks=100), sid, 70)
    ov = client.get(f"/api/v1/grades/class?subject_id={subj.id}", headers=_auth(ttok)).json()
    assert ov["subject_code"] == subj.code
    assert len(ov["students"]) == 1
    assert ov["students"][0]["final_score"] == 75.0
    assert ov["students"][0]["letter_grade"] == "A"


def test_students_cannot_view_class_grades(client, signup_payload):
    student = _signup(client, signup_payload, "student")
    r = client.get(f"/api/v1/grades/class?subject_id={uuid.uuid4()}", headers=_auth(student["access_token"]))
    assert r.status_code == 403
