"""Match an uploaded answer sheet to a roster student by USN, then by name.

Pure-ish: small Levenshtein (no new dependency), reads the roster. Returns a
``(student_id | None, confidence, source)`` tuple; the teacher always confirms.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import StudentProfile, SubjectEnrollment, User


def _norm(s: str | None) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def roster_candidates(db: Session, subject_id: uuid.UUID) -> list[tuple[User, StudentProfile | None]]:
    rows = db.execute(
        select(User, StudentProfile)
        .join(SubjectEnrollment, SubjectEnrollment.student_id == User.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(SubjectEnrollment.subject_id == subject_id)
    ).all()
    return [(u, sp) for u, sp in rows]


def match_student(
    db: Session,
    subject_id: uuid.UUID,
    detected_usn: str | None,
    detected_name: str | None,
) -> tuple[uuid.UUID | None, float, str]:
    """Best-effort match against the subject roster. Priority: exact USN → fuzzy
    USN → fuzzy name → unmatched."""
    candidates = roster_candidates(db, subject_id)

    usn_n = _norm(detected_usn)
    if usn_n:
        for u, sp in candidates:
            if sp and sp.usn and _norm(sp.usn) == usn_n:
                return u.id, 0.98, "usn"
        best: tuple[uuid.UUID, int] | None = None
        for u, sp in candidates:
            if sp and sp.usn:
                d = _levenshtein(usn_n, _norm(sp.usn))
                if d <= 1 and (best is None or d < best[1]):
                    best = (u.id, d)
        if best is not None:
            return best[0], 0.80, "usn"

    name_n = _norm(detected_name)
    if name_n:
        best_name: tuple[uuid.UUID, float] | None = None
        for u, sp in candidates:
            cand = _norm(u.full_name)
            if not cand:
                continue
            d = _levenshtein(name_n, cand)
            ratio = 1 - d / max(len(name_n), len(cand))
            if ratio >= 0.70 and (best_name is None or ratio > best_name[1]):
                best_name = (u.id, ratio)
        if best_name is not None:
            return best_name[0], round(0.5 + best_name[1] * 0.3, 3), "name"

    return None, 0.0, "unmatched"
