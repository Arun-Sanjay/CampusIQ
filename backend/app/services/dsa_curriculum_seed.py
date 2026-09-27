"""Seed the DSA pattern curriculum (Phase 2) from a checked-in JSON file.

`dsa_curriculum.json` is generated once from the source spreadsheet
(`dsa_curriculum.xlsx`) — 38 patterns and 376 deduped LeetCode problems grouped
by the technique that solves them, ordered easy->hard within each pattern. The
app reads the JSON at runtime (no spreadsheet dependency).

Seeding (idempotent, gated on `coding_patterns` being empty):
1. Ensure the 5 in-app-judge problems exist (`coding_problems_seed`).
2. Insert all patterns.
3. Upsert problems by slug:
   - existing rows (the 5 judge problems) are *enriched* with curriculum
     metadata but keep `source='seed_inapp'` + their test cases / starter code;
   - new rows are inserted LeetCode-only (`source='curriculum'`, empty judge
     fields) so the redirect + coach work without an in-app judge.

Curriculum problems carry `skill_node_names` mapped from their pattern so a
self-reported solve still bumps the right skill-graph mastery.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coding import CodingDifficulty, CodingPattern, CodingProblem
from app.services import coding_problems_seed

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).parent / "dsa_curriculum.json"

# Map each pattern to skill-graph node names (from skill_graph_seed) so a solve
# bumps mastery. Patterns with no clean DSA-node match are left empty — the
# solve still records + awards XP, it just doesn't move a specific skill.
PATTERN_SKILL_MAP: dict[str, list[str]] = {
    "arrays-hashing": ["Arrays", "Hashing"],
    "prefix-sum-difference-arrays": ["Arrays"],
    "two-pointers": ["Arrays"],
    "sliding-window": ["Arrays"],
    "fast-slow-pointers": ["Linked Lists"],
    "cyclic-sort": ["Arrays", "Sorting"],
    "stack": ["Stacks & Queues"],
    "monotonic-stack": ["Stacks & Queues"],
    "queue-monotonic-deque": ["Stacks & Queues"],
    "binary-search": ["Searching"],
    "linked-list-in-place-reversal": ["Linked Lists"],
    "trees-dfs": ["Trees"],
    "trees-bfs": ["Trees"],
    "binary-search-trees": ["Trees", "Searching"],
    "tries": ["Tries"],
    "heap-top-k-elements": ["Heaps"],
    "two-heaps": ["Heaps"],
    "k-way-merge": ["Heaps"],
    "backtracking-subsets": ["Backtracking"],
    "graph-traversal-dfs-bfs": ["Graphs"],
    "topological-sort": ["Graphs"],
    "union-find-dsu": ["Graphs"],
    "shortest-path-dijkstra-bellman-ford": ["Graphs"],
    "minimum-spanning-tree": ["Graphs"],
    "1-d-dp-fibonacci-style": ["Dynamic Programming"],
    "knapsack-dp-0-1-unbounded": ["Dynamic Programming"],
    "grid-2-d-dp": ["Dynamic Programming"],
    "lcs-string-dp": ["Dynamic Programming", "Strings"],
    "interval-dp": ["Dynamic Programming"],
    "dp-on-trees": ["Dynamic Programming", "Trees"],
    "bitmask-dp": ["Dynamic Programming"],
    "greedy": ["Greedy Algorithms"],
    "intervals-line-sweep": ["Sorting"],
    "math-geometry": [],
    "bit-manipulation": [],
    "segment-tree-fenwick-bit": ["DSA Advanced"],
    "string-matching-kmp-rabin-karp-z": ["Strings"],
    "misc-quickselect-reservoir-game-theory": ["DSA Advanced"],
}


@lru_cache(maxsize=1)
def _load_data() -> dict:
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))


def _curriculum_description(q: dict, pattern_name: str, core_idea: str) -> str:
    """A short markdown stub for a LeetCode-only problem (we don't store the
    full statement). The Coach recognises these classic problems by name."""
    lc = f" · LeetCode #{q['lc_number']}" if q.get("lc_number") else ""
    parts = [
        f"**{q['title']}**{lc}",
        "",
        f"**{q['difficulty'].title()}** · part of the **{pattern_name}** pattern. "
        f"Read the full statement and solve it on LeetCode (button above), then use "
        f"the Coach for hints — it won't just hand you the answer.",
    ]
    if core_idea:
        parts += ["", f"_Pattern idea: {core_idea}_"]
    if q.get("free_alternative"):
        parts += ["", f"> **Premium problem.** Free alternative: {q['free_alternative']}"]
    return "\n".join(parts)


def seed_if_empty(db: Session) -> int:
    """Seed patterns + curriculum problems if the patterns table is empty.

    Returns the number of new problem rows inserted (0 if already seeded).
    """
    if db.scalar(select(CodingPattern).limit(1)) is not None:
        return 0

    # Make sure the 5 in-app-judge problems exist before we enrich them.
    coding_problems_seed.seed_if_empty(db)

    data = _load_data()

    # Patterns first → slug → (id, name, core_idea)
    pattern_meta: dict[str, dict] = {}
    for p in data["patterns"]:
        pat = CodingPattern(
            slug=p["slug"],
            name=p["name"],
            track=p["track"],
            tier=p["tier"],
            order_num=p["order_num"],
            core_idea=p["core_idea"],
            recognize_when=p["recognize_when"],
            difficulty_span=p["difficulty_span"],
            problem_count=p["problem_count"],
        )
        db.add(pat)
        db.flush()  # populate pat.id
        pattern_meta[p["slug"]] = {"id": pat.id, "name": p["name"], "core_idea": p["core_idea"]}

    existing = {row.slug: row for row in db.scalars(select(CodingProblem)).all()}
    inserted = 0
    enriched = 0

    for q in data["problems"]:
        meta = pattern_meta.get(q["pattern_slug"])
        pattern_id = meta["id"] if meta else None
        pattern_name = meta["name"] if meta else ""
        skills = PATTERN_SKILL_MAP.get(q["pattern_slug"], [])

        row = existing.get(q["slug"])
        if row is not None:
            # Enrich the existing in-app-judge problem; keep source + judge fields.
            row.pattern_id = pattern_id
            row.track = q["track"]
            row.tier = q["tier"]
            row.seq = q["seq"]
            row.lc_number = q["lc_number"]
            row.priority = q["priority"]
            row.is_premium = q["is_premium"]
            row.free_alternative = q["free_alternative"]
            row.also_appears_in = q["also_appears_in"]
            row.leetcode_url = q["leetcode_url"]
            enriched += 1
            continue

        problem = CodingProblem(
            slug=q["slug"],
            title=q["title"],
            description=_curriculum_description(q, pattern_name, meta["core_idea"] if meta else ""),
            difficulty=CodingDifficulty(q["difficulty"]),
            # LeetCode-only — empty judge fields (no in-app editor for these).
            function_name="",
            function_signature={},
            examples=[],
            hints=[],
            starter_code={},
            reference_solution={},
            visible_test_cases=[],
            hidden_test_cases=[],
            comparator="exact",
            topic_tags=[pattern_name] if pattern_name else [],
            skill_node_names=skills,
            leetcode_url=q["leetcode_url"],
            source="curriculum",
            pattern_id=pattern_id,
            track=q["track"],
            tier=q["tier"],
            seq=q["seq"],
            lc_number=q["lc_number"],
            priority=q["priority"],
            is_premium=q["is_premium"],
            free_alternative=q["free_alternative"],
            also_appears_in=q["also_appears_in"],
        )
        db.add(problem)
        inserted += 1

    db.commit()
    logger.info(
        "Seeded curriculum: %d patterns, %d new problems, %d enriched",
        len(data["patterns"]),
        inserted,
        enriched,
    )
    return inserted
