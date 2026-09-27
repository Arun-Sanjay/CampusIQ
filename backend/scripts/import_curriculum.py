"""Regenerate `app/services/dsa_curriculum.json` from the source spreadsheet.

The app reads the JSON at runtime (no spreadsheet dependency). Re-run this only
when the curriculum sheet changes. Dev-only — needs `openpyxl` (requirements-dev).

Usage (from backend/):
    .venv/bin/python scripts/import_curriculum.py /path/to/dsa_curriculum.xlsx

The sheet must have a 'Patterns' sheet (Track, Tier, #, Pattern, Core Idea,
Recognize When, # Problems, Difficulty Span, Premium) and a 'Problems' sheet
(#, Track, Tier, Pattern, Seq, LC #, Problem, Difficulty, Priority, Premium,
Free Alternative, Also Appears In, LeetCode Link). Problems are deduped by
LeetCode slug, keeping the first (primary) pattern occurrence.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required: .venv/bin/pip install openpyxl")

DEST = Path(__file__).resolve().parent.parent / "app" / "services" / "dsa_curriculum.json"


def _slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).strip().lower())).strip("-")


def _url_slug(url: str) -> str | None:
    m = re.search(r"/problems/([^/?#]+)", str(url or ""))
    return m.group(1) if m else None


def _norm_track(t: str) -> str:
    return "advanced" if "advanced" in str(t).lower() else "core"


def _rows(wb, name: str) -> list[dict]:
    data = list(wb[name].iter_rows(values_only=True))
    hdr = [str(h).strip() if h is not None else "" for h in data[0]]
    return [dict(zip(hdr, r)) for r in data[1:] if any(c is not None for c in r)]


def main(xlsx_path: str) -> None:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    pats_raw = _rows(wb, "Patterns")
    probs_raw = _rows(wb, "Problems")

    patterns: list[dict] = []
    pat_slug_by_name: dict[str, str] = {}
    for p in pats_raw:
        name = str(p["Pattern"]).strip()
        pslug = _slugify(name)
        pat_slug_by_name[name] = pslug
        patterns.append(
            {
                "slug": pslug,
                "name": name,
                "track": _norm_track(p["Track"]),
                "tier": int(p["Tier"]),
                "order_num": int(p["#"]),
                "core_idea": str(p["Core Idea"]).strip(),
                "recognize_when": str(p["Recognize When"]).strip(),
                "difficulty_span": str(p["Difficulty Span"]).strip(),
                "problem_count": 0,  # recomputed after dedup
            }
        )

    seen: set[str] = set()
    problems: list[dict] = []
    for q in probs_raw:
        s = _url_slug(q["LeetCode Link"])
        if not s or s in seen:
            continue
        seen.add(s)
        pname = str(q["Pattern"]).strip()
        problems.append(
            {
                "slug": s,
                "lc_number": int(q["LC #"]) if q.get("LC #") is not None else None,
                "title": str(q["Problem"]).strip(),
                "pattern_slug": pat_slug_by_name[pname],
                "track": _norm_track(q["Track"]),
                "tier": int(q["Tier"]),
                "seq": int(q["Seq"]) if q.get("Seq") is not None else 0,
                "difficulty": str(q["Difficulty"]).strip().lower(),
                "priority": str(q["Priority"]).strip().lower() if q.get("Priority") else "medium",
                "is_premium": str(q.get("Premium") or "").strip().lower() == "premium",
                "free_alternative": (str(q["Free Alternative"]).strip() or None) if q.get("Free Alternative") else None,
                "also_appears_in": (str(q["Also Appears In"]).strip() or None) if q.get("Also Appears In") else None,
                "leetcode_url": str(q["LeetCode Link"]).strip(),
            }
        )

    counts = collections.Counter(p["pattern_slug"] for p in problems)
    for pat in patterns:
        pat["problem_count"] = counts.get(pat["slug"], 0)

    out = {
        "generated_from": Path(xlsx_path).name,
        "pattern_count": len(patterns),
        "problem_count": len(problems),
        "patterns": patterns,
        "problems": problems,
    }
    DEST.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {DEST} — {len(patterns)} patterns, {len(problems)} problems (deduped).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/import_curriculum.py <dsa_curriculum.xlsx>")
    main(sys.argv[1])
