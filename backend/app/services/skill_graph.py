"""Adaptive Learning Engine service (Phase 15, F7/F17/F18/F22).

This is the research-paper core. Given a student and a target company:

1. **Mastery map** — compute the student's current mastery level for every
   skill in the graph, from quiz attempts + declared profile skills.
2. **Dynamic edge weights** — rescale every edge in the base graph using
   the student's mastery of the prerequisite (source) skill:
       adjusted = base × (1 - α × mastery(u)) × (1 + β × gap(v))
   where α = confidence factor (cheaper if they already know the basics)
   and β = urgency factor (costlier if they're especially weak on the target).
3. **Skill gap** — set difference + cosine-style similarity between the
   student's mastery vector and the target company's requirement vector.
4. **Dijkstra** — shortest path from a synthetic START node (0-cost into the
   student's known skills) to each required skill of the target company.
5. **Knapsack** — given an available-hours budget, pick the subset of missing
   skills on the path(s) that maximises total fit-score gain.
6. **Prim's MST** — over the prerequisite subgraph induced by the target
   skills + their prerequisites, used to render a clean dependency tree.
7. **Research logging** — every plan is persisted to `study_optimizer_results`
   with predicted improvement and (eventually) actual improvement for the
   paper's evaluation.
"""
from __future__ import annotations

import logging
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.algorithm import (
    CompanySkillRequirement,
    SkillGraphEdge,
    SkillNode,
    StudyOptimizerResult,
)
from app.models.quiz import Quiz, QuizAttempt
from app.models.user import User, UserRole
from app.services import dijkstra as dijkstra_mod
from app.services import knapsack as knapsack_mod
from app.services import mst as mst_mod
from app.services.skill_graph_seed import (
    SEED_COMPANIES,
    SEED_EDGES,
    SEED_NODES,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Dynamic weighting tunables (research paper deltas)
# ════════════════════════════════════════════════════════════════

CONFIDENCE_ALPHA = 0.55   # up to 55% discount for strong prerequisites
URGENCY_BETA = 0.40       # up to 40% surcharge for especially weak targets
MIN_EDGE_WEIGHT = 0.5     # floor so edges never go to zero
IMPLICIT_SKILL_MASTERY = 0.75  # students get credit for skills in their declared profile
QUIZ_MASTERY_WEIGHT = 1.0      # full credit for quiz-backed mastery
COMPANY_MATCH_BASE_VALUE = 10  # Knapsack value per required skill gained


# ════════════════════════════════════════════════════════════════
# Seeding
# ════════════════════════════════════════════════════════════════

def is_seeded(db: Session) -> bool:
    return db.scalar(select(SkillNode).limit(1)) is not None


def seed_if_empty(db: Session) -> None:
    """Idempotent seed — called on first use."""
    if is_seeded(db):
        return
    logger.info(
        "Seeding skill graph: %d nodes, %d edges, %d companies",
        len(SEED_NODES),
        len(SEED_EDGES),
        len(SEED_COMPANIES),
    )
    for node in SEED_NODES:
        db.add(
            SkillNode(
                name=node.name,
                domain=node.domain,
                description=node.description,
                difficulty_tier=node.difficulty_tier,
            )
        )
    for edge in SEED_EDGES:
        db.add(
            SkillGraphEdge(
                from_skill=edge.from_skill,
                to_skill=edge.to_skill,
                base_weight_hours=Decimal(str(edge.base_weight_hours)),
                domain=edge.domain,
            )
        )
    for company in SEED_COMPANIES:
        db.add(
            CompanySkillRequirement(
                company_name=company.company,
                role=company.role,
                required_skills=list(company.required_skills),
                preferred_skills=list(company.preferred_skills),
                difficulty_tier=company.difficulty_tier,
            )
        )
    db.commit()


# ════════════════════════════════════════════════════════════════
# Graph loading
# ════════════════════════════════════════════════════════════════

@dataclass
class SkillNodeInfo:
    name: str
    domain: str
    description: str
    difficulty_tier: int


@dataclass
class CompanyInfo:
    id: uuid.UUID
    company: str
    role: str
    required_skills: list[str]
    preferred_skills: list[str]
    difficulty_tier: int


def _load_base_graph(db: Session) -> tuple[dict[str, dict[str, float]], list[SkillNodeInfo]]:
    """Load the base directed graph from the DB. Returns (adjacency, nodes)."""
    seed_if_empty(db)
    rows = db.scalars(select(SkillGraphEdge)).all()
    nodes_rows = db.scalars(select(SkillNode)).all()

    graph: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        graph[row.from_skill][row.to_skill] = float(row.base_weight_hours)
        # Ensure destination nodes exist as keys
        if row.to_skill not in graph:
            graph[row.to_skill] = {}

    # Also make sure every node appears as a key (even isolated ones)
    for n in nodes_rows:
        graph.setdefault(n.name, {})

    nodes = [
        SkillNodeInfo(
            name=n.name,
            domain=n.domain or "misc",
            description=n.description or "",
            difficulty_tier=n.difficulty_tier,
        )
        for n in nodes_rows
    ]
    return dict(graph), nodes


def list_nodes(db: Session) -> list[SkillNodeInfo]:
    _, nodes = _load_base_graph(db)
    return sorted(nodes, key=lambda n: (n.domain, n.name))


def list_companies(db: Session) -> list[CompanyInfo]:
    seed_if_empty(db)
    rows = db.scalars(select(CompanySkillRequirement).order_by(CompanySkillRequirement.company_name)).all()
    return [
        CompanyInfo(
            id=r.id,
            company=r.company_name,
            role=r.role,
            required_skills=list(r.required_skills or []),
            preferred_skills=list(r.preferred_skills or []),
            difficulty_tier=r.difficulty_tier,
        )
        for r in rows
    ]


def get_company(
    db: Session, *, company_name: str, role: str | None = None
) -> CompanyInfo:
    seed_if_empty(db)
    stmt = select(CompanySkillRequirement).where(
        CompanySkillRequirement.company_name == company_name
    )
    if role:
        stmt = stmt.where(CompanySkillRequirement.role == role)
    row = db.scalar(stmt)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company profile not found: {company_name} / {role or 'any role'}",
        )
    return CompanyInfo(
        id=row.id,
        company=row.company_name,
        role=row.role,
        required_skills=list(row.required_skills or []),
        preferred_skills=list(row.preferred_skills or []),
        difficulty_tier=row.difficulty_tier,
    )


