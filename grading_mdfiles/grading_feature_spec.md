# CampusIQ — Grading Feature (domain spec)

This describes **how grading works**, end to end, so the feature computes the right grade for any subject. No implementation details — just the rules, the mark structures, and a fully worked sample subject. (The AI evaluator feeds in the raw marks; this feature turns marks into grades.)

---

## 1. What the grading feature does

For each student, per subject:

1. Take the **CIE** marks (continuous internal evaluation — quizzes, tests, experiential learning, lab) and the **SEE** marks (semester-end exam — theory and/or lab).
2. **Condense** CIE to 50 and SEE to 50 → a final score out of **100**.
3. Apply **pass/fail gates**.
4. Assign a **grade** and **grade point** from the score.
5. Roll up across subjects into **SGPA** (semester) and **CGPA** (cumulative).

It also reports **per-CO attainment** (marks + % for each course outcome) for every exam.

---

## 2. Grade table (authoritative)

| Score (out of 100) | 90–100 | 80–89 | 70–79 | 60–69 | 55–59 | 50–54 | 40–49 | 0–39 |
|---|---|---|---|---|---|---|---|---|
| **Grade** | O | A+ | A | B+ | B | C | P | F |
| **Grade Point** | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 0 |

The final score is rounded to the nearest whole number before the grade is looked up.

---

## 3. How marks are structured

Every subject is one of three evaluation shapes. CIE and SEE maximums differ by shape, which is why condensation (§4) exists.

### 3.1 Theory-only subject — CIE 100, SEE 100

**CIE (100):**

| Component | Breakup | Marks |
|---|---|---|
| Quizzes | 2 quizzes × 10, summed | 20 |
| Tests | 2 tests × 50 (= 100), **reduced to 40** | 40 |
| Experiential Learning | Case study 10 + Program-specific 10 + Video seminar 20 | 40 |
| **CIE total** | | **100** |

**SEE (100):**

| Part | Contents | Marks |
|---|---|---|
| Part A | Objective questions, entire syllabus | 20 |
| Part B | Unit 1 (compulsory) 16 + Units 2–5 (internal choice) 16 each | 80 |
| **SEE total** | | **100** |

### 3.2 Theory + Practice subject — CIE 150, SEE 150

This is for subjects with both lectures and a lab (L:T:P with P ≥ 1). CIE and SEE each split into a theory part and a lab part.

**CIE (150) = Theory CIE 100 + Lab CIE 50:**

| Component | Breakup | Marks |
|---|---|---|
| Quizzes | 2 × 10 | 20 |
| Tests | 2 × 50 reduced to 40 | 40 |
| Experiential Learning | Case study 10 + Program-specific 10 + Video seminar 10 + Design & Modeling 10 | 40 |
| **— Theory CIE subtotal** | | **100** |
| Lab | Lab exercises / report / observation / analysis 20 + Lab test 10 + Innovative experiment / concept design & implementation 20 | 50 |
| **CIE total** | | **150** |

**SEE (150) = Theory SEE 100 + Lab SEE 50:**

| Exam | Contents | Marks |
|---|---|---|
| Theory SEE | Part A 20 + Part B 80 | 100 |
| Lab SEE | Write-up 10 + Conduction of experiments 20 + Viva 20 | 50 |
| **SEE total** | | **150** |

### 3.3 Practical / project / skill subject — CIE 50, SEE 50

Two common forms:

**(a) Lab / practical course:**

| | Component | Marks |
|---|---|---|
| CIE | Quizzes (2 × 5) 10 + Tests (2 × 25 reduced to 20) 20 + Experiential Learning 20 | 50 |
| SEE | Write-up 10 + Conduction 20 + Viva 20 | 50 |

**(b) Project / design-thinking course (phase-based):**

| | Component | Marks |
|---|---|---|
| CIE | Phase I (Empathy, Ideate) 10 + Phase II (Design) 15 + Phase III (Prototype + Digital Poster + Report) 25 | 50 |
| SEE | Synopsis write-up 5 + Presentation 15 + Demonstration 20 + Viva 5 + Report 5 | 50 |

> Component splits inside CIE vary by subject (some use MATLAB 20, some average the two tests instead of reducing, etc.). The feature should treat **CIE components as configurable per subject**; the totals (50 / 100 / 150) and the condensation are the fixed parts.

---

## 4. Condensation (reduce to a common scale)

Regardless of whether CIE is out of 50, 100, or 150, and SEE out of 50, 100, or 150:

- **CIE → 50:**  `CIE_50 = CIE_obtained ÷ CIE_max × 50`
- **SEE → 50:**  `SEE_50 = SEE_obtained ÷ SEE_max × 50`
- **Final score (out of 100) = CIE_50 + SEE_50**, rounded to the nearest whole number.

CIE and SEE each carry **50% weightage** — that's the whole point of condensing both to 50.

---

## 5. Pass / fail gates

A student must clear **all** of these. Failing any one means the subject grade is **F (grade point 0)**, no matter how high the total:

1. **≥ 40% in CIE.**
2. **≥ 40% in SEE.**
3. **≥ 40% aggregate** (this is exactly the P floor — score must reach 40/100).

> **To confirm:** the "minimum 24/60 in CIE" rule. 24/60 = 40%, which matches gate (1) applied to the CIE total — but verify whether it's 40% of the full CIE or a threshold on the test component only. It's a per-subject parameter either way.
>
> **To confirm (theory + practice subjects):** whether the 40% gate is checked on the *combined* CIE/SEE, or separately on the theory part and the lab part. This matters for subjects like IoT — a student could pass theory but fail the lab.

