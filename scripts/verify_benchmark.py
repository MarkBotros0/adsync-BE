"""Verify our derived-metrics functions against the marketing-expert benchmark workbook.

Workbook: ``Test Database Cleaned - Michel Magdy.xlsx`` (project root).
Sheet: ``Content`` — one row per post across Facebook / Instagram / Twitter / LinkedIn /
YouTube with the expected interactions, /1k-follower, grade, and engagement-rate columns.

Run from project root:
    python ad-sync-py/scripts/verify_benchmark.py

Exits non-zero if any post's computed value diverges from the workbook beyond the
tolerance. Reports per-column pass/fail counts so you can see where the math drifts.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# Make the app package importable when run from project root or scripts dir.
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

import openpyxl  # noqa: E402

from app.services.analytics.derived import (  # noqa: E402
    engagement_rate,
    grade_posts,
    interactions_per_1k_followers,
    total_interactions,
    weighted_score,
)


WORKBOOK_PATH = HERE.parents[2] / "Test Database Cleaned - Michel Magdy.xlsx"
SHEET = "Content"

# Tolerances per column. /1k followers is fractional; ER is fractional; counts must be exact.
TOL_INT = 0          # exact match required
TOL_FRACTION = 0.01  # 1% relative tolerance for floats


# Workbook column indices (verified by inspecting the header row).
COL = {
    "platform": 5,
    "followers": 3,
    "total_interactions": 14,
    "interactions_per_1k": 16,
    "grade": 17,
    "total_reactions": 26,
    "total_comments": 28,
    "total_shares": 31,
    "saves": 36,
    "total_reach": 49,
    "reach_engagement_rate": 56,
    "total_likes": 60,
    "engagements": 37,  # wider than interactions — includes clicks, post consumers, etc.
}


def _is_close(a: float | None, b: float | None, tol: float) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if b == 0:
        return abs(a) <= tol
    return abs(a - b) / max(abs(b), 1e-9) <= tol


def _to_post(row: tuple) -> dict | None:
    """Coerce a raw spreadsheet row into the dict shape our derived functions expect."""
    platform = row[COL["platform"]]
    if not platform:
        return None
    likes = row[COL["total_likes"]] or 0
    comments = row[COL["total_comments"]] or 0
    shares = row[COL["total_shares"]] or 0
    saves = row[COL["saves"]] or 0
    reach = row[COL["total_reach"]] or 0
    followers = row[COL["followers"]] or 0
    engagements = row[COL["engagements"]] or 0
    return {
        "platform": platform,
        "likes": int(likes),
        "comments": int(comments),
        "shares": int(shares),
        "saves": int(saves),
        "reach": int(reach),
        "followers": int(followers),
        "engagements": int(engagements),
        # Expected columns we're verifying against:
        "_expected_total_interactions": row[COL["total_interactions"]],
        "_expected_per_1k": row[COL["interactions_per_1k"]],
        "_expected_grade": row[COL["grade"]],
        "_expected_reach_er": row[COL["reach_engagement_rate"]],
    }


def _compare(label: str, ok: int, fail: int, fail_examples: list[str]) -> None:
    total = ok + fail
    pct = (ok / total) * 100 if total else 0
    print(f"  {label:30s}  {ok:4d}/{total:4d} pass ({pct:5.1f}%)")
    for ex in fail_examples[:3]:
        print(f"    FAIL: {ex}")


def main() -> int:
    if not WORKBOOK_PATH.exists():
        print(f"Workbook not found: {WORKBOOK_PATH}", file=sys.stderr)
        return 2

    wb = openpyxl.load_workbook(WORKBOOK_PATH, data_only=True)
    ws = wb[SHEET]

    posts: list[dict] = []
    for raw in ws.iter_rows(values_only=True, min_row=2):
        post = _to_post(raw)
        if post:
            posts.append(post)
    print(f"Loaded {len(posts)} posts from {SHEET!r}")

    # Grade with the A+ variant — matches the workbook's grading scale.
    grade_posts(posts, use_a_plus=True)

    counters = {k: [0, 0, []] for k in (
        "total_interactions", "interactions_per_1k", "reach_engagement_rate", "grade",
    )}

    for p in posts:
        # 1. Total interactions
        ours = total_interactions(p)
        expected = p["_expected_total_interactions"]
        if expected is not None:
            ok = ours == int(expected)
            counters["total_interactions"][0 if ok else 1] += 1
            if not ok:
                counters["total_interactions"][2].append(
                    f"{p['platform']}: ours={ours}  workbook={expected}"
                )

        # 2. Interactions per 1,000 followers
        ours_p1k = interactions_per_1k_followers(ours, p["followers"])
        expected_p1k = p["_expected_per_1k"]
        if expected_p1k is not None:
            ok = _is_close(ours_p1k, float(expected_p1k), TOL_FRACTION)
            counters["interactions_per_1k"][0 if ok else 1] += 1
            if not ok:
                counters["interactions_per_1k"][2].append(
                    f"{p['platform']}: ours={ours_p1k}  workbook={expected_p1k}"
                )

        # 3. Reach engagement rate — workbook uses "Engagements" (wider than interactions:
        # includes clicks, post consumers, story interactions). Stored as raw fraction.
        ours_er = engagement_rate(p["engagements"], p["reach"])
        expected_er_pct = (
            float(p["_expected_reach_er"]) * 100
            if p["_expected_reach_er"] is not None else None
        )
        if expected_er_pct is not None:
            ok = _is_close(ours_er, expected_er_pct, TOL_FRACTION)
            counters["reach_engagement_rate"][0 if ok else 1] += 1
            if not ok:
                counters["reach_engagement_rate"][2].append(
                    f"{p['platform']}: ours={ours_er}%  workbook={expected_er_pct}%"
                )

        # 4. Grade — quartile-based ranks differ from the workbook's algorithm
        # because the workbook's exact score formula isn't in the cell, only the
        # final letter. We compare loosely: same letter family (A*=A, B/C/D unchanged).
        ours_grade = (p.get("grade") or "").rstrip("+")
        expected_grade = (str(p["_expected_grade"]) if p["_expected_grade"] else "").rstrip("+")
        if expected_grade:
            ok = ours_grade == expected_grade
            counters["grade"][0 if ok else 1] += 1
            if not ok:
                counters["grade"][2].append(
                    f"{p['platform']} score={p['score']}: ours={p['grade']}  workbook={p['_expected_grade']}"
                )

    print()
    print("Per-column verification:")
    fail_total = 0
    for label, (ok, fail, examples) in counters.items():
        _compare(label, ok, fail, examples)
        fail_total += fail

    print()
    print("Notes on expected divergence:")
    print(" - Grade comparison is best-effort: workbook uses an undocumented weighting; we")
    print("   use the spec formula (likes·1 + comments·2 + shares·3 + saves·5). Counts will")
    print("   differ for posts whose underlying weighting is different.")
    print(" - Reach ER: workbook uses Engagements (wider than interactions: includes clicks,")
    print("   post consumers, story interactions). Stored as a raw fraction; we return %.")
    print("   Implementation note: the spec said 'Total Engagements' — that maps to the")
    print("   Engagements column in the workbook, NOT total_interactions. The dashboard")
    print("   tile must use the Engagements value; total_interactions stays separate.")
    print(" - /1k followers tolerance is 1% to absorb rounding the workbook applies.")

    return 1 if fail_total > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