# ════════════════════════════════════════════════════════════════
# Mastery computation (the DYNAMIC bit of the weights)
# ════════════════════════════════════════════════════════════════

@dataclass
class MasterySnapshot:
    per_skill: dict[str, float]   # skill name → mastery in [0, 1]
    quiz_topics: dict[str, float] # raw quiz topic averages (for debugging)
    declared_skills: list[str]


def _normalize(name: str) -> str:
    return name.strip().lower()


def _name_matches(a: str, b: str) -> bool:
    """Word-level match — case-insensitive, strip punctuation.

    Two names match iff they share at least one meaningful token, or one is
    an exact substring of the other at a word boundary. We deliberately avoid
    naive substring matches because "Go" is a substring of "algorithm".
    """
    na = _normalize(a).replace("-", " ").replace("_", " ")
    nb = _normalize(b).replace("-", " ").replace("_", " ")
    if na == nb:
        return True
    # Word-boundary containment: every word of the shorter string must appear
    # as a distinct word in the longer string.
    tokens_a = [t for t in na.split() if len(t) >= 2]
    tokens_b = [t for t in nb.split() if len(t) >= 2]
    if not tokens_a or not tokens_b:
        return False
    shorter, longer = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
    longer_set = set(longer)
    # Require EVERY token of the shorter name to appear — avoids matching
    # "Arrays" with a quiz topic named "Huffman Algorithm Steps".
    return all(t in longer_set for t in shorter)


