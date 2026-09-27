"""Teacher-facing routes for the AI auto-grader + grading config.

All routes require teacher/admin. Claude-triggering routes (scheme parse, grade,
regrade) carry claude_rate_limit. Answer-sheet page images are served only here,
behind an ownership check (never a public static mount).
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import DbSession, claude_rate_limit, require_role
from app.models.user import User
from app.schemas.grading import (
    AnswerSheetDetail,
    AnswerSheetSummary,
    BulkManualResults,  # noqa: F401  (used by the manual-results route below)
    CourseOutcomeCreate,
    CoverScanResult,
    CourseOutcomeResponse,
    ExamAttainmentResponse,
    ExamCreate,
    ExamQuestionCreate,
    ExamQuestionResponse,
    ExamQuestionUpdate,
    ExamResponse,
    ExamUpdate,
    GradeConfigResponse,
    GradeConfigUpdate,
    MatchUpdate,
    QuestionGradeOverride,
    QuestionGradeResponse,
    ReviewQueueItem,
    SchemeResponse,
)
from app.services import answersheet_grader, answersheet_ingest, document, scheme_parser
from app.services import grading as svc

router = APIRouter()

TeacherUser = Annotated[User, Depends(require_role("teacher", "admin"))]
RateLimited = [Depends(claude_rate_limit)]


# ── exams ────────────────────────────────────────────────────────────────────
@router.post("/exams", response_model=ExamResponse)
def create_exam(data: ExamCreate, db: DbSession, user: TeacherUser):
    return svc.create_exam(db, user, data)


@router.get("/exams", response_model=list[ExamResponse])
def list_exams(db: DbSession, user: TeacherUser, subject_id: uuid.UUID | None = None):
    return svc.list_exams(db, user, subject_id)


@router.get("/exams/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.to_exam_response(db, svc._owned_exam(db, user, exam_id))


@router.patch("/exams/{exam_id}", response_model=ExamResponse)
def update_exam(exam_id: uuid.UUID, data: ExamUpdate, db: DbSession, user: TeacherUser):
    return svc.update_exam(db, user, exam_id, data)


@router.delete("/exams/{exam_id}", status_code=204)
def delete_exam(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    svc.delete_exam(db, user, exam_id)


# ── scheme ───────────────────────────────────────────────────────────────────
@router.post("/exams/{exam_id}/scheme", response_model=ExamResponse, dependencies=RateLimited)
def upload_scheme(
    exam_id: uuid.UUID, db: DbSession, user: TeacherUser, background: BackgroundTasks,
    file: UploadFile = File(...),
):
    exam = svc._owned_exam(db, user, exam_id)
    doc = document.upload_document(db, exam.subject_id, file, user, title=f"Scheme — {exam.title}")
    svc.set_scheme_document(db, user, exam_id, doc.id)
    background.add_task(scheme_parser.process_scheme, exam_id)
    db.refresh(exam)
    return svc.to_exam_response(db, exam)


@router.get("/exams/{exam_id}/scheme", response_model=SchemeResponse)
def get_scheme(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.get_scheme(db, user, exam_id)


@router.post("/exams/{exam_id}/scheme/confirm", response_model=ExamResponse)
def confirm_scheme(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.confirm_scheme(db, user, exam_id)


@router.post("/exams/{exam_id}/questions", response_model=ExamQuestionResponse)
def add_question(exam_id: uuid.UUID, data: ExamQuestionCreate, db: DbSession, user: TeacherUser):
    return svc.create_question(db, user, exam_id, data)


@router.patch("/exams/{exam_id}/questions/{question_id}", response_model=ExamQuestionResponse)
def edit_question(exam_id: uuid.UUID, question_id: uuid.UUID, data: ExamQuestionUpdate, db: DbSession, user: TeacherUser):
    return svc.update_question(db, user, exam_id, question_id, data)


@router.delete("/exams/{exam_id}/questions/{question_id}", status_code=204)
def remove_question(exam_id: uuid.UUID, question_id: uuid.UUID, db: DbSession, user: TeacherUser):
    svc.delete_question(db, user, exam_id, question_id)


# ── config + course outcomes ─────────────────────────────────────────────────
@router.get("/subjects/{subject_id}/config", response_model=GradeConfigResponse)
def get_config(subject_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.get_config(db, user, subject_id)


@router.put("/subjects/{subject_id}/config", response_model=GradeConfigResponse)
def update_config(subject_id: uuid.UUID, data: GradeConfigUpdate, db: DbSession, user: TeacherUser):
    return svc.update_config(db, user, subject_id, data)


@router.get("/subjects/{subject_id}/course-outcomes", response_model=list[CourseOutcomeResponse])
def list_cos(subject_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.list_course_outcomes(db, user, subject_id)


@router.post("/subjects/{subject_id}/course-outcomes", response_model=CourseOutcomeResponse)
def add_co(subject_id: uuid.UUID, data: CourseOutcomeCreate, db: DbSession, user: TeacherUser):
    return svc.create_course_outcome(db, user, subject_id, data)


# ── answer sheets ────────────────────────────────────────────────────────────
@router.post("/exams/{exam_id}/answer-sheets/batch", response_model=list[AnswerSheetSummary], dependencies=RateLimited)
def upload_batch(
    exam_id: uuid.UUID, db: DbSession, user: TeacherUser, background: BackgroundTasks,
    files: list[UploadFile] = File(...), pages_per_student: int | None = Form(None),
):
    exam = svc._owned_exam(db, user, exam_id)
    sheets = answersheet_ingest.ingest_batch(db, exam.id, files, pages_per_student=pages_per_student)
    for s in sheets:
        background.add_task(answersheet_grader.grade_answer_sheet, s.id)
    return [svc._sheet_summary(db, s) for s in sheets]


@router.post("/exams/{exam_id}/answer-sheets", response_model=AnswerSheetSummary, dependencies=RateLimited)
def upload_single(
    exam_id: uuid.UUID, db: DbSession, user: TeacherUser, background: BackgroundTasks,
    file: UploadFile = File(...), student_id: uuid.UUID | None = Form(None),
):
    exam = svc._owned_exam(db, user, exam_id)
    sheet = answersheet_ingest.ingest_single(db, exam.id, file, student_id=student_id)
    background.add_task(answersheet_grader.grade_answer_sheet, sheet.id)
    return svc._sheet_summary(db, sheet)


@router.get("/exams/{exam_id}/answer-sheets", response_model=list[AnswerSheetSummary])
def list_sheets(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.list_sheets(db, user, exam_id)


@router.get("/answer-sheets/{sheet_id}", response_model=AnswerSheetDetail)
def get_sheet(sheet_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.get_sheet_detail(db, user, sheet_id)


@router.get("/answer-sheets/{sheet_id}/pages/{idx}")
def get_sheet_page(sheet_id: uuid.UUID, idx: int, db: DbSession, user: TeacherUser):
    sheet, _ = svc._owned_sheet(db, user, sheet_id)
    files = sheet.page_files or []
    if idx < 0 or idx >= len(files) or not sheet.storage_dir:
        raise HTTPException(status_code=404, detail="Page not found")
    path = Path(sheet.storage_dir) / files[idx]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Page file missing")
    return FileResponse(str(path), media_type="image/png")


@router.patch("/answer-sheets/{sheet_id}/match", response_model=AnswerSheetSummary)
def set_match(sheet_id: uuid.UUID, data: MatchUpdate, db: DbSession, user: TeacherUser):
    return svc.set_match(db, user, sheet_id, data.student_id)


@router.post("/answer-sheets/{sheet_id}/regrade", dependencies=RateLimited)
def regrade(sheet_id: uuid.UUID, db: DbSession, user: TeacherUser, background: BackgroundTasks, force: bool = False):
    svc._owned_sheet(db, user, sheet_id)
    background.add_task(answersheet_grader.grade_answer_sheet, sheet_id, force=force)
    return {"status": "scheduled"}


@router.post("/answer-sheets/{sheet_id}/finalize", response_model=AnswerSheetSummary)
def finalize_sheet(sheet_id: uuid.UUID, db: DbSession, user: TeacherUser, force: bool = False):
    return svc.finalize_sheet(db, user, sheet_id, force=force)


@router.post("/exams/{exam_id}/finalize-all")
def finalize_all(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return {"finalized": svc.finalize_all(db, user, exam_id)}


# ── review + override ────────────────────────────────────────────────────────
@router.get("/exams/{exam_id}/review-queue", response_model=list[ReviewQueueItem])
def review_queue(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.review_queue(db, user, exam_id)


@router.patch("/question-grades/{grade_id}", response_model=QuestionGradeResponse)
def override_grade(grade_id: uuid.UUID, data: QuestionGradeOverride, db: DbSession, user: TeacherUser):
    return svc.override_grade(db, user, grade_id, data)


# ── manual mark entry (experiential / lab / SEE) ──────────────────────────────
@router.post("/exams/{exam_id}/results/bulk")
def enter_results(exam_id: uuid.UUID, data: BulkManualResults, db: DbSession, user: TeacherUser):
    return {"entered": svc.enter_manual_results(db, user, exam_id, data.results)}


# ── Auto Marks Assigner: scan booklet cover pages → record CO marks ───────────
@router.post(
    "/exams/{exam_id}/cover-marks",
    response_model=list[CoverScanResult],
    dependencies=RateLimited,
)
def scan_cover_marks(
    exam_id: uuid.UUID,
    db: DbSession,
    user: TeacherUser,
    files: list[UploadFile] = File(...),
):
    return svc.scan_and_record_cover(db, user, exam_id, files)


# ── attainment ───────────────────────────────────────────────────────────────
@router.get("/exams/{exam_id}/attainment", response_model=ExamAttainmentResponse)
def attainment(exam_id: uuid.UUID, db: DbSession, user: TeacherUser):
    return svc.exam_attainment(db, user, exam_id)
