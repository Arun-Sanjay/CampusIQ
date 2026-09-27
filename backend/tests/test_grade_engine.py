"""Unit tests for the pure grade engine — validated against grading_feature_spec.md."""
from app.services import grade_engine as ge


# ── grade table ──────────────────────────────────────────────────────────────
def test_grade_table_boundaries():
    cases = {90: ("O", 10), 89: ("A+", 9), 80: ("A+", 9), 78: ("A", 8),
             70: ("A", 8), 60: ("B+", 7), 55: ("B", 6), 54: ("C", 5),
             50: ("C", 5), 49: ("P", 4), 40: ("P", 4), 39: ("F", 0), 0: ("F", 0)}
    for score, (letter, gp) in cases.items():
        g = ge.score_to_grade(score)
        assert (g.letter, g.grade_point) == (letter, gp), score


def test_score_clamped():
    assert ge.score_to_grade(120).letter == "O"
    assert ge.score_to_grade(-5).letter == "F"


# ── rounding (ROUND_HALF_UP) ─────────────────────────────────────────────────
def test_round_half_up():
    assert ge.round_int_half_up(78.5) == 79
    assert ge.round_int_half_up(78.33) == 78
    assert ge.round_int_half_up(78.49) == 78


def test_safe_pct_guards_zero():
    assert ge.safe_pct(10, 0) == 0.0
    assert ge.safe_pct(10, None) == 0.0
    assert ge.safe_pct(None, 50) == 0.0
    assert ge.safe_pct(25, 50) == 50.0


# ── condensation + the worked IoT example (spec §8) ──────────────────────────
def test_condense_iot_example():
    c = ge.condense(125, 150, 110, 150)
    assert c.cie_50 == 41.67
    assert c.see_50 == 36.67
    assert c.final_rounded == 78


def test_iot_subject_grade_is_A_8():
    r = ge.compute_subject_grade(125, 150, 110, 150)
    assert r.final_rounded == 78
    assert (r.letter, r.grade_point) == ("A", 8)
    assert r.passed is True
    assert r.gate_failed == "none"


def test_fail_by_see_gate_forces_F():
    # CIE 130/150 (86.7%) but SEE 50/150 (33.3% < 35%) → F regardless of score 60.
    r = ge.compute_subject_grade(130, 150, 50, 150)
    assert r.final_rounded == 60
    assert r.passed is False
    assert r.gate_failed == "see"
    assert (r.letter, r.grade_point) == ("F", 0)


def test_fail_by_cie_gate():
    r = ge.compute_subject_grade(30, 100, 90, 100)  # CIE 30% < 40%
    assert r.gate_failed == "cie"
    assert r.grade_point == 0


def test_pass_at_floor():
    # Exactly 40% CIE, 35% SEE → aggregate 37.5 → rounds to 38 < 40 → aggregate gate fails.
    r = ge.compute_subject_grade(40, 100, 35, 100)
    assert r.gate_failed == "aggregate"
    # Bump SEE so aggregate clears 40.
    r2 = ge.compute_subject_grade(40, 100, 40, 100)
    assert r2.passed is True
    assert r2.final_rounded == 40
    assert r2.letter == "P"


# ── split (theory + lab) gating ──────────────────────────────────────────────
def test_split_lab_fails_separately():
    # Theory fine, lab SEE 30% < 35% → fails on lab even if aggregate is high.
    r = ge.compute_subject_grade(
        125, 150, 110, 150, split=True,
        cie_theory_obtained=85, cie_theory_max=100, cie_lab_obtained=40, cie_lab_max=50,
        see_theory_obtained=80, see_theory_max=100, see_lab_obtained=15, see_lab_max=50,
    )
    assert r.gate_failed == "see_lab"
    assert r.grade_point == 0


# ── CO attainment (spec §7 example) ──────────────────────────────────────────
def test_co_attainment_matches_spec():
    pq = [
        {"co": "CO1", "obtained": 7, "max": 10},
        {"co": "CO2", "obtained": 10, "max": 15},
        {"co": "CO2", "obtained": 8, "max": 10},
        {"co": "CO3", "obtained": 11, "max": 15},
        {"co": "CO4", "obtained": 3, "max": 5},
        {"co": "CO5", "obtained": 4, "max": 5},
    ]
    res = {c.co: c for c in ge.compute_co_attainment(pq)}
    assert (res["CO1"].obtained, res["CO1"].max, res["CO1"].pct) == (7.0, 10.0, 70.0)
    assert (res["CO2"].obtained, res["CO2"].max, res["CO2"].pct) == (18.0, 25.0, 72.0)
    assert res["CO3"].pct == 73.33
    assert res["CO4"].pct == 60.0
    assert res["CO5"].pct == 80.0


# ── SGPA / CGPA (spec §9 worked example) ─────────────────────────────────────
def test_sgpa_worked_example():
    entries = [(3, 9), (4, 8), (4, 8), (3, 7), (2, 9), (2, 10), (2, 8)]  # + audit (0, _)
    res = ge.compute_sgpa(entries + [(0, 0)])
    assert res.total_credits == 20
    assert res.total_grade_points == 166.0
    assert res.sgpa == 8.3


def test_sgpa_zero_credits_safe():
    assert ge.compute_sgpa([(0, 10)]).sgpa == 0.0
    assert ge.compute_sgpa([]).sgpa == 0.0


def test_cgpa_across_semesters():
    assert ge.compute_cgpa([(4, 10), (4, 8)]) == 9.0


# ── reduce_best_of (CIE component combination) ───────────────────────────────
def test_reduce_two_tests_to_40():
    # Two tests /50: 40 and 36 → 76/100 → reduced to 40 → 30.4
    assert ge.reduce_best_of([40, 36], [50, 50], 40) == 30.4


def test_reduce_best_two_of_three():
    # Best 2 of [40, 36, 45] → 85/100 → reduced to 40 → 34.0
    assert ge.reduce_best_of([40, 36, 45], [50, 50, 50], 40, top_n=2) == 34.0


def test_reduce_empty_safe():
    assert ge.reduce_best_of([], [], 40) == 0.0
