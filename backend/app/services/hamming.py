"""Hamming distance similarity checker (Phase 19, F23).

DMS Unit IV — Hamming distance over binary vectors. Used to flag suspiciously
similar quiz submissions: each `QuizAttempt` carries an `answer_bit_vector`
(a string of 1s and 0s, 1 = correct) that we wrote during Phase 11.

Algorithm: O(N² · L) brute-force pairwise comparison of N attempts each
with L answers. With ≤ 50 students per quiz and ≤ 20 questions, that's
50 000 ops — trivial.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.algorithm import QuizSimilarityFlag
from app.models.quiz import Quiz, QuizAttempt
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


@dataclass
class HammingPairResult:
    student_a_id: uuid.UUID
    student_a_name: str
    student_b_id: uuid.UUID
    student_b_name: str
    quiz_id: uuid.UUID
    quiz_title: str
    hamming_distance: int
    similarity_percent: float
    answer_length: int


def _hamming(a: str, b: str) -> int:
    """Return the number of positions at which a and b differ.

    If the strings are different lengths, the shorter is right-padded with
    '0' so the longer string's tail counts as a difference.
    """
    if len(a) < len(b):
        a = a.ljust(len(b), "0")
    elif len(b) < len(a):
        b = b.ljust(len(a), "0")
    return sum(1 for x, y in zip(a, b) if x != y)


def analyze_quiz(
    db: Session,
    user: User,
    *,
    quiz_id: uuid.UUID,
    max_distance: int = 2,
) -> tuple[list[HammingPairResult], int, float]:
    """Run pairwise Hamming distance over every attempt of `quiz_id`.

    Returns (flagged_pairs, total_attempts, mean_pairwise_similarity).
    Pairs whose Hamming distance is ≤ `max_distance` are flagged.

    Teachers see only their own quizzes; admins see anything.
    """
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can run the similarity checker.",
        )

    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Quiz not found")
    if user.role == UserRole.TEACHER and quiz.created_by_id != user.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="You don't own this quiz")

    rows = db.execute(
        select(QuizAttempt, User)
        .join(User, QuizAttempt.student_id == User.id)
        .where(QuizAttempt.quiz_id == quiz.id)
        .order_by(QuizAttempt.completed_at)
    ).all()

    if len(rows) < 2:
        return [], len(rows), 0.0

    # Use the latest attempt per student so we don't double-count retakes
    latest_per_student: dict[uuid.UUID, tuple[QuizAttempt, User]] = {}
    for attempt, student in rows:
        latest_per_student[student.id] = (attempt, student)

    pairs_iter = list(latest_per_student.values())
    flagged: list[HammingPairResult] = []
    total_similarity = 0.0
    pair_count = 0

    for i in range(len(pairs_iter)):
        attempt_a, student_a = pairs_iter[i]
        vec_a = attempt_a.answer_bit_vector or ""
        for j in range(i + 1, len(pairs_iter)):
            attempt_b, student_b = pairs_iter[j]
            vec_b = attempt_b.answer_bit_vector or ""
            if not vec_a or not vec_b:
                continue
            distance = _hamming(vec_a, vec_b)
            length = max(len(vec_a), len(vec_b))
            sim = ((length - distance) / length) * 100 if length else 0.0
            total_similarity += sim
            pair_count += 1
            if distance <= max_distance:
                flagged.append(
                    HammingPairResult(
                        student_a_id=student_a.id,
                        student_a_name=student_a.full_name,
                        student_b_id=student_b.id,
                        student_b_name=student_b.full_name,
                        quiz_id=quiz.id,
                        quiz_title=quiz.title,
                        hamming_distance=distance,
                        similarity_percent=round(sim, 2),
                        answer_length=length,
                    )
                )

    flagged.sort(key=lambda p: p.hamming_distance)
    mean_similarity = round(total_similarity / pair_count, 2) if pair_count else 0.0
    return flagged, len(latest_per_student), mean_similarity


def persist_flags(db: Session, results: list[HammingPairResult]) -> int:
    """Idempotent — only creates a flag if no row exists for the (quiz, A, B)
    triple. Returns the number of NEW rows inserted."""
    inserted = 0
    for r in results:
        existing = db.scalar(
            select(QuizSimilarityFlag.id)
            .where(QuizSimilarityFlag.quiz_id == r.quiz_id)
            .where(QuizSimilarityFlag.student_a_id == r.student_a_id)
            .where(QuizSimilarityFlag.student_b_id == r.student_b_id)
        )
        if existing:
            continue
        from decimal import Decimal

        db.add(
            QuizSimilarityFlag(
                quiz_id=r.quiz_id,
                student_a_id=r.student_a_id,
                student_b_id=r.student_b_id,
                hamming_distance=r.hamming_distance,
                similarity_percentage=Decimal(f"{r.similarity_percent:.2f}"),
            )
        )
        inserted += 1
    if inserted:
        db.commit()
    return inserted
