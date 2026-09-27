"""Pure grade-computation engine (no DB) — the math core of the grading system.

Implements the RVCE rules (Handbook §4.3/§4.4 + grading_feature_spec.md):
condensation (CIE/SEE → 50 each), pass gates (CIE 40% / SEE 35% / aggregate 40%,
theory & lab separable), the absolute 10-point grade table, per-CO attainment,
and SGPA/CGPA. Primitives in, dataclasses out — like dijkstra.py / knapsack.py.

Rounding: final score → nearest integer (ROUND_HALF_UP, so 78.5 → 79); SGPA/CGPA
→ 2 decimals (ROUND_HALF_UP). All ratios guard a zero denominator.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# (low, high, letter, grade_point) — inclusive integer bands on the 0–100 score.
DEFAULT_GRADE_BANDS: list[tuple[int, int, str, int]] = [
    (90, 100, "O", 10),
    (80, 89, "A+", 9),
    (70, 79, "A", 8),
    (60, 69, "B+", 7),
    (55, 59, "B", 6),
    (50, 54, "C", 5),
    (40, 49, "P", 4),
    (0, 39, "F", 0),
]

DEFAULT_CIE_MIN_PCT = 40.0
DEFAULT_SEE_MIN_PCT = 35.0
DEFAULT_AGGREGATE_MIN_PCT = 40.0


# ── small numeric helpers ────────────────────────────────────────────────────
def round_int_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def safe_pct(obtained: float | None, maximum: float | None) -> float:
    """obtained/maximum × 100, guarded against a None/zero denominator."""
    if not maximum or float(maximum) <= 0 or obtained is None:
        return 0.0
    return (float(obtained) / float(maximum)) * 100.0


# ── result dataclasses ───────────────────────────────────────────────────────
@dataclass
class CondensedScore:
    cie_50: float
    see_50: float
    final_score: float
    final_rounded: int


@dataclass
class GateResult:
    passed: bool
    gate_failed: str  # "none" | "cie" | "see" | "aggregate" | "cie_lab" | ...


@dataclass
class GradeResult:
    letter: str
    grade_point: int


@dataclass
class COAttainment:
    co: str
    obtained: float
    max: float
    pct: float


@dataclass
class SubjectGradeComputation:
    cie_50: float
    see_50: float
    final_score: float
    final_rounded: int
    letter: str
    grade_point: int
    passed: bool
    gate_failed: str


@dataclass
class SGPAResult:
    sgpa: float
    total_credits: int
    total_grade_points: float


# ── core functions ───────────────────────────────────────────────────────────
def condense(
    cie_obtained: float | None,
    cie_max: float | None,
    see_obtained: float | None,
    see_max: float | None,
) -> CondensedScore:
    """Condense CIE and SEE each to 50 → final score out of 100."""
    cie_50 = safe_pct(cie_obtained, cie_max) / 100.0 * 50.0
    see_50 = safe_pct(see_obtained, see_max) / 100.0 * 50.0
    final = cie_50 + see_50
    return CondensedScore(round2(cie_50), round2(see_50), round2(final), round_int_half_up(final))


def score_to_grade(score: float, bands: list[tuple[int, int, str, int]] | None = None) -> GradeResult:
    bands = bands or DEFAULT_GRADE_BANDS
    s = max(0, min(100, int(score)))
    for lo, hi, letter, gp in bands:
        if lo <= s <= hi:
            return GradeResult(letter, gp)
    return GradeResult("F", 0)


def apply_gates(
    cie_pct: float,
    see_pct: float,
    aggregate_pct: float,
    *,
    cie_min: float = DEFAULT_CIE_MIN_PCT,
    see_min: float = DEFAULT_SEE_MIN_PCT,
    agg_min: float = DEFAULT_AGGREGATE_MIN_PCT,
) -> GateResult:
    """Non-split subjects: CIE ≥ cie_min, SEE ≥ see_min, aggregate ≥ agg_min."""
    if cie_pct < cie_min:
        return GateResult(False, "cie")
    if see_pct < see_min:
        return GateResult(False, "see")
    if aggregate_pct < agg_min:
        return GateResult(False, "aggregate")
    return GateResult(True, "none")


def apply_split_gates(
    cie_theory_pct: float,
    see_theory_pct: float,
    cie_lab_pct: float,
    see_lab_pct: float,
    aggregate_pct: float,
    *,
    cie_min: float = DEFAULT_CIE_MIN_PCT,
    see_min: float = DEFAULT_SEE_MIN_PCT,
    cie_lab_min: float = DEFAULT_CIE_MIN_PCT,
    see_lab_min: float = DEFAULT_SEE_MIN_PCT,
    agg_min: float = DEFAULT_AGGREGATE_MIN_PCT,
) -> GateResult:
    """Theory + lab subjects: gate theory and lab separately, aggregate combined."""
    if cie_theory_pct < cie_min:
        return GateResult(False, "cie_theory")
    if see_theory_pct < see_min:
        return GateResult(False, "see_theory")
    if cie_lab_pct < cie_lab_min:
        return GateResult(False, "cie_lab")
    if see_lab_pct < see_lab_min:
        return GateResult(False, "see_lab")
    if aggregate_pct < agg_min:
        return GateResult(False, "aggregate")
    return GateResult(True, "none")


def compute_co_attainment(per_question: list[dict]) -> list[COAttainment]:
    """Group ``[{co, obtained, max}, ...]`` by CO → obtained/max + %.

    Preserves first-seen CO order; every CO that appears in the input is output.
    """
    order: list[str] = []
    agg: dict[str, list[float]] = {}
    for q in per_question:
        co = q.get("co")
        if not co:
            continue
        if co not in agg:
            agg[co] = [0.0, 0.0]
            order.append(co)
        agg[co][0] += float(q.get("obtained") or 0)
        agg[co][1] += float(q.get("max") or 0)
    return [
        COAttainment(co, round2(agg[co][0]), round2(agg[co][1]), round2(safe_pct(agg[co][0], agg[co][1])))
        for co in order
    ]


def compute_subject_grade(
    cie_obtained: float | None,
    cie_max: float | None,
    see_obtained: float | None,
    see_max: float | None,
    *,
    cie_min: float = DEFAULT_CIE_MIN_PCT,
    see_min: float = DEFAULT_SEE_MIN_PCT,
    agg_min: float = DEFAULT_AGGREGATE_MIN_PCT,
    split: bool = False,
    cie_theory_obtained: float | None = None,
    cie_theory_max: float | None = None,
    cie_lab_obtained: float | None = None,
    cie_lab_max: float | None = None,
    see_theory_obtained: float | None = None,
    see_theory_max: float | None = None,
    see_lab_obtained: float | None = None,
    see_lab_max: float | None = None,
    cie_lab_min: float | None = None,
    see_lab_min: float | None = None,
    bands: list[tuple[int, int, str, int]] | None = None,
) -> SubjectGradeComputation:
    """Full per-subject grade: condense → gates → letter/grade-point.

    A failed gate forces F (grade point 0) regardless of the score — the headline
    rule from Handbook §4.4.
    """
    cond = condense(cie_obtained, cie_max, see_obtained, see_max)
    aggregate_pct = float(cond.final_rounded)  # the score out of 100

    if split:
        gate = apply_split_gates(
            safe_pct(cie_theory_obtained, cie_theory_max),
            safe_pct(see_theory_obtained, see_theory_max),
            safe_pct(cie_lab_obtained, cie_lab_max),
            safe_pct(see_lab_obtained, see_lab_max),
            aggregate_pct,
            cie_min=cie_min,
            see_min=see_min,
            cie_lab_min=cie_lab_min if cie_lab_min is not None else cie_min,
            see_lab_min=see_lab_min if see_lab_min is not None else see_min,
            agg_min=agg_min,
        )
    else:
        gate = apply_gates(
            safe_pct(cie_obtained, cie_max),
            safe_pct(see_obtained, see_max),
            aggregate_pct,
            cie_min=cie_min,
            see_min=see_min,
            agg_min=agg_min,
        )

    grade = score_to_grade(cond.final_rounded, bands) if gate.passed else GradeResult("F", 0)
    return SubjectGradeComputation(
        cond.cie_50, cond.see_50, cond.final_score, cond.final_rounded,
        grade.letter, grade.grade_point, gate.passed, gate.gate_failed,
    )


def compute_sgpa(entries: list[tuple[int, int]]) -> SGPAResult:
    """SGPA = Σ(credits × grade_point) / Σ(credits).

    ``entries`` is ``[(credits, grade_point), ...]``. The caller must already
    have excluded 0-credit/audit and transitional courses (they're filtered here
    too, defensively, by dropping credits ≤ 0).
    """
    valid = [(int(c), int(gp)) for c, gp in entries if int(c) > 0]
    total_credits = sum(c for c, _ in valid)
    total_gp = sum(c * gp for c, gp in valid)
    sgpa = round2(total_gp / total_credits) if total_credits else 0.0
    return SGPAResult(sgpa, total_credits, round2(total_gp))


def compute_cgpa(all_entries: list[tuple[int, int]]) -> float:
    """CGPA across all semesters — same formula as SGPA over every graded course."""
    return compute_sgpa(all_entries).sgpa


def reduce_best_of(
    obtained_list: list[float],
    max_list: list[float],
    reduce_to: float,
    top_n: int | None = None,
) -> float:
    """Combine repeated assessments into one CIE component value.

    e.g. "2 tests × 50 reduced to 40", or "best 2 of 3 tests × 50 reduced to 40".
    Picks the best ``top_n`` by obtained marks, sums obtained/max, scales the
    ratio to ``reduce_to``.
    """
    pairs = sorted(zip(obtained_list, max_list), key=lambda p: float(p[0]), reverse=True)
    if top_n is not None:
        pairs = pairs[:top_n]
    raw = sum(float(o) for o, _ in pairs)
    raw_max = sum(float(m) for _, m in pairs)
    if raw_max <= 0:
        return 0.0
    return round2((raw / raw_max) * float(reduce_to))
