"""Job Tracker service (Phase 17, F12).

Students browse job listings, save them, and track their application status
through a simple state machine (saved → applied → oa_received →
interview_scheduled → offer_received/rejected). The fit score is computed
from the overlap between the student's mastery vector (from the Phase 15
skill graph) and keywords parsed out of the job's requirements text.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.placement import (
    ApplicationStatus,
    JobApplication,
    JobListing,
    JobListingSource,
    JobType,
)
from app.models.user import User, UserRole
from app.schemas.jobs import (
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
    JobBoardResponse,
    JobListingCreate,
    JobListingResponse,
)
from app.services import skill_graph

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Fit score computation
# ════════════════════════════════════════════════════════════════

# Pre-compile the token splitter — lowercase, strip punctuation, 2+ chars
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.]{1,}")


def _extract_keywords(text: str | None) -> set[str]:
    if not text:
        return set()
    return {m.group(0).lower() for m in _WORD_RE.finditer(text)}


def _compute_fit_score(
    student_mastery: dict[str, float],
    skill_nodes: list[str],
    job: JobListing,
) -> float:
    """Return a 0-100 fit score.

    Approach:
    1. Extract keyword tokens from the job's `requirements` + `description`.
    2. For every skill node in the graph whose name (case-insensitive) appears
       as a token in the job text, include it as a "required" skill.
    3. Average the student's mastery across those required skills × 100.
    4. Fallback: if we can't extract any required skills, return 50 as neutral.
    """
    tokens = _extract_keywords((job.requirements or "") + " " + (job.description or ""))
    if not tokens:
        return 50.0

    required: list[str] = []
    for skill in skill_nodes:
        # Each skill node might be multi-word ("Dynamic Programming"). We check
        # all its tokens against the job tokens and require a majority match.
        skill_tokens = [t.lower() for t in _WORD_RE.findall(skill) if len(t) >= 2]
        if not skill_tokens:
            continue
        matches = sum(1 for t in skill_tokens if t in tokens)
        if matches >= max(1, len(skill_tokens) // 2 + 1):
            required.append(skill)
        # Single-token skills need a direct hit
        elif len(skill_tokens) == 1 and skill_tokens[0] in tokens:
            required.append(skill)

    if not required:
        return 50.0

    total_mastery = sum(student_mastery.get(s, 0.0) for s in required)
    avg = (total_mastery / len(required)) * 100.0
    return round(max(0.0, min(100.0, avg)), 2)


@dataclass
class FitContext:
    """Cached mastery + skill node list so we don't recompute per job."""

    mastery: dict[str, float]
    skill_nodes: list[str]


def _build_fit_context(db: Session, user: User) -> FitContext:
    """Load the student's mastery snapshot once for batch scoring."""
    try:
        _graph, nodes = skill_graph._load_base_graph(db)
    except Exception:
        return FitContext(mastery={}, skill_nodes=[])
    names = [n.name for n in nodes]
    snap = skill_graph.compute_mastery(db, user, graph_nodes=names)
    return FitContext(mastery=snap.per_skill, skill_nodes=names)


def _to_listing_response(job: JobListing, fit_score: float | None) -> JobListingResponse:
    return JobListingResponse(
        id=job.id,
        title=job.title,
        company_name=job.company_name,
        description=job.description,
        requirements=job.requirements,
        location=job.location,
        job_type=job.job_type.value,  # type: ignore[arg-type]
        application_deadline=job.application_deadline,
        source=job.source.value,  # type: ignore[arg-type]
        created_at=job.created_at,
        fit_score=fit_score,
    )


def _to_application_response(
    app: JobApplication, job: JobListing, fit_score: float | None
) -> JobApplicationResponse:
    return JobApplicationResponse(
        id=app.id,
        student_id=app.student_id,
        job_listing_id=app.job_listing_id,
        status=app.status.value,  # type: ignore[arg-type]
        fit_score=float(app.fit_score) if app.fit_score is not None else fit_score,
        notes=app.notes,
        created_at=app.created_at,
        updated_at=app.updated_at,
        job=_to_listing_response(job, fit_score),
    )


# ════════════════════════════════════════════════════════════════
# Listings
# ════════════════════════════════════════════════════════════════