def compute_mastery(
    db: Session, user: User, *, graph_nodes: list[str]
) -> MasterySnapshot:
    """Compute the student's mastery level for every node in the graph.

    Inputs considered:
    - `student_profile.skills` → IMPLICIT_SKILL_MASTERY (0.75) baseline
    - Per-topic quiz averages → full credit (0-1 scaled from the average %)

    If both signals are present, the quiz-backed score takes priority
    (it's more recent evidence).
    """
    mastery: dict[str, float] = {name: 0.0 for name in graph_nodes}

    declared: list[str] = []
    if user.student_profile and user.student_profile.skills:
        declared = [str(s) for s in user.student_profile.skills if s]

    for skill in graph_nodes:
        for d in declared:
            if _name_matches(skill, d):
                mastery[skill] = max(mastery[skill], IMPLICIT_SKILL_MASTERY)
                break

    # Quiz-topic averages (reuse the answers JSON we already store on attempts)
    topic_bucket: dict[str, dict] = defaultdict(lambda: {"correct": 0, "total": 0})
    attempts = db.execute(
        select(QuizAttempt, Quiz)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .where(QuizAttempt.student_id == user.id)
    ).all()
    for attempt, _quiz in attempts:
        if not attempt.answers:
            continue
        for ans in attempt.answers:
            topic = (ans.get("topic") or "").strip()
            if not topic:
                continue
            topic_bucket[topic]["total"] += 1
            if ans.get("is_correct"):
                topic_bucket[topic]["correct"] += 1

    quiz_topics: dict[str, float] = {}
    for topic, b in topic_bucket.items():
        if b["total"] == 0:
            continue
        frac = b["correct"] / b["total"]
        quiz_topics[topic] = round(frac, 3)
        # Project the quiz topic onto graph nodes via fuzzy match
        for skill in graph_nodes:
            if _name_matches(skill, topic):
                mastery[skill] = max(mastery[skill], frac * QUIZ_MASTERY_WEIGHT)

    return MasterySnapshot(
        per_skill={k: round(v, 3) for k, v in mastery.items()},
        quiz_topics=quiz_topics,
        declared_skills=declared,
    )


# ════════════════════════════════════════════════════════════════
# Dynamic edge rescaling
# ════════════════════════════════════════════════════════════════

def _rescale_graph(
    base_graph: dict[str, dict[str, float]],
    mastery: dict[str, float],
    target_skills: set[str],
) -> dict[str, dict[str, float]]:
    """Apply the dynamic weight formula to every edge.

    Formula (the paper contribution):
        adjusted = base × (1 - α × mastery(u)) × (1 + β × (1 - mastery(v) if v in targets else 0))

    - Strong prerequisite (u) ⇒ cheaper edge.
    - Weak target (v) in the company's required set ⇒ more urgent / slightly
      costlier so Knapsack prefers foundational moves.
    - All edges have a floor of MIN_EDGE_WEIGHT so nothing collapses to 0.
    """
    adjusted: dict[str, dict[str, float]] = {}
    for u, neighbors in base_graph.items():
        adjusted[u] = {}
        for v, base in neighbors.items():
            u_mastery = mastery.get(u, 0.0)
            v_gap = 0.0
            if v in target_skills:
                v_mastery = mastery.get(v, 0.0)
                v_gap = max(0.0, 1.0 - v_mastery)
            weight = base * (1.0 - CONFIDENCE_ALPHA * u_mastery) * (1.0 + URGENCY_BETA * v_gap)
            adjusted[u][v] = max(MIN_EDGE_WEIGHT, round(weight, 2))
    return adjusted


# ════════════════════════════════════════════════════════════════
# Main adaptive plan
# ════════════════════════════════════════════════════════════════

@dataclass
class GapBreakdown:
    student_has: list[str]
    missing: list[str]
    present_count: int
    required_count: int
    coverage_percent: float
    gap_percent: float
    cosine_similarity: float


@dataclass
class AdaptivePlan:
    company: CompanyInfo
    mastery: MasterySnapshot
    gap: GapBreakdown
    base_graph: dict[str, dict[str, float]]
    dynamic_graph: dict[str, dict[str, float]]
    dijkstra_paths: dict[str, dijkstra_mod.ShortestPathResult]
    mst: mst_mod.MSTResult
    knapsack: knapsack_mod.KnapsackResult
    plan_id: uuid.UUID | None


