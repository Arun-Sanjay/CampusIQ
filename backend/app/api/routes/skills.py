"""Skill Gap Analyzer + Adaptive Learning Engine endpoints (Phase 15)."""
from __future__ import annotations

import math

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.skills import (
    AdaptivePlanRequest,
    AdaptivePlanResponse,
    CompanyProfile,
    GapBreakdownResponse,
    KnapsackItemResponse,
    KnapsackResponse,
    MasteryItem,
    MasterySnapshotResponse,
    MSTEdge,
    MSTResponse,
    PathEdge,
    SkillEdgeResponse,
    SkillNodeResponse,
    SkillPathResult,
    StudyOptimizerHistoryRow,
)
from app.services import skill_graph as skill_graph_service

router = APIRouter()


# ════════════════════════════════════════════════════════════════
# Reference data
# ════════════════════════════════════════════════════════════════

@router.get(
    "/nodes",
    response_model=list[SkillNodeResponse],
    summary="List all skill nodes in the graph",
)
def list_skill_nodes(
    db: DbSession, current_user: CurrentUser
) -> list[SkillNodeResponse]:
    nodes = skill_graph_service.list_nodes(db)
    return [
        SkillNodeResponse(
            name=n.name,
            domain=n.domain,
            description=n.description,
            difficulty_tier=n.difficulty_tier,
        )
        for n in nodes
    ]


@router.get(
    "/graph",
    response_model=list[SkillEdgeResponse],
    summary="Full prerequisite edge list (base weights only)",
)
def get_skill_graph(
    db: DbSession, current_user: CurrentUser
) -> list[SkillEdgeResponse]:
    graph, _ = skill_graph_service._load_base_graph(db)
    edges: list[SkillEdgeResponse] = []
    for u, neighbors in graph.items():
        for v, w in neighbors.items():
            edges.append(
                SkillEdgeResponse(
                    from_skill=u,
                    to_skill=v,
                    base_weight_hours=float(w),
                )
            )
    edges.sort(key=lambda e: (e.from_skill, e.to_skill))
    return edges


@router.get(
    "/companies",
    response_model=list[CompanyProfile],
    summary="List all company profiles",
)
def list_companies(
    db: DbSession, current_user: CurrentUser
) -> list[CompanyProfile]:
    companies = skill_graph_service.list_companies(db)
    return [
        CompanyProfile(
            id=c.id,
            company=c.company,
            role=c.role,
            required_skills=c.required_skills,
            preferred_skills=c.preferred_skills,
            difficulty_tier=c.difficulty_tier,
        )
        for c in companies
    ]


# ════════════════════════════════════════════════════════════════
# Adaptive plan (the research core)
# ════════════════════════════════════════════════════════════════

@router.post(
    "/me/plan",
    response_model=AdaptivePlanResponse,
    summary="Student: build an adaptive learning plan for a target company/role",
)
def build_plan(
    data: AdaptivePlanRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> AdaptivePlanResponse:
    plan = skill_graph_service.build_adaptive_plan(
        db,
        current_user,
        company_name=data.company,
        role=data.role,
        available_hours=data.available_hours,
    )

    mastery_items = sorted(
        [MasteryItem(skill=k, mastery=v) for k, v in plan.mastery.per_skill.items()],
        key=lambda m: (-m.mastery, m.skill),
    )

    paths_out: list[SkillPathResult] = []
    for skill, result in plan.dijkstra_paths.items():
        reachable = not math.isinf(result.total_cost) and bool(result.path)
        paths_out.append(
            SkillPathResult(
                target=skill,
                total_hours=round(result.total_cost, 2) if reachable else 0.0,
                nodes=[n for n in result.path if n != "__START__"],
                edges=[
                    PathEdge(from_skill=u if u != "__START__" else "Start", to_skill=v, weight=round(w, 2))
                    for (u, v, w) in result.edges_with_weights
                ],
                reachable=reachable,
            )
        )
    paths_out.sort(key=lambda p: (not p.reachable, p.total_hours))

    mst_out = MSTResponse(
        nodes=plan.mst.nodes,
        edges=[
            MSTEdge(from_skill=u, to_skill=v, weight=round(w, 2))
            for (u, v, w) in plan.mst.edges
        ],
        total_weight=plan.mst.total_weight,
    )

    knapsack_items: list[KnapsackItemResponse] = []
    for item in plan.knapsack.included:
        knapsack_items.append(
            KnapsackItemResponse(
                topic=item.topic,
                hours=item.hours,
                value=item.value,
                reason=item.reason,
                included=True,
            )
        )
    for item in plan.knapsack.excluded:
        knapsack_items.append(
            KnapsackItemResponse(
                topic=item.topic,
                hours=item.hours,
                value=item.value,
                reason=item.reason,
                included=False,
            )
        )

    predicted_improvement = skill_graph_service._estimate_improvement(
        plan.knapsack, plan.gap
    )

    return AdaptivePlanResponse(
        plan_id=plan.plan_id,
        company=CompanyProfile(
            id=plan.company.id,
            company=plan.company.company,
            role=plan.company.role,
            required_skills=plan.company.required_skills,
            preferred_skills=plan.company.preferred_skills,
            difficulty_tier=plan.company.difficulty_tier,
        ),
        mastery=MasterySnapshotResponse(
            declared_skills=plan.mastery.declared_skills,
            quiz_topics=plan.mastery.quiz_topics,
            per_skill=mastery_items,
        ),
        gap=GapBreakdownResponse(
            student_has=plan.gap.student_has,
            missing=plan.gap.missing,
            present_count=plan.gap.present_count,
            required_count=plan.gap.required_count,
            coverage_percent=plan.gap.coverage_percent,
            gap_percent=plan.gap.gap_percent,
            cosine_similarity=plan.gap.cosine_similarity,
        ),
        paths=paths_out,
        mst=mst_out,
        knapsack=KnapsackResponse(
            budget_hours=plan.knapsack.budget_hours,
            total_hours=plan.knapsack.total_hours,
            total_value=plan.knapsack.total_value,
            predicted_improvement_percent=predicted_improvement,
            items=knapsack_items,
        ),
    )


@router.get(
    "/me/plans",
    response_model=list[StudyOptimizerHistoryRow],
    summary="Student: past adaptive plan history (for research paper data)",
)
def list_plan_history(
    db: DbSession, current_user: CurrentUser
) -> list[StudyOptimizerHistoryRow]:
    rows = skill_graph_service.list_plan_history(db, current_user)
    return [
        StudyOptimizerHistoryRow(
            id=r.id,
            target_company=r.target_company,
            target_role=r.target_role,
            available_hours=float(r.available_hours),
            included_topics=list(r.included_topics or []),
            predicted_improvement=float(r.predicted_improvement),
            actual_improvement=float(r.actual_improvement) if r.actual_improvement is not None else None,
            created_at=r.created_at,
        )
        for r in rows
    ]
