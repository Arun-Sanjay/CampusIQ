#!/usr/bin/env python
"""CampusIQ evaluation suite — real, measured numbers for the report.

Three evals, all against the ACTUAL pipelines (Haiku in dev — never Opus):

1. RAG faithfulness  — reconstructs the production Note-Assistant tutor (real
   retrieval + real system prompt + Claude) over auto-generated, corpus-grounded
   questions, then LLM-judges whether each answer is faithful/grounded → a single
   accuracy %.
2. Grading agreement — renders a few answer sheets, runs the REAL Claude-vision
   grader (same GRADING_SYSTEM prompt the app uses), and compares the AI's marks
   to a human ground-truth rubric → agreement %.
3. Latency          — tutor reply time (time-to-first-token + full) and document
   ingestion time (extract → chunk → embed) on real corpus PDFs.

Run from backend/:  .venv/bin/python scripts/eval_suite.py
Reads an isolated copy of campusiq.db (never writes the dev DB).
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import statistics
import sys
import textwrap
import time
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

# Isolated copy of the dev DB so the corpus (docs + chunks + embeddings) is
# available without touching the live DB.
SRC_DB = BACKEND / "campusiq.db"
EVAL_DB = BACKEND / "_eval_campusiq.db"
if SRC_DB.exists():
    shutil.copyfile(SRC_DB, EVAL_DB)
    os.environ["DATABASE_URL"] = f"sqlite:///{EVAL_DB}"
os.environ.setdefault("SEED_DSA_CURRICULUM", "false")
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services import chunking, claude_client, embeddings, text_extraction, vector_search  # noqa: E402
from app.services.ai_chat import _format_chunks_as_context, _select_note_assistant_system_prompt  # noqa: E402
from app.services.answersheet_grader import GRADING_SYSTEM, _strip_json  # noqa: E402

RAG_N = int(os.environ.get("EVAL_RAG_N", "20"))   # questions for the faithfulness eval
TOP_K = 5

settings = get_settings()


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _stats(xs: list[float]) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    s = sorted(xs)
    return {
        "n": len(xs),
        "mean": round(statistics.mean(xs), 2),
        "median": round(statistics.median(xs), 2),
        "p90": round(s[min(len(s) - 1, int(0.9 * len(s)))], 2),
        "min": round(min(xs), 2),
        "max": round(max(xs), 2),
    }


# ════════════════════════════════════════════════════════════════
# 1. RAG faithfulness
# ════════════════════════════════════════════════════════════════

QGEN_SYSTEM = (
    "You write ONE specific exam-style study question a student would ask, "
    "answerable SOLELY from the given course-notes excerpt. Make it self-contained "
    "(name the topic; never say 'the excerpt'/'the passage'). Return ONLY the question."
)

JUDGE_SYSTEM = (
    "You are a strict evaluator of an AI tutor's groundedness (faithfulness). "
    "Given a QUESTION, the COURSE MATERIAL the tutor was shown, and the tutor's ANSWER, "
    "decide whether the answer is FAITHFUL: every specific factual claim is supported by, "
    "or directly inferable from, the COURSE MATERIAL, and nothing contradicts it. "
    "Correct, generic phrasing/elaboration that adds no unsupported specifics is fine. "
    "If the material doesn't contain the answer and the tutor says so, that is FAITHFUL. "
    "Mark UNFAITHFUL only if the answer asserts specific facts not supported by the "
    "material, or contradicts it.\n"
    'Return STRICT JSON only: {"faithful": true|false, "reason": "<one short sentence>"}'
)


def _sample_chunks(db) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT c.id AS cid, c.chunk_text AS txt, d.file_name AS fname
            FROM document_chunks c JOIN documents d ON d.id = c.document_id
            WHERE length(c.chunk_text) > 280
            ORDER BY c.document_id, c.chunk_index
            """
        )
    ).mappings().all()
    if not rows:
        return []
    # Even spread across the ordered set for topic diversity.
    step = max(1, len(rows) // RAG_N)
    picked = rows[::step][:RAG_N]
    return [dict(r) for r in picked]


def _admin_user(db) -> User:
    u = db.scalars(select(User).where(User.role == UserRole.ADMIN)).first()
    if u is not None:
        return u
    # Transient admin — search_chunks only reads .role/.id for admins (sees all).
    t = User()
    t.id = uuid.uuid4()
    t.role = UserRole.ADMIN
    return t


def _parse_json(raw: str) -> dict | None:
    try:
        return json.loads(_strip_json(raw))
    except Exception:
        return None


def eval_rag(db) -> dict:
    print("\n[1/3] RAG faithfulness — generating grounded questions…", flush=True)
    user = _admin_user(db)
    chunks = _sample_chunks(db)
    if not chunks:
        return {"error": "no document chunks in corpus"}

    records = []
    reply_ttft, reply_total, retrieval_ms = [], [], []
    faithful = unfaithful = errored = recall_hits = 0

    for i, ch in enumerate(chunks, 1):
        q = claude_client.generate_completion(
            system=QGEN_SYSTEM, user_message=f"EXCERPT:\n{ch['txt'][:1300]}",
            max_tokens=120, temperature=0.4,
        ).strip().strip('"')
        if not q:
            errored += 1
            continue

        t0 = time.perf_counter()
        hits = vector_search.search_chunks(db, q, user, top_k=TOP_K)
        retrieval_ms.append((time.perf_counter() - t0) * 1000)
        context = _format_chunks_as_context(hits)
        _norm = lambda x: str(x).replace("-", "").lower()  # noqa: E731
        if _norm(ch["cid"]) in {_norm(h.chunk_id) for h in hits}:
            recall_hits += 1

        base_prompt, max_tokens = _select_note_assistant_system_prompt(None)
        system = (
            f"{base_prompt}\n\n"
            "=== RELEVANT MATERIAL FROM THE STUDENT'S COURSE DOCUMENTS ===\n\n"
            f"{context}\n\n=== END OF MATERIAL ==="
        )

        # Stream the tutor reply (real production path) + time it.
        t0 = time.perf_counter()
        first = None
        parts: list[str] = []
        for delta in claude_client.stream_completion(
            system=system, messages=[{"role": "user", "content": q}],
            max_tokens=max_tokens, temperature=0.4,
        ):
            if first is None:
                first = time.perf_counter()
            parts.append(delta)
        end = time.perf_counter()
        answer = "".join(parts).strip()
        if not answer:
            errored += 1
            continue
        reply_ttft.append((first - t0) if first else None)
        reply_total.append(end - t0)

        verdict = _parse_json(
            claude_client.generate_completion(
                system=JUDGE_SYSTEM,
                user_message=f"QUESTION:\n{q}\n\nCOURSE MATERIAL:\n{context}\n\nANSWER:\n{answer}",
                max_tokens=200, temperature=0.0,
            )
        ) or {}
        is_faithful = bool(verdict.get("faithful"))
        faithful += int(is_faithful)
        unfaithful += int(not is_faithful)
        records.append({
            "q": q, "doc": ch["fname"], "faithful": is_faithful,
            "reason": verdict.get("reason", ""), "answer_chars": len(answer),
            "retrieved": [str(h.chunk_id) for h in hits],
        })
        print(f"  {i:>2}/{len(chunks)}  faithful={is_faithful}  ({ch['fname']})", flush=True)

    scored = faithful + unfaithful
    return {
        "questions": len(chunks),
        "scored": scored,
        "errored": errored,
        "faithfulness_accuracy_pct": _pct(faithful, scored),
        "faithful": faithful,
        "unfaithful": unfaithful,
        "retrieval_recall_at_5_pct": _pct(recall_hits, len(chunks)),
        "mean_answer_chars": round(statistics.mean([r["answer_chars"] for r in records]), 0) if records else 0,
        "latency_reply_ttft_s": _stats(reply_ttft),
        "latency_reply_total_s": _stats(reply_total),
        "latency_retrieval_ms": _stats(retrieval_ms),
        "unfaithful_examples": [
            {"q": r["q"], "reason": r["reason"]} for r in records if not r["faithful"]
        ][:5],
    }


# ════════════════════════════════════════════════════════════════
# 2. Grading agreement (real Claude-vision grader vs human rubric)
# ════════════════════════════════════════════════════════════════

SCHEME = [
    {"label": "1", "co": "CO1", "max_marks": 4,
     "question": "Differentiate between a microprocessor and a microcontroller (any two points).",
     "model_answer": "Microprocessor: only a CPU, needs external RAM/ROM/peripherals, general-purpose (e.g. 8086). Microcontroller: CPU+RAM+ROM+peripherals on a single chip, application-specific (e.g. 8051)."},
    {"label": "2", "co": "CO2", "max_marks": 3,
     "question": "What is the function of the IODIR register in LPC2148 GPIO?",
     "model_answer": "It sets the direction of each GPIO pin: 0 = input, 1 = output."},
    {"label": "3", "co": "CO2", "max_marks": 4,
     "question": "State the time complexity of binary search and explain why.",
     "model_answer": "O(log n) because each comparison halves the remaining search space."},
    {"label": "4", "co": "CO3", "max_marks": 3,
     "question": "What is the Thumb instruction set in ARM and give one advantage.",
     "model_answer": "A 16-bit compressed subset of the ARM instruction set; advantage: higher code density / less memory use."},
    {"label": "5", "co": "CO1", "max_marks": 4,
     "question": "Write the formula for nCr and compute 5C2.",
     "model_answer": "nCr = n! / (r!(n-r)!); 5C2 = 10."},
    {"label": "6", "co": "CO4", "max_marks": 4,
     "question": "List two characteristics of an embedded system.",
     "model_answer": "Any two of: application-specific, real-time response, resource-constrained, high reliability, low power."},
]

# Each student: answers per label + the marks a fair human grader would award
# (ground truth). Mix of full / partial / wrong / blank.
STUDENTS = [
    {"usn": "1RV23CS001", "name": "Aarav Kumar",
     "answers": {
        "1": "Microprocessor has only the CPU and needs external memory and peripherals, while a microcontroller has CPU, RAM, ROM and I/O on one chip. Microprocessor is general purpose, microcontroller is application specific.",
        "2": "IODIR sets whether a pin is input or output. 0 means input and 1 means output.",
        "3": "Binary search is O(log n) because we divide the array in half each step.",
        "4": "Thumb is a 16-bit instruction set in ARM. It gives better code density.",
        "5": "nCr = n!/(r!(n-r)!). 5C2 = 10.",
        "6": "It is application specific and works in real time.",
     },
     "truth": {"1": 4, "2": 3, "3": 4, "4": 3, "5": 4, "6": 4}},
    {"usn": "1RV23CS002", "name": "Diya Sharma",
     "answers": {
        "1": "Microcontroller is a small computer on a single chip.",
        "2": "It is a register in the GPIO.",
        "3": "O(log n).",
        "4": "Thumb is used in ARM processors for 16 bit instructions.",
        "5": "5C2 = 20.",
        "6": "Embedded systems are cheap and small.",
     },
     "truth": {"1": 1, "2": 1, "3": 2, "4": 2, "5": 1, "6": 2}},
    {"usn": "1RV23CS003", "name": "Rohan Mehta",
     "answers": {
        "1": "Microprocessor: CPU only, external memory, general purpose. Microcontroller: all on chip, specific use.",
        "2": "Sets pin direction, 1 = output, 0 = input.",
        "3": "It is O(n) because we may check every element.",
        "4": "",
        "5": "nCr = n!/(r!(n-r)!) = 10 for 5C2.",
        "6": "Real-time and resource constrained.",
     },
     "truth": {"1": 4, "2": 3, "3": 0, "4": 0, "5": 4, "6": 4}},
    {"usn": "1RV23CS004", "name": "Sara Iyer",
     "answers": {
        "1": "Both are processors used in computers.",
        "2": "IODIR controls the direction of GPIO pins (input/output).",
        "3": "Binary search has O(log n) time because the list is sorted and halved each comparison.",
        "4": "Thumb is a compressed 16-bit subset of ARM instructions; it reduces memory usage.",
        "5": "The combination formula is n!/(r!(n-r)!).",
        "6": "",
     },
     "truth": {"1": 1, "2": 3, "3": 4, "4": 3, "5": 2, "6": 0}},
    {"usn": "1RV23CS005", "name": "Karan Nair",
     "answers": {
        "1": "Microprocessor needs external RAM/ROM; microcontroller has memory and peripherals integrated on one chip.",
        "2": "input output direction register",
        "3": "O(log n) since search space halves; binary search needs sorted data.",
        "4": "16-bit ARM instruction set.",
        "5": "5C2 = 10 using n!/(r!(n-r)!).",
        "6": "Application specific, real time, low power.",
     },
     "truth": {"1": 4, "2": 2, "3": 4, "4": 2, "5": 4, "6": 4}},
]


def _render_sheet_png(student: dict) -> bytes:
    import fitz  # PyMuPDF, already a dependency

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    y = 48
    page.insert_text((48, y), f"USN: {student['usn']}    Name: {student['name']}", fontsize=12)
    y += 16
    page.insert_text((48, y), "Answer Script — Embedded Systems & DSA", fontsize=10)
    y += 26
    for q in SCHEME:
        page.insert_text((48, y), f"Q{q['label']}) {q['question']}", fontsize=10)
        y += 16
        ans = student["answers"].get(q["label"], "").strip()
        if not ans:
            page.insert_text((62, y), "(left blank)", fontsize=10)
            y += 16
        else:
            for line in textwrap.wrap(ans, width=92):
                page.insert_text((62, y), line, fontsize=10)
                y += 14
        y += 12
    return page.get_pixmap(dpi=130).tobytes("png")


def _grading_prompt() -> str:
    scheme = [
        {"label": q["label"], "question": q["question"], "model_answer": q["model_answer"],
         "max_marks": float(q["max_marks"]), "co": q["co"]}
        for q in SCHEME
    ]
    return (
        "Leniency: Be balanced: reward correct concepts; minor omissions lose partial marks.\n"
        f"\nMARKING SCHEME (JSON):\n{json.dumps(scheme, ensure_ascii=False)}\n\n"
        "Grade the student's script (images below) and return the JSON described."
    )


def eval_grading() -> dict:
    print("\n[2/3] Grading agreement — running the real vision grader…", flush=True)
    prompt = _grading_prompt()
    max_by_label = {q["label"]: q["max_marks"] for q in SCHEME}
    pairs = []           # (ai, truth) per question
    sheet_rows = []
    out_dir = BACKEND / "uploads" / "_eval_grading"
    out_dir.mkdir(parents=True, exist_ok=True)
    students = STUDENTS[: int(os.environ.get("EVAL_GRADING_N", str(len(STUDENTS))))]

    for s in students:
        png = _render_sheet_png(s)
        (out_dir / f"{s['usn']}.png").write_bytes(png)
        raw = claude_client.generate_completion_vision(
            system=GRADING_SYSTEM, text=prompt, images=[png], max_tokens=4096, temperature=0.1,
        )
        data = _parse_json(raw) or {}
        ai = {str(a.get("label")): a for a in (data.get("answers") or [])}
        sheet_ai_total = sheet_truth_total = 0.0
        for q in SCHEME:
            lbl = q["label"]
            mx = max_by_label[lbl]
            try:
                ai_mark = max(0.0, min(mx, float(ai.get(lbl, {}).get("awarded_marks", 0))))
            except (TypeError, ValueError):
                ai_mark = 0.0
            truth = float(s["truth"][lbl])
            pairs.append((ai_mark, truth))
            sheet_ai_total += ai_mark
            sheet_truth_total += truth
        sheet_rows.append({
            "usn": s["usn"], "ai_total": round(sheet_ai_total, 1),
            "truth_total": round(sheet_truth_total, 1),
            "detected_usn": data.get("detected_usn"),
        })
        print(f"  {s['usn']}: AI={sheet_ai_total:.0f}  teacher={sheet_truth_total:.0f}  "
              f"(detected USN: {data.get('detected_usn')})", flush=True)

    n = len(pairs)
    exact = sum(1 for a, t in pairs if abs(a - t) < 0.01)
    within1 = sum(1 for a, t in pairs if abs(a - t) <= 1.0)
    mae = round(statistics.mean([abs(a - t) for a, t in pairs]), 2) if n else 0
    sheet_total_mae = round(
        statistics.mean([abs(r["ai_total"] - r["truth_total"]) for r in sheet_rows]), 2
    ) if sheet_rows else 0
    total_possible = sum(q["max_marks"] for q in SCHEME)
    return {
        "sheets": len(students),
        "questions_per_sheet": len(SCHEME),
        "graded_pairs": n,
        "exact_agreement_pct": _pct(exact, n),
        "within_1_mark_pct": _pct(within1, n),
        "mean_abs_error_marks": mae,
        "sheet_total_mae_marks": sheet_total_mae,
        "marks_per_sheet": total_possible,
        "sheet_breakdown": sheet_rows,
    }


# ════════════════════════════════════════════════════════════════
# 3. Document ingestion latency
# ════════════════════════════════════════════════════════════════

def eval_ingestion() -> dict:
    print("\n[3/3] Document ingestion latency…", flush=True)
    # Warm the embedding model so the one-time lazy load isn't counted.
    t0 = time.perf_counter()
    warm = embeddings.embed_text("warm up the sentence-transformers model")
    model_load_s = round(time.perf_counter() - t0, 2)
    if not warm:
        return {"error": "embedding model unavailable"}

    pdfs = sorted(glob.glob(str(BACKEND / "uploads" / "**" / "*.pdf"), recursive=True))
    pdfs = [p for p in pdfs if "_eval_grading" not in p][: int(os.environ.get("EVAL_ING_N", "5"))]
    rows = []
    for p in pdfs:
        try:
            t0 = time.perf_counter()
            txt = text_extraction.extract_text(p)
            t1 = time.perf_counter()
            chunks = chunking.split_into_chunks(txt)
            t2 = time.perf_counter()
            embeddings.embed_batch([c.text for c in chunks])
            t3 = time.perf_counter()
        except Exception as e:  # noqa: BLE001
            rows.append({"file": Path(p).name, "error": str(e)[:80]})
            continue
        rows.append({
            "file": Path(p).name,
            "chars": len(txt),
            "chunks": len(chunks),
            "extract_s": round(t1 - t0, 2),
            "chunk_s": round(t2 - t1, 3),
            "embed_s": round(t3 - t2, 2),
            "total_s": round(t3 - t0, 2),
        })
        print(f"  {Path(p).name}: {len(txt)} chars, {len(chunks)} chunks, total {round(t3 - t0, 2)}s", flush=True)

    ok = [r for r in rows if "total_s" in r]
    return {
        "embedding_model_cold_load_s": model_load_s,
        "docs": rows,
        "ingestion_total_s": _stats([r["total_s"] for r in ok]),
        "ingestion_per_1k_chars_s": round(
            statistics.mean([r["total_s"] / max(1, r["chars"] / 1000) for r in ok]), 3
        ) if ok else None,
    }


# ════════════════════════════════════════════════════════════════

def main() -> int:
    if not claude_client.is_available():
        print("ANTHROPIC_API_KEY not set — cannot run AI evals.", file=sys.stderr)
        return 1
    print(f"Model: {settings.active_anthropic_model}  (USE_PRODUCTION_MODEL={settings.use_production_model})")
    print(f"Embeddings available: {embeddings.is_available()}")

    db = SessionLocal()
    try:
        rag = eval_rag(db)
    finally:
        db.close()
    grading = eval_grading()
    ingestion = eval_ingestion()

    report = {
        "model": settings.active_anthropic_model,
        "rag_faithfulness": rag,
        "grading_agreement": grading,
        "ingestion_latency": ingestion,
    }
    (BACKEND / "eval_results.json").write_text(json.dumps(report, indent=2, default=str))

    print("\n" + "═" * 64)
    print("CAMPUSIQ EVALUATION RESULTS")
    print("═" * 64)
    print(f"Model: {settings.active_anthropic_model} (dev tier)\n")
    print("1) RAG — AI tutor faithfulness/groundedness")
    print(f"   • Faithfulness accuracy : {rag.get('faithfulness_accuracy_pct')}%  "
          f"({rag.get('faithful')}/{rag.get('scored')} answers grounded)")
    print(f"   • Retrieval recall@5    : {rag.get('retrieval_recall_at_5_pct')}%")
    print(f"   • Tutor reply (full)    : {rag.get('latency_reply_total_s', {}).get('mean')}s mean / "
          f"{rag.get('latency_reply_total_s', {}).get('median')}s median")
    print(f"   • Time-to-first-token   : {rag.get('latency_reply_ttft_s', {}).get('mean')}s mean")
    print("\n2) Grading — AI vs teacher (human rubric) agreement")
    print(f"   • Exact-mark agreement  : {grading.get('exact_agreement_pct')}%  "
          f"({grading.get('graded_pairs')} graded answers across {grading.get('sheets')} sheets)")
    print(f"   • Within ±1 mark        : {grading.get('within_1_mark_pct')}%")
    print(f"   • Mean abs error        : {grading.get('mean_abs_error_marks')} marks/question, "
          f"{grading.get('sheet_total_mae_marks')} marks/sheet (of {grading.get('marks_per_sheet')})")
    print("\n3) System latency")
    ing = ingestion.get("ingestion_total_s", {})
    print(f"   • Tutor reply           : {rag.get('latency_reply_total_s', {}).get('mean')}s mean "
          f"(TTFT {rag.get('latency_reply_ttft_s', {}).get('mean')}s)")
    print(f"   • Doc ingestion         : {ing.get('mean')}s mean / {ing.get('max')}s max "
          f"(extract+chunk+embed); embed model cold-load {ingestion.get('embedding_model_cold_load_s')}s")
    print("═" * 64)
    print("Full detail → backend/eval_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
