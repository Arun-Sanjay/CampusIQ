"""Skill Tree service (Phase 18, F13).

Reuses the Phase 15 skill graph + mastery snapshot to render a domain-
grouped skill tree. Uses DFS + topological sort (DAA Unit II) to decide
which skills are "unlocked" for the student:

    - MASTERED:     mastery ≥ MASTERY_THRESHOLD
    - UNLOCKED:     all prerequisites (incoming edges) are mastered,
                    but this skill itself isn't
    - LOCKED:       otherwise

Each domain gets a progress percentage (mastered / total) that drives the
UI's 6-card grid.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import skill_graph


UnlockStateLiteral = Literal["locked", "unlocked", "mastered"]

MASTERY_THRESHOLD = 0.5


@dataclass
class SkillNodeState:
    name: str
    domain: str
    description: str
    difficulty_tier: int
    mastery: float
    state: UnlockStateLiteral


@dataclass
class DomainProgress:
    name: str
    total_skills: int
    mastered_count: int
    unlocked_count: int
    progress_percent: float
    skills: list[SkillNodeState]


@dataclass
class SkillTreeResponse:
    domains: list[DomainProgress]
    mastered_count: int
    total_count: int
    overall_percent: float


def build_skill_tree(db: Session, user: User) -> SkillTreeResponse:
    """Return the full skill tree grouped by domain with per-node unlock state."""
    base_graph, nodes = skill_graph._load_base_graph(db)
    if not nodes:
        return SkillTreeResponse(domains=[], mastered_count=0, total_count=0, overall_percent=0.0)

    node_names = [n.name for n in nodes]
    mastery = skill_graph.compute_mastery(db, user, graph_nodes=node_names)

    # ── DFS-based unlock detection ─────────────────────────────
    # For every node, collect its incoming edges (prerequisites) by
    # reversing the adjacency list.
    prereqs: dict[str, list[str]] = defaultdict(list)
    for u, neighbors in base_graph.items():
        for v in neighbors:
            prereqs[v].append(u)

    # A node is unlocked iff every prerequisite has mastery ≥ threshold.
    # Roots (no prereqs) are always unlocked.
    mastered: set[str] = {
        n.name for n in nodes if mastery.per_skill.get(n.name, 0.0) >= MASTERY_THRESHOLD
    }
    states: dict[str, UnlockStateLiteral] = {}
    for n in nodes:
        if n.name in mastered:
            states[n.name] = "mastered"
            continue
        prereq_list = prereqs.get(n.name, [])
        if not prereq_list:
            states[n.name] = "unlocked"
            continue
        if all(p in mastered for p in prereq_list):
            states[n.name] = "unlocked"
        else:
            states[n.name] = "locked"

    # ── Group into domains ─────────────────────────────────────
    by_domain: dict[str, list[SkillNodeState]] = defaultdict(list)
    for n in nodes:
        node_state = SkillNodeState(
            name=n.name,
            domain=n.domain or "misc",
            description=n.description or "",
            difficulty_tier=n.difficulty_tier,
            mastery=round(mastery.per_skill.get(n.name, 0.0), 3),
            state=states[n.name],
        )
        by_domain[node_state.domain].append(node_state)

    domains: list[DomainProgress] = []
    for domain_name, skills in by_domain.items():
        # Sort skills within a domain by difficulty tier then name
        skills_sorted = sorted(skills, key=lambda s: (s.difficulty_tier, s.name))
        mastered_n = sum(1 for s in skills_sorted if s.state == "mastered")
        unlocked_n = sum(1 for s in skills_sorted if s.state == "unlocked")
        total = len(skills_sorted)
        pct = round((mastered_n / total) * 100, 2) if total else 0.0
        domains.append(
            DomainProgress(
                name=domain_name,
                total_skills=total,
                mastered_count=mastered_n,
                unlocked_count=unlocked_n,
                progress_percent=pct,
                skills=skills_sorted,
            )
        )

    # Order domains by # mastered skills desc, then alphabetically
    domains.sort(key=lambda d: (-d.mastered_count, d.name))

    total_count = sum(d.total_skills for d in domains)
    mastered_total = sum(d.mastered_count for d in domains)
    overall = round((mastered_total / total_count) * 100, 2) if total_count else 0.0

    return SkillTreeResponse(
        domains=domains,
        mastered_count=mastered_total,
        total_count=total_count,
        overall_percent=overall,
    )