---

## 6. Grade point → SGPA → CGPA

- **Per subject:** final score → grade → grade point (§2).
- **SGPA (one semester)** = Σ (grade point × credits) ÷ Σ credits.
- **CGPA (all semesters)** = same formula across every subject taken so far.
- Audit courses (0 credits) are excluded from SGPA/CGPA.

---

## 7. CO attainment output (per student, per exam)

Each question is tagged with a course outcome (CO). Group marks by CO → obtained / max + %. Every CO in the paper appears.

Example output for one CIE-2 (IoT, illustrative CO distribution out of 60):

```
Total: 43 / 60  (71.7%)
CO1:  7 / 10   (70.0%)
CO2: 18 / 25   (72.0%)
CO3: 11 / 15   (73.3%)
CO4:  3 / 5    (60.0%)
CO5:  4 / 5    (80.0%)
```

This is the **direct** measure that feeds the college's CO→PO attainment (80% direct + 20% indirect).

---

## 8. Sample subject as data — IoT and Embedded Computing (CS344AI)

| Field | Value |
|---|---|
| Course code | CS344AI |
| Category | Professional Core — Theory & Practice |
| L:T:P | 3:0:1 → **4 credits** |
| CIE | 100 + 50 = **150** |
| SEE | 100 + 50 = **150** |
| Course outcomes | CO1–CO5 |

**CIE structure (150):**

| Part | Component | Max |
|---|---|---|
| Theory | Quizzes (2 × 10) | 20 |
| Theory | Tests (2 × 50 → reduced to 40) | 40 |
| Theory | Experiential Learning (case study 10 + program 10 + video seminar 10 + design & modeling 10) | 40 |
| Lab | Lab exercises/report/observation/analysis 20 + Lab test 10 + Innovative experiment 20 | 50 |
| | **Total** | **150** |

**SEE structure (150):**

| Exam | Component | Max |
|---|---|---|
| Theory SEE | Part A (objective) 20 + Part B (Unit 1 compulsory + Units 2–5 internal choice, 16 each) 80 | 100 |
| Lab SEE | Write-up 10 + Conduction 20 + Viva 20 | 50 |
| | **Total** | **150** |

### Worked example — one student in IoT

**CIE marks:**

| Component | Obtained / Max |
|---|---|
| Quizzes | 16 / 20 |
| Tests | 32 / 40 |
| Experiential Learning | 35 / 40 |
| Lab | 42 / 50 |
| **CIE total** | **125 / 150** |

**SEE marks:**

| Component | Obtained / Max |
|---|---|
| Theory SEE | 70 / 100 |
| Lab SEE | 40 / 50 |
| **SEE total** | **110 / 150** |

**Condensation & grade:**

- CIE_50 = 125 ÷ 150 × 50 = **41.67**
- SEE_50 = 110 ÷ 150 × 50 = **36.67**
- Final = 41.67 + 36.67 = 78.33 → **78**
- Gates: CIE 83.3% ✓ · SEE 73.3% ✓ · aggregate 78 ✓
- **Score 78 → Grade A → Grade Point 8** ✅

**Fail-by-gate example (same subject):** a student with CIE 130/150 (86.7%) but SEE 50/150 (**33.3%**) lands at a final score of 60 — which would be B+ — but the **SEE < 40% gate fails**, so the result is **F, grade point 0**. This is the case the gates exist to catch.

---

## 9. Other subjects in the semester (data)

| Course | Code | Category | Credits | CIE | SEE |
|---|---|---|---|---|---|
| Discrete Mathematical Structures | CS241AT | Theory | 3 | 100 | 100 |
| Design and Analysis of Algorithms | CD343AI | Theory & Practice | 4 | 150 | 150 |
| IoT and Embedded Computing | CS344AI | Theory & Practice | 4 | 150 | 150 |
| Computer Networks | CY245AT | Theory | 3 | 100 | 100 |
| Professional Elective (Group B) | CS246TX | NPTEL | 2 | 50 | 50 |
| Ability Enhancement (Group C) | HS247LX | Practice | 2 | 50 | 50 |
| Universal Human Values | HS248AT | Theory | 2 | 50 | 50 |
| Bridge Course: Mathematics | MAT149AT | Audit | 0 | 50 | — |

**SGPA worked example** (sample grade points for the semester):

| Subject | Credits | Grade | GP | GP × Credits |
|---|---|---|---|---|
| Discrete Math | 3 | A+ | 9 | 27 |
| DAA | 4 | A | 8 | 32 |
| IoT & Embedded | 4 | A | 8 | 32 |
| Computer Networks | 3 | B+ | 7 | 21 |
| Professional Elective | 2 | A+ | 9 | 18 |
| Ability Enhancement | 2 | O | 10 | 20 |
| Universal Human Values | 2 | A | 8 | 16 |
| **Total** | **20** | | | **166** |

SGPA = 166 ÷ 20 = **8.3** (Bridge Course excluded — audit, 0 credits).

---

## 10. Open items to confirm

1. **"24/60" CIE minimum** — confirm it means 40% of the CIE total (vs. a threshold on the test component only).
2. **Theory + Practice gates** — is the 40% pass requirement on combined CIE/SEE, or separately on the theory and lab parts?
3. **Rounding** — final score rounded to nearest whole number assumed (e.g. 78.33 → 78, 78.5 → 79). Confirm if a different rounding is used.
4. **CIE component splits** are configurable per subject; the totals (50/100/150) and condensation are fixed.
