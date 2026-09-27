"""Integration tests for the AI auto-grader (Claude vision mocked)."""
from __future__ import annotations

import uuid

import fitz
import pytest
from sqlalchemy import select

from app.api.deps import _reset_claude_buckets_for_tests


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _signup(client, signup_payload, role: str, username: str | None = None) -> dict:
    payload = signup_payload(role)
    if username:
        payload["username"] = username
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _png_bytes() -> bytes:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 100))
    pix.clear_with(255)
    return pix.tobytes("png")


def _make_subject(db_session, teacher_id: uuid.UUID):
    from app.models.user import Subject
    s = Subject(teacher_id=teacher_id, code=f"GR{uuid.uuid4().hex[:6]}", name="IoT Grading",
                category="theory", credits=4, cie_max=20, see_max=100)
    db_session.add(s)
    db_session.commit()
    return s


def _enroll(db_session, subject_id, student_id, usn: str | None = None):
    from app.models.user import StudentProfile, SubjectEnrollment
    db_session.add(SubjectEnrollment(subject_id=subject_id, student_id=student_id))
    if usn:
        sp = db_session.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
        if sp is None:
            sp = StudentProfile(user_id=student_id)
            db_session.add(sp)
        sp.usn = usn
    db_session.commit()


def _two_question_exam(client, teacher_token, subject_id) -> str:
    r = client.post("/api/v1/grading/exams", headers=_auth(teacher_token), json={
        "subject_id": str(subject_id), "title": "CIE-2", "kind": "test", "max_marks": 20,
    })
    assert r.status_code == 200, r.text
    exam_id = r.json()["id"]
    for label, co in (("1", "CO1"), ("2", "CO2")):
        rq = client.post(f"/api/v1/grading/exams/{exam_id}/questions", headers=_auth(teacher_token), json={
            "label": label, "question_text": f"Q{label}", "model_answer": "ans",
            "max_marks": 10, "co": co, "order_index": int(label),
        })
        assert rq.status_code == 200, rq.text
    rc = client.post(f"/api/v1/grading/exams/{exam_id}/scheme/confirm", headers=_auth(teacher_token))
    assert rc.status_code == 200, rc.text
    assert rc.json()["scheme_status"] == "ready"
    return exam_id


def _mock_vision(monkeypatch, *, usn="1RV23CS001", q1=8, q2=5, q2_conf=0.4):
    import json as _json
    from app.services import claude_client

    def stub(system, text, images, **kw):
        return _json.dumps({
            "detected_usn": usn, "detected_name": "Test Student",
            "answers": [
                {"label": "1", "extracted_answer": "a1", "awarded_marks": q1, "max_marks": 10,
                 "co": "CO1", "ocr_confidence": 0.95, "confidence": 0.9, "needs_review": False},
                {"label": "2", "extracted_answer": "a2", "awarded_marks": q2, "max_marks": 10,
                 "co": "CO2", "ocr_confidence": 0.9, "confidence": q2_conf, "needs_review": False},
            ],
        })

    monkeypatch.setattr(claude_client, "generate_completion_vision", stub)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _reset_claude_buckets_for_tests()
    yield