def _require_student(user: User) -> None:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Job Tracker is only available to students.",
        )


def list_listings(
    db: Session, user: User, *, search: str | None = None, limit: int = 100
) -> list[JobListingResponse]:
    stmt = select(JobListing).order_by(JobListing.created_at.desc())
    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import func as sqlfunc, or_
        stmt = stmt.where(
            or_(
                sqlfunc.lower(JobListing.title).like(like),
                sqlfunc.lower(JobListing.company_name).like(like),
            )
        )
    stmt = stmt.limit(limit)
    jobs = list(db.scalars(stmt).all())

    ctx = _build_fit_context(db, user) if user.role == UserRole.STUDENT else FitContext({}, [])
    return [
        _to_listing_response(
            j,
            _compute_fit_score(ctx.mastery, ctx.skill_nodes, j)
            if user.role == UserRole.STUDENT
            else None,
        )
        for j in jobs
    ]


def create_listing(
    db: Session, user: User, data: JobListingCreate
) -> JobListingResponse:
    source = (
        JobListingSource.STUDENT_ADDED
        if user.role == UserRole.STUDENT
        else JobListingSource.ADMIN_ADDED
    )
    job = JobListing(
        added_by_id=user.id,
        title=data.title.strip(),
        company_name=data.company_name.strip(),
        description=data.description,
        requirements=data.requirements,
        location=data.location,
        job_type=JobType(data.job_type),
        application_deadline=data.application_deadline,
        source=source,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    fit = None
    if user.role == UserRole.STUDENT:
        ctx = _build_fit_context(db, user)
        fit = _compute_fit_score(ctx.mastery, ctx.skill_nodes, job)
    return _to_listing_response(job, fit)


def delete_listing(db: Session, user: User, listing_id: uuid.UUID) -> None:
    job = db.get(JobListing, listing_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job listing not found")
    if user.role == UserRole.STUDENT and job.added_by_id != user.id:
        raise HTTPException(
            status_code=403, detail="You can only delete listings you added"
        )
    db.delete(job)
    db.commit()


# ════════════════════════════════════════════════════════════════
# Applications
# ════════════════════════════════════════════════════════════════

def save_or_update_application(
    db: Session, user: User, data: JobApplicationCreate
) -> JobApplicationResponse:
    """Create an application for a student. If one already exists for this
    student + listing, return/update that instead of duplicating."""
    _require_student(user)
    job = db.get(JobListing, data.job_listing_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job listing not found")

    existing = db.scalar(
        select(JobApplication)
        .where(JobApplication.student_id == user.id)
        .where(JobApplication.job_listing_id == job.id)
    )
    ctx = _build_fit_context(db, user)
    fit = _compute_fit_score(ctx.mastery, ctx.skill_nodes, job)
    if existing is not None:
        existing.status = ApplicationStatus(data.status)
        if data.notes is not None:
            existing.notes = data.notes
        existing.fit_score = Decimal(f"{fit:.2f}")
        db.commit()
        db.refresh(existing)
        return _to_application_response(existing, job, fit)

    app = JobApplication(
        student_id=user.id,
        job_listing_id=job.id,
        status=ApplicationStatus(data.status),
        notes=data.notes,
        fit_score=Decimal(f"{fit:.2f}"),
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _to_application_response(app, job, fit)


def update_application(
    db: Session,
    user: User,
    application_id: uuid.UUID,
    data: JobApplicationUpdate,
) -> JobApplicationResponse:
    _require_student(user)
    app = db.get(JobApplication, application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.student_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this application")

    if data.status is not None:
        app.status = ApplicationStatus(data.status)
    if data.notes is not None:
        app.notes = data.notes

    db.commit()
    db.refresh(app)

    job = db.get(JobListing, app.job_listing_id)
    if job is None:
        raise HTTPException(status_code=500, detail="Application's job listing disappeared")
    return _to_application_response(app, job, float(app.fit_score) if app.fit_score else None)


def delete_application(
    db: Session, user: User, application_id: uuid.UUID
) -> None:
    _require_student(user)
    app = db.get(JobApplication, application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.student_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this application")
    db.delete(app)
    db.commit()


def list_my_board(db: Session, user: User) -> JobBoardResponse:
    """Return the student's Kanban view — every application bucketed by status."""
    _require_student(user)
    rows = db.execute(
        select(JobApplication, JobListing)
        .join(JobListing, JobApplication.job_listing_id == JobListing.id)
        .where(JobApplication.student_id == user.id)
        .order_by(JobApplication.updated_at.desc())
    ).all()

    board: dict[str, list[JobApplicationResponse]] = {
        "saved": [],
        "applied": [],
        "oa_received": [],
        "interview_scheduled": [],
        "offer_received": [],
        "rejected": [],
    }
    for app, job in rows:
        resp = _to_application_response(
            app, job, float(app.fit_score) if app.fit_score is not None else None
        )
        board[app.status.value].append(resp)

    return JobBoardResponse(
        saved=board["saved"],
        applied=board["applied"],
        oa_received=board["oa_received"],
        interview_scheduled=board["interview_scheduled"],
        offer_received=board["offer_received"],
        rejected=board["rejected"],
    )


# ════════════════════════════════════════════════════════════════
# Seed data (to make the board interesting out of the box)
# ════════════════════════════════════════════════════════════════

def seed_sample_listings_if_empty(db: Session, user: User) -> int:
    """Drop a handful of realistic job listings on first load. Idempotent."""
    existing = db.scalar(select(JobListing).limit(1))
    if existing is not None:
        return 0

    samples = [
        JobListingCreate(
            title="SWE Intern",
            company_name="Google",
            description=(
                "Work on production systems at Google scale. Ideal for 3rd/4th year "
                "students with strong CS fundamentals and a portfolio of side projects."
            ),
            requirements=(
                "Arrays, Trees, Graphs, Dynamic Programming, System Design Basics, "
                "Problem Solving, Git. Bonus: C++, Python, Distributed Systems."
            ),
            location="Bangalore",
            job_type="internship",
        ),
        JobListingCreate(
            title="SDE-1",
            company_name="Amazon",
            description=(
                "Join the AWS team building highly scalable infra. Strong ownership "
                "culture. New grad friendly."
            ),
            requirements=(
                "Arrays, Trees, Graphs, Dynamic Programming, System Design Basics, "
                "AWS Basics, Java, SQL, Git. Bonus: AWS Advanced, Microservices."
            ),
            location="Hyderabad",
            job_type="full_time",
        ),
        JobListingCreate(
            title="Full-Stack Intern",
            company_name="Flipkart",
            description=(
                "Ship customer-facing features on the consumer app. Pair programming "
                "with senior engineers."
            ),
            requirements=(
                "HTML/CSS, JavaScript, TypeScript, React, Node.js, REST APIs, SQL, Git. "
                "Bonus: Next.js, Redis."
            ),
            location="Bangalore",
            job_type="internship",
        ),
        JobListingCreate(
            title="Backend Engineer",
            company_name="Swiggy",
            description=(
                "Own the order-dispatch service. Low-latency Java services, high QPS."
            ),
            requirements=(
                "Arrays, Trees, Java, SQL, PostgreSQL, Redis, REST APIs, "
                "System Design Basics, Git."
            ),
            location="Bangalore",
            job_type="full_time",
        ),
        JobListingCreate(
            title="Power Programmer",
            company_name="Infosys",
            description=(
                "Fast-track program for top performers. Client-facing delivery roles."
            ),
            requirements="Java, SQL, Git, Problem Solving, OOP.",
            location="Mysore",
            job_type="full_time",
        ),
        JobListingCreate(
            title="SWE Intern — Systems",
            company_name="Microsoft",
            description=(
                "Internship on Azure core services. Strong C++ / systems background preferred."
            ),
            requirements=(
                "Arrays, Trees, Graphs, Dynamic Programming, C++, OS Concepts, "
                "System Design Basics, Git."
            ),
            location="Noida",
            job_type="internship",
        ),
    ]

    for s in samples:
        job = JobListing(
            added_by_id=user.id,
            title=s.title,
            company_name=s.company_name,
            description=s.description,
            requirements=s.requirements,
            location=s.location,
            job_type=JobType(s.job_type),
            source=JobListingSource.ADMIN_ADDED,
        )
        db.add(job)
    db.commit()
    return len(samples)