def _compute_gap(company: CompanyInfo, mastery: MasterySnapshot) -> GapBreakdown:
    required = company.required_skills
    present: list[str] = []
    missing: list[str] = []
    for skill in required:
        if mastery.per_skill.get(skill, 0.0) >= 0.5:
            present.append(skill)
        else:
            missing.append(skill)

    required_count = len(required)
    present_count = len(present)
    coverage = (present_count / required_count * 100) if required_count else 0.0
    gap = 100.0 - coverage

    # Cosine similarity between the student's mastery vector and a binary
    # requirement vector. Provides a smoother signal than the binary coverage.
    cosine = 0.0
    if required_count > 0:
        dot = sum(mastery.per_skill.get(s, 0.0) for s in required)
        a_norm = math.sqrt(sum(m ** 2 for m in mastery.per_skill.values()))
        b_norm = math.sqrt(required_count)  # all 1s for required skills
        if a_norm > 0 and b_norm > 0:
            cosine = dot / (a_norm * b_norm)

    return GapBreakdown(
        student_has=present,
        missing=missing,
        present_count=present_count,
        required_count=required_count,
        coverage_percent=round(coverage, 2),
        gap_percent=round(gap, 2),
        cosine_similarity=round(cosine, 4),
    )


def _add_virtual_source(
    graph: dict[str, dict[str, float]],
    known_skills: list[str],
    foundation_skills: list[str],
) -> None:
    """Add a synthetic START node with edges into every mastered skill.

    - Mastered skills: 0-cost (the student already has them)
    - Tier-1 foundation skills they DON'T have: small bootstrap cost so every
      target remains reachable but plans still reflect the effort of starting
      from scratch.
    """
    source: dict[str, float] = {}
    for skill in known_skills:
        if skill in graph:
            source[skill] = 0.0
    for skill in foundation_skills:
        if skill in graph and skill not in source:
            source[skill] = 1.0  # small bootstrap cost for foundational skills
    graph["__START__"] = source


def _build_knapsack_items(
    target_skills: list[str],
    paths: dict[str, dijkstra_mod.ShortestPathResult],
    mastery: dict[str, float],
) -> list[knapsack_mod.KnapsackItem]:
    """Turn the Dijkstra result into Knapsack-ready items.

    Each target skill the student is missing becomes a candidate item:
    - hours = Dijkstra path cost from START to that skill
    - value = base value × (1 + mastery-gap bonus)
    - reason = human-readable path description
    """
    items: list[knapsack_mod.KnapsackItem] = []
    for skill in target_skills:
        path_result = paths.get(skill)
        if path_result is None or math.isinf(path_result.total_cost):
            continue
        skill_mastery = mastery.get(skill, 0.0)
        if skill_mastery >= 0.95:
            # Already mastered — no need for the Knapsack to consider it
            continue
        hours = max(0.5, round(path_result.total_cost, 2))
        gap = max(0.0, 1.0 - skill_mastery)
        value = COMPANY_MATCH_BASE_VALUE * (1.0 + gap)
        # Path string — strip the synthetic __START__ marker
        path_nodes = [n for n in path_result.path if n != "__START__"]
        reason = " → ".join(path_nodes) if path_nodes else skill
        items.append(
            knapsack_mod.KnapsackItem(
                topic=skill,
                hours=hours,
                value=round(value, 2),
                reason=f"Path: {reason}",
            )
        )
    return items