def test_full_autograde_flow(client, signup_payload, db_session, monkeypatch):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid = uuid.UUID(teacher["user"]["id"])
    sid = uuid.UUID(student["user"]["id"])
    subject = _make_subject(db_session, tid)
    _enroll(db_session, subject.id, sid, usn="1RV23CS001")
    ttok = teacher["access_token"]

    exam_id = _two_question_exam(client, ttok, subject.id)
    _mock_vision(monkeypatch)

    # Upload one student's sheet (auto-match by USN). Background task grades it.
    r = client.post(
        f"/api/v1/grading/exams/{exam_id}/answer-sheets",
        headers=_auth(ttok),
        files={"file": ("ans.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200, r.text
    sheet_id = r.json()["id"]

    # After background grading: matched, scored, Q2 flagged for review (conf 0.4).
    detail = client.get(f"/api/v1/grading/answer-sheets/{sheet_id}", headers=_auth(ttok)).json()
    assert detail["status"] == "review"
    assert detail["match_source"] == "usn"
    assert str(detail["student_id"]) == str(sid)
    assert detail["total_awarded"] == 13.0
    assert detail["needs_review_count"] == 1
    grades = {g["label"]: g for g in detail["grades"]}
    assert grades["1"]["awarded_marks"] == 8.0
    assert grades["2"]["needs_review"] is True

    # Class CO attainment reflects the marks.
    att = client.get(f"/api/v1/grading/exams/{exam_id}/attainment", headers=_auth(ttok)).json()
    per_co = {row["co"]: row for row in att["per_co"]}
    assert per_co["CO1"]["pct"] == 80.0
    assert per_co["CO2"]["pct"] == 50.0

    # Review queue has the flagged Q2; teacher overrides it.
    queue = client.get(f"/api/v1/grading/exams/{exam_id}/review-queue", headers=_auth(ttok)).json()
    assert len(queue) == 1
    grade_id = queue[0]["question_grade_id"]
    ro = client.patch(f"/api/v1/grading/question-grades/{grade_id}", headers=_auth(ttok),
                      json={"teacher_marks": 9})
    assert ro.status_code == 200, ro.text
    assert ro.json()["effective_marks"] == 9.0

    # Override cleared the review flag → sheet graded; finalize succeeds.
    detail2 = client.get(f"/api/v1/grading/answer-sheets/{sheet_id}", headers=_auth(ttok)).json()
    assert detail2["needs_review_count"] == 0
    assert detail2["total_awarded"] == 17.0
    rf = client.post(f"/api/v1/grading/answer-sheets/{sheet_id}/finalize", headers=_auth(ttok))
    assert rf.status_code == 200, rf.text
    assert rf.json()["status"] == "finalized"


def test_override_cannot_exceed_max(client, signup_payload, db_session, monkeypatch):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    subject = _make_subject(db_session, uuid.UUID(teacher["user"]["id"]))
    _enroll(db_session, subject.id, uuid.UUID(student["user"]["id"]), usn="1RV23CS001")
    ttok = teacher["access_token"]
    exam_id = _two_question_exam(client, ttok, subject.id)
    _mock_vision(monkeypatch)
    r = client.post(f"/api/v1/grading/exams/{exam_id}/answer-sheets", headers=_auth(ttok),
                    files={"file": ("a.png", _png_bytes(), "image/png")})
    sheet_id = r.json()["id"]
    detail = client.get(f"/api/v1/grading/answer-sheets/{sheet_id}", headers=_auth(ttok)).json()
    gid = detail["grades"][0]["id"]
    bad = client.patch(f"/api/v1/grading/question-grades/{gid}", headers=_auth(ttok),
                       json={"teacher_marks": 99})
    assert bad.status_code == 400


def test_grading_blocked_until_scheme_ready(client, signup_payload, db_session, monkeypatch):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    subject = _make_subject(db_session, uuid.UUID(teacher["user"]["id"]))
    _enroll(db_session, subject.id, uuid.UUID(student["user"]["id"]))
    ttok = teacher["access_token"]
    # Create exam + question but DON'T confirm (status stays 'pending').
    r = client.post("/api/v1/grading/exams", headers=_auth(ttok),
                    json={"subject_id": str(subject.id), "title": "X", "max_marks": 10})
    exam_id = r.json()["id"]
    client.post(f"/api/v1/grading/exams/{exam_id}/questions", headers=_auth(ttok),
                json={"label": "1", "question_text": "q", "max_marks": 10, "co": "CO1"})
    _mock_vision(monkeypatch)
    up = client.post(f"/api/v1/grading/exams/{exam_id}/answer-sheets", headers=_auth(ttok),
                     files={"file": ("a.png", _png_bytes(), "image/png")})
    sheet_id = up.json()["id"]
    detail = client.get(f"/api/v1/grading/answer-sheets/{sheet_id}", headers=_auth(ttok)).json()
    assert detail["status"] == "failed"


def test_idempotent_regrade_preserves_override(client, signup_payload, db_session, monkeypatch):
    from app.models.grading import AnswerSheet, QuestionGrade
    from app.services import answersheet_grader

    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    subject = _make_subject(db_session, uuid.UUID(teacher["user"]["id"]))
    _enroll(db_session, subject.id, uuid.UUID(student["user"]["id"]), usn="1RV23CS001")
    ttok = teacher["access_token"]
    exam_id = _two_question_exam(client, ttok, subject.id)
    _mock_vision(monkeypatch)
    r = client.post(f"/api/v1/grading/exams/{exam_id}/answer-sheets", headers=_auth(ttok),
                    files={"file": ("a.png", _png_bytes(), "image/png")})
    sheet_id = uuid.UUID(r.json()["id"])
    # Override Q1 → 3
    detail = client.get(f"/api/v1/grading/answer-sheets/{sheet_id}", headers=_auth(ttok)).json()
    gid = next(g["id"] for g in detail["grades"] if g["label"] == "1")
    client.patch(f"/api/v1/grading/question-grades/{gid}", headers=_auth(ttok), json={"teacher_marks": 3})
    # Re-grade (force=False) — should keep the override, refresh the rest.
    answersheet_grader.grade_answer_sheet(sheet_id, force=False)
    db_session.expire_all()
    grades = db_session.scalars(
        select(QuestionGrade).join(AnswerSheet).where(QuestionGrade.answer_sheet_id == sheet_id)
    ).all()
    by_marks = {float(g.max_marks): g for g in grades}
    overridden = [g for g in grades if g.is_overridden]
    assert len(overridden) == 1
    assert overridden[0].effective_marks == 3.0


def test_students_cannot_access_grading(client, signup_payload):
    student = _signup(client, signup_payload, "student")
    r = client.get("/api/v1/grading/exams", headers=_auth(student["access_token"]))
    assert r.status_code == 403


def test_scheme_parse_text(monkeypatch):
    import json as _json
    from app.services import claude_client, scheme_parser

    def stub(system, user_message, **kw):
        return "```json\n" + _json.dumps({
            "title": "CIE-2", "total_marks": 20,
            "course_outcomes": [{"code": "CO1", "text": "x"}],
            "co_mark_grid": {"CO1": 10, "CO2": 10},
            "questions": [
                {"label": "1", "part": "part_a", "question_text": "q1", "model_answer": "a1",
                 "max_marks": 10, "co": "CO1", "bloom": "L2"},
                {"label": "2", "part": "part_b", "question_text": "q2", "model_answer": "a2",
                 "max_marks": 10, "co": "CO2", "bloom": "L3"},
            ],
        }) + "\n```"

    monkeypatch.setattr(claude_client, "generate_completion", stub)
    data = scheme_parser.parse_scheme_text("some scheme text " * 40)
    assert data is not None
    assert data["total_marks"] == 20
    assert len(data["questions"]) == 2
    assert data["co_mark_grid"]["CO1"] == 10


# ── deep stress: AI robustness + matching + isolation ────────────────────────
def _setup_ready_exam(client, signup_payload, db_session, usn="1RV23CS001"):
    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    subject = _make_subject(db_session, uuid.UUID(teacher["user"]["id"]))
    _enroll(db_session, subject.id, uuid.UUID(student["user"]["id"]), usn=usn)
    exam_id = _two_question_exam(client, teacher["access_token"], subject.id)
    return teacher, student, subject, exam_id


def test_malformed_ai_json_fails_gracefully(client, signup_payload, db_session, monkeypatch):
    from app.services import claude_client
    teacher, student, subject, exam_id = _setup_ready_exam(client, signup_payload, db_session)
    monkeypatch.setattr(claude_client, "generate_completion_vision", lambda *a, **k: "not json at all")
    ttok = teacher["access_token"]
    r = client.post(f"/api/v1/grading/exams/{exam_id}/answer-sheets", headers=_auth(ttok),
                    files={"file": ("a.png", _png_bytes(), "image/png")})
    detail = client.get(f"/api/v1/grading/answer-sheets/{r.json()['id']}", headers=_auth(ttok)).json()
    assert detail["status"] == "failed"
    assert detail["error_detail"]


def test_over_award_clamped_and_missing_answer_flagged(client, signup_payload, db_session, monkeypatch):
    import json as _json
    from app.services import claude_client
    teacher, student, subject, exam_id = _setup_ready_exam(client, signup_payload, db_session)
    ttok = teacher["access_token"]

    def stub(system, text, images, **kw):
        # Q1 over-awarded (50 > max 10); Q2 omitted entirely.
        return _json.dumps({"detected_usn": "1RV23CS001", "answers": [
            {"label": "1", "awarded_marks": 50, "max_marks": 10, "co": "CO1",
             "confidence": 0.9, "ocr_confidence": 0.9}]})
    monkeypatch.setattr(claude_client, "generate_completion_vision", stub)

    r = client.post(f"/api/v1/grading/exams/{exam_id}/answer-sheets", headers=_auth(ttok),
                    files={"file": ("a.png", _png_bytes(), "image/png")})
    detail = client.get(f"/api/v1/grading/answer-sheets/{r.json()['id']}", headers=_auth(ttok)).json()
    grades = {g["label"]: g for g in detail["grades"]}
    assert grades["1"]["awarded_marks"] == 10.0  # clamped to max
    assert grades["2"]["awarded_marks"] == 0.0    # missing → 0
    assert grades["2"]["needs_review"] is True     # missing → flagged
    assert detail["total_awarded"] == 10.0


def test_unmatched_sheet_then_manual_match(client, signup_payload, db_session, monkeypatch):
    import json as _json
    from app.services import claude_client
    teacher, student, subject, exam_id = _setup_ready_exam(client, signup_payload, db_session, usn="1RV23CS999")
    ttok = teacher["access_token"]
    sid = student["user"]["id"]

    # AI detects a USN that matches nobody → unmatched.
    monkeypatch.setattr(claude_client, "generate_completion_vision", lambda *a, **k: _json.dumps({
        "detected_usn": "9XX99XX999", "answers": [
            {"label": "1", "awarded_marks": 7, "max_marks": 10, "co": "CO1", "confidence": 0.9, "ocr_confidence": 0.9},
            {"label": "2", "awarded_marks": 6, "max_marks": 10, "co": "CO2", "confidence": 0.9, "ocr_confidence": 0.9}]}))
    r = client.post(f"/api/v1/grading/exams/{exam_id}/answer-sheets", headers=_auth(ttok),
                    files={"file": ("a.png", _png_bytes(), "image/png")})
    sheet_id = r.json()["id"]
    detail = client.get(f"/api/v1/grading/answer-sheets/{sheet_id}", headers=_auth(ttok)).json()
    assert detail["student_id"] is None
    assert detail["match_source"] == "unmatched"

    # Can't finalize an unmatched sheet.
    rf = client.post(f"/api/v1/grading/answer-sheets/{sheet_id}/finalize", headers=_auth(ttok))
    assert rf.status_code == 400

    # Manual match to the enrolled student attaches the result.
    rm = client.patch(f"/api/v1/grading/answer-sheets/{sheet_id}/match", headers=_auth(ttok),
                      json={"student_id": sid})
    assert rm.status_code == 200, rm.text
    assert str(rm.json()["student_id"]) == str(sid)
    att = client.get(f"/api/v1/grading/exams/{exam_id}/attainment", headers=_auth(ttok)).json()
    assert att["graded_students"] == 1


def test_cross_teacher_isolation(client, signup_payload, db_session, monkeypatch):
    teacher_a, student, subject, exam_id = _setup_ready_exam(client, signup_payload, db_session)
    teacher_b = _signup(client, signup_payload, "teacher")
    btok = teacher_b["access_token"]
    # Teacher B cannot see or fetch teacher A's exam.
    assert all(e["id"] != exam_id for e in client.get("/api/v1/grading/exams", headers=_auth(btok)).json())
    assert client.get(f"/api/v1/grading/exams/{exam_id}", headers=_auth(btok)).status_code in (403, 404)


def test_batch_upload_creates_multiple_sheets(client, signup_payload, db_session, monkeypatch):
    from app.services import claude_client
    teacher, student, subject, exam_id = _setup_ready_exam(client, signup_payload, db_session)
    ttok = teacher["access_token"]
    monkeypatch.setattr(claude_client, "generate_completion_vision", lambda *a, **k: '{"answers": []}')
    files = [("files", (f"s{i}.png", _png_bytes(), "image/png")) for i in range(3)]
    r = client.post(f"/api/v1/grading/exams/{exam_id}/answer-sheets/batch", headers=_auth(ttok), files=files)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 3
    assert len(client.get(f"/api/v1/grading/exams/{exam_id}/answer-sheets", headers=_auth(ttok)).json()) == 3


def test_cover_marks_auto_assign(client, signup_payload, db_session, monkeypatch):
    """Auto Marks Assigner: scan a cover page, auto-match by USN, record the marks."""
    import json as _json
    from app.services import claude_client
    from app.models.grading import ExamResult

    teacher = _signup(client, signup_payload, "teacher")
    student = _signup(client, signup_payload, "student")
    tid = uuid.UUID(teacher["user"]["id"])
    sid = uuid.UUID(student["user"]["id"])
    subject = _make_subject(db_session, tid)
    _enroll(db_session, subject.id, sid, usn="1RV23CS001")
    ttok = teacher["access_token"]
    exam_id = _two_question_exam(client, ttok, subject.id)  # CO1=10, CO2=10, max 20

    monkeypatch.setattr(claude_client, "generate_completion_vision", lambda *a, **k: _json.dumps({
        "detected_usn": "1RV23CS001", "detected_name": "Test Student",
        "total_awarded": 15, "total_max": 20,
        "per_question": [
            {"label": "1", "awarded": 9, "max": 10, "co": "CO1"},
            {"label": "2", "awarded": 6, "max": 10, "co": "CO2"},
        ],
        "per_co": [],
    }))

    r = client.post(f"/api/v1/grading/exams/{exam_id}/cover-marks", headers=_auth(ttok),
                    files={"files": ("cover.png", _png_bytes(), "image/png")})
    assert r.status_code == 200, r.text
    row = r.json()[0]
    assert row["saved"] is True
    assert str(row["student_id"]) == str(sid)
    assert row["total_obtained"] == 15.0
    assert row["per_co"]["CO1"]["obtained"] == 9.0
    assert row["per_co"]["CO2"]["pct"] == 60.0

    # The result landed in the grade engine as a finalized MANUAL ExamResult.
    db_session.expire_all()
    er = db_session.scalar(select(ExamResult).where(
        ExamResult.exam_id == uuid.UUID(exam_id), ExamResult.student_id == sid))
    assert er is not None
    assert float(er.total_obtained) == 15.0
    assert er.source.value == "manual"
    assert er.finalized is True


def test_cover_marks_unmatched_returns_unsaved(client, signup_payload, db_session, monkeypatch):
    import json as _json
    from app.services import claude_client

    teacher = _signup(client, signup_payload, "teacher")
    tid = uuid.UUID(teacher["user"]["id"])
    subject = _make_subject(db_session, tid)
    ttok = teacher["access_token"]
    exam_id = _two_question_exam(client, ttok, subject.id)

    monkeypatch.setattr(claude_client, "generate_completion_vision", lambda *a, **k: _json.dumps({
        "detected_usn": "9NOBODY", "detected_name": "Nobody Here",
        "total_awarded": 10,
        "per_question": [{"label": "1", "awarded": 10, "max": 10, "co": "CO1"}],
    }))
    r = client.post(f"/api/v1/grading/exams/{exam_id}/cover-marks", headers=_auth(ttok),
                    files={"files": ("cover.png", _png_bytes(), "image/png")})
    assert r.status_code == 200, r.text
    row = r.json()[0]
    assert row["saved"] is False
    assert row["student_id"] is None
    assert row["message"]
    # Teacher can then assign it manually via the bulk-results endpoint.
    assert row["total_obtained"] == 10.0
