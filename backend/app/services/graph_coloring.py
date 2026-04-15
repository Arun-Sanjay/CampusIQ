"""Greedy graph coloring for quiz scheduling (Phase 19, F21).

DMS Unit V — graph coloring / chromatic number. Two quizzes that share at
least one student conflict and need different time slots. We model this as
a graph (nodes = quizzes, edges = "share a student") and run the standard
greedy coloring algorithm with the largest-degree-first heuristic.

The chromatic number gives the minimum number of distinct time slots needed
to schedule every quiz without anyone facing two at once.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quiz import Quiz, QuizAttempt
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


@dataclass
class QuizSlotAssignment:
    quiz_id: uuid.UUID
    quiz_title: str
    subject_code: str | None
    color: int                          # 0-indexed slot number
    conflict_quiz_titles: list[str]     # quizzes that share students with this one


@dataclass
class GraphColoringResult:
    assignments: list[QuizSlotAssignment]
    chromatic_number: int          # max color used + 1
    quiz_count: int
    edge_count: int                # number of conflict pairs
    color_groups: dict[int, list[str]]  # color → list of quiz titles


def _build_conflict_graph(
    db: Session, user: User
) -> tuple[dict[uuid.UUID, set[uuid.UUID]], dict[uuid.UUID, Quiz]]:
    """Return (adjacency dict, quizzes_by_id).

    Two quizzes conflict iff at least one student has attempted both.
    Teachers see only their own quizzes; admins see everything.
    """
    stmt = select(Quiz)
    if user.role == UserRole.TEACHER:
        stmt = stmt.where(Quiz.created_by_id == user.id)
    quizzes = list(db.scalars(stmt).all())
    if not quizzes:
        return {}, {}

    quiz_ids = {q.id for q in quizzes}
    quizzes_by_id = {q.id: q for q in quizzes}

    # Map student → set of quizzes they've attempted (within scope)
    attempts = db.execute(
        select(QuizAttempt.student_id, QuizAttempt.quiz_id).where(
            QuizAttempt.quiz_id.in_(quiz_ids)
        )
    ).all()
    student_to_quizzes: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for sid, qid in attempts:
        student_to_quizzes[sid].add(qid)

    # Build adjacency: any two quizzes that co-occur in a student's set are
    # connected by an edge.
    adjacency: dict[uuid.UUID, set[uuid.UUID]] = {qid: set() for qid in quiz_ids}
    for quizzes_for_student in student_to_quizzes.values():
        if len(quizzes_for_student) < 2:
            continue
        quizzes_list = list(quizzes_for_student)
        for i in range(len(quizzes_list)):
            for j in range(i + 1, len(quizzes_list)):
                a, b = quizzes_list[i], quizzes_list[j]
                adjacency[a].add(b)
                adjacency[b].add(a)
    return adjacency, quizzes_by_id


def color_quizzes(db: Session, user: User) -> GraphColoringResult:
    """Greedy coloring with the largest-degree-first heuristic.

    Sorting by degree descending tends to produce a coloring closer to the
    optimum (DSatur is even better but greedy is enough for ≤ 100 quizzes).
    """
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can run quiz scheduling.",
        )

    adjacency, quizzes_by_id = _build_conflict_graph(db, user)
    if not quizzes_by_id:
        return GraphColoringResult(
            assignments=[],
            chromatic_number=0,
            quiz_count=0,
            edge_count=0,
            color_groups={},
        )

    # Largest degree first
    nodes_in_order = sorted(
        adjacency.keys(),
        key=lambda q: -len(adjacency.get(q, set())),
    )

    color_of: dict[uuid.UUID, int] = {}
    for node in nodes_in_order:
        used_by_neighbours = {
            color_of[n] for n in adjacency.get(node, set()) if n in color_of
        }
        # Pick the smallest color not used by any neighbour
        c = 0
        while c in used_by_neighbours:
            c += 1
        color_of[node] = c

    chromatic = max(color_of.values()) + 1 if color_of else 0
    edge_count = sum(len(s) for s in adjacency.values()) // 2

    assignments: list[QuizSlotAssignment] = []
    color_groups: dict[int, list[str]] = defaultdict(list)
    for qid, color in color_of.items():
        quiz = quizzes_by_id[qid]
        # Resolve subject code (if any) from the relationship
        subject_code = None
        if quiz.subject_id:
            from app.models.user import Subject

            subject = db.get(Subject, quiz.subject_id)
            if subject:
                subject_code = subject.code
        conflict_titles = [
            quizzes_by_id[n].title for n in adjacency.get(qid, set()) if n in quizzes_by_id
        ]
        assignments.append(
            QuizSlotAssignment(
                quiz_id=qid,
                quiz_title=quiz.title,
                subject_code=subject_code,
                color=color,
                conflict_quiz_titles=sorted(conflict_titles),
            )
        )
        color_groups[color].append(quiz.title)

    assignments.sort(key=lambda a: (a.color, a.quiz_title))
    return GraphColoringResult(
        assignments=assignments,
        chromatic_number=chromatic,
        quiz_count=len(quizzes_by_id),
        edge_count=edge_count,
        color_groups={k: sorted(v) for k, v in color_groups.items()},
    )