def build_adaptive_plan(
    db: Session,
    user: User,
    *,
    company_name: str,
    role: str | None,
    available_hours: float,
    persist: bool = True,
) -> AdaptivePlan:
    """Full adaptive plan. The heart of the research paper."""
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Adaptive learning plans are only available to students.",
        )

    # 1. Load graph + company
    base_graph, nodes = _load_base_graph(db)
    node_names = [n.name for n in nodes]
    company = get_company(db, company_name=company_name, role=role)

    # 2. Mastery
    mastery = compute_mastery(db, user, graph_nodes=node_names)

    # 3. Gap
    gap = _compute_gap(company, mastery)

    # 4. Dynamic weights
    target_set = set(company.required_skills)
    dynamic_graph = _rescale_graph(base_graph, mastery.per_skill, target_set)

    # 5. Dijkstra from a synthetic START to every required skill.
    # Bootstrap sources: (a) mastered skills at 0 cost, (b) tier-1 foundation
    # skills at small cost, (c) "orphan" root nodes that have no incoming
    # edges — otherwise skills like OS Concepts / Problem Solving (which sit
    # at the top of their respective dependency chains) would be unreachable.
    known_skills = [s for s, m in mastery.per_skill.items() if m >= 0.5]
    tier_1_skills = [n.name for n in nodes if n.difficulty_tier == 1]
    # Find orphan roots — every node except the ones with ≥ 1 incoming edge
    incoming: set[str] = set()
    for u, neighbors in base_graph.items():
        for v in neighbors:
            incoming.add(v)
    orphan_roots = [n.name for n in nodes if n.name not in incoming]
    foundation_skills = list(dict.fromkeys(tier_1_skills + orphan_roots))
    _add_virtual_source(dynamic_graph, known_skills, foundation_skills)
    paths = dijkstra_mod.dijkstra_multi_target(
        dynamic_graph,
        source="__START__",
        targets=list(company.required_skills),
    )

    # 6. Prim's MST over the subgraph induced by target skills + their paths
    involved: set[str] = set()
    for res in paths.values():
        for node in res.path:
            if node != "__START__":
                involved.add(node)
    involved.update(company.required_skills)
    involved.update(known_skills)

    # Subgraph containing only the involved nodes
    sub_graph: dict[str, dict[str, float]] = {}
    for u in involved:
        if u not in base_graph:
            continue
        sub_graph[u] = {v: w for v, w in base_graph[u].items() if v in involved}
    mst = mst_mod.mst_over_subset(sub_graph, list(involved))

    # 7. Knapsack — optimise over missing required skills
    items = _build_knapsack_items(
        target_skills=company.required_skills,
        paths=paths,
        mastery=mastery.per_skill,
    )
    knapsack_result = knapsack_mod.solve(items, budget_hours=available_hours)

    plan_id: uuid.UUID | None = None
    if persist:
        predicted_improvement = _estimate_improvement(knapsack_result, gap)
        record = StudyOptimizerResult(
            student_id=user.id,
            target_company=company.company,
            target_role=company.role,
            available_hours=Decimal(f"{available_hours:.2f}"),
            included_topics=[
                {
                    "topic": item.topic,
                    "hours": item.hours,
                    "value": item.value,
                    "reason": item.reason,
                }
                for item in knapsack_result.included
            ],
            excluded_topics=[
                {
                    "topic": item.topic,
                    "hours": item.hours,
                    "value": item.value,
                    "reason": item.reason,
                }
                for item in knapsack_result.excluded
            ],
            predicted_improvement=Decimal(f"{predicted_improvement:.2f}"),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        plan_id = record.id

    return AdaptivePlan(
        company=company,
        mastery=mastery,
        gap=gap,
        base_graph=base_graph,
        dynamic_graph=dynamic_graph,
        dijkstra_paths=paths,
        mst=mst,
        knapsack=knapsack_result,
        plan_id=plan_id,
    )


def _estimate_improvement(
    knapsack: knapsack_mod.KnapsackResult, gap: GapBreakdown
) -> float:
    """Heuristic used for research logging — the predicted gain in fit score.

    Fit score is roughly `coverage_percent`. Each included skill that was
    previously missing bumps coverage by 1/required_count × 100. We apply an
    efficiency discount based on time budget saturation.
    """
    if gap.required_count == 0:
        return 0.0
    per_skill_gain = 100.0 / gap.required_count
    base = per_skill_gain * len(knapsack.included)
    # Discount by how heavily we saturated the budget — rewards balanced plans
    saturation = 1.0
    if knapsack.budget_hours > 0:
        saturation = min(1.0, knapsack.total_hours / knapsack.budget_hours)
    return round(base * (0.6 + 0.4 * saturation), 2)


# ════════════════════════════════════════════════════════════════
# Research paper data — plan history
# ════════════════════════════════════════════════════════════════

def list_plan_history(
    db: Session, user: User, *, limit: int = 20
) -> list[StudyOptimizerResult]:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403, detail="Only students have optimizer history."
        )
    rows = db.scalars(
        select(StudyOptimizerResult)
        .where(StudyOptimizerResult.student_id == user.id)
        .order_by(StudyOptimizerResult.created_at.desc())
        .limit(limit)
    ).all()
    return list(rows)
