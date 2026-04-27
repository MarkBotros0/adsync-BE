"""Derived analytics metrics — engagement rate, saves, share of voice, post grade.

These are the headline numbers marketers report to clients. They are NOT raw counts
returned by a platform API; they are pure functions of counts the platform already
gives us. Keeping them in one module guarantees every endpoint computes them the same
way, so the dashboard, the reports PDF, and the period-over-period helper never drift.

Spec source: this module implements the formulae the marketing expert handed us —
ERR (Engagement Rate per Reach), Interactions per 1,000 followers, post Grade A/B/C/D
based on a weighted score, and the top-of-page averages (avg engagements, avg likes,
avg reach, avg saves, avg shares, follower growth rate). The benchmark workbook
"Test Database Cleaned - Michel Magdy.xlsx" should reproduce identical numbers when
fed into these functions — see verification step in the plan file.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any


# ── Engagement rate (per reach — the marketing-expert's ERR) ────────────────

def engagement_rate(interactions: int | float, reach: int | float) -> float | None:
    """Engagement Rate per Reach (ERR) = (Total Engagements per Post / Reach per Post) × 100.

    This is the formula in the marketing-expert spec. Returns None when reach is zero
    (no defined ER). Capped at 100% to swallow the occasional API quirk where the
    interactions counter briefly exceeds the reach counter.
    """
    if not reach:
        return None
    er = (float(interactions) / float(reach)) * 100.0
    return round(min(er, 100.0), 2)


# Alias for clarity at the call-site.
err = engagement_rate


def engagement_rate_by_followers(interactions: int | float, followers: int | float) -> float | None:
    """Engagement Rate by Followers = interactions / followers × 100.

    Used when reach isn't available (e.g. TikTok). Returns None if followers is zero.
    """
    if not followers:
        return None
    return round((float(interactions) / float(followers)) * 100.0, 2)


# ── Total interactions (matches the Michel Magdy workbook column) ───────────

def total_interactions(post: dict[str, Any]) -> int:
    """Total Interactions = likes + comments + shares.

    Matches the "Total interactions" column in the Michel Magdy benchmark workbook —
    explicitly NOT the wider "Engagements" column (which also counts clicks, story
    interactions, post consumers, etc). The benchmark verification script asserts
    this equals the workbook value to the unit.
    """
    return (
        int(post.get("likes") or 0)
        + int(post.get("comments") or 0)
        + int(post.get("shares") or 0)
    )


# ── Interactions per 1,000 followers (marketing-expert spec #2) ─────────────

def interactions_per_1k_followers(
    interactions: int | float, total_followers: int | float
) -> float | None:
    """Interactions per 1,000 followers = (Total Interactions / Total Followers) × 1,000.

    The "size-normalised" engagement number the expert wants on the dashboard so
    accounts of different sizes can be compared apples-to-apples. Uses total
    interactions (likes+comments+shares), not the wider engagements field — this
    matches the workbook's column of the same name.
    """
    if not total_followers:
        return None
    return round((float(interactions) / float(total_followers)) * 1000.0, 6)


def aggregate_engagement_rate(mentions: Iterable[dict[str, Any]]) -> float | None:
    """Average ER across a list of mentions (each having `interactions` + `reach`).

    Uses the totals method (Σinteractions / Σreach) rather than a mean of per-post
    ERs — the totals method is what the platforms themselves report, and avoids one
    high-ER tiny-reach post skewing the brand average.
    """
    total_int = 0
    total_reach = 0
    for m in mentions:
        total_int += int(m.get("interactions") or 0)
        total_reach += int(m.get("reach") or 0)
    return engagement_rate(total_int, total_reach)


# ── Saves (Instagram / TikTok algorithmic signal) ────────────────────────────

def total_saves(mentions: Iterable[dict[str, Any]]) -> int:
    """Sum saves across mentions. Field key follows Meta's convention: ``saves``.

    Falls back to ``saved`` (IG insights field name) when the unified ``saves`` key
    isn't populated, so this works against both transformed mention rows and raw
    insights payloads.
    """
    total = 0
    for m in mentions:
        v = m.get("saves")
        if v is None:
            v = m.get("saved")
        total += int(v or 0)
    return total


# ── Share of Voice ───────────────────────────────────────────────────────────

def share_of_voice(brand_mentions: int, competitor_mentions: Iterable[int]) -> float | None:
    """SoV = brand_mentions / (brand_mentions + Σ competitor_mentions) × 100.

    The classic listening-era definition: what % of all conversation about this
    competitive set is about us. Returns None if there is literally zero conversation
    in the set (no SoV is defined when the denominator is 0).
    """
    competitor_total = sum(int(c or 0) for c in competitor_mentions)
    denominator = int(brand_mentions or 0) + competitor_total
    if denominator == 0:
        return None
    return round((float(brand_mentions) / float(denominator)) * 100.0, 2)


def share_of_voice_breakdown(
    brand_name: str,
    brand_mentions: int,
    competitors: Iterable[tuple[str, int]],
) -> dict[str, Any]:
    """Full SoV table for the chart: name, mentions, share% per row, sorted desc.

    Args:
        brand_name: how to label the brand row.
        brand_mentions: brand's mention count in the window.
        competitors: iterable of ``(name, mention_count)`` for each competitor.

    Returns a dict with ``rows`` (sorted, each ``{name, mentions, share_pct}``) and
    ``total_mentions`` for convenience.
    """
    rows: list[dict[str, Any]] = [{"name": brand_name, "mentions": int(brand_mentions or 0), "is_brand": True}]
    for name, count in competitors:
        rows.append({"name": name, "mentions": int(count or 0), "is_brand": False})

    total = sum(r["mentions"] for r in rows)
    for r in rows:
        r["share_pct"] = round((r["mentions"] / total) * 100.0, 2) if total else None

    rows.sort(key=lambda r: r["mentions"], reverse=True)
    return {"rows": rows, "total_mentions": total}


# ── Post Grade (marketing-expert spec #3 — weighted score → A/B/C/D) ────────

# Weights from the spec. Saves are 5× a like because they are the strongest IG / TT
# algorithmic signal; comments and shares sit between them.
GRADE_WEIGHTS: dict[str, int] = {"likes": 1, "comments": 2, "shares": 3, "saves": 5}


def weighted_score(post: dict[str, Any]) -> int:
    """Per-post weighted score: (likes × 1) + (comments × 2) + (shares × 3) + (saves × 5).

    Looks up each component on the post dict, falling back to common alternative
    field names so this works against both transformed mention rows and raw insights
    payloads. ``saved`` (IG insights name) maps to ``saves``.
    """
    likes = int(post.get("likes") or 0)
    comments = int(post.get("comments") or 0)
    shares = int(post.get("shares") or 0)
    saves = int(post.get("saves") or post.get("saved") or 0)
    return (
        likes * GRADE_WEIGHTS["likes"]
        + comments * GRADE_WEIGHTS["comments"]
        + shares * GRADE_WEIGHTS["shares"]
        + saves * GRADE_WEIGHTS["saves"]
    )


def grade_posts(
    posts: list[dict[str, Any]],
    *,
    use_a_plus: bool = False,
) -> list[dict[str, Any]]:
    """Mutate each post in-place to add ``score`` + ``grade``, then return list.

    Default grading (matches the marketing-expert written spec): top 25% → A, 25–50% → B,
    50–75% → C, bottom 25% → D.

    With ``use_a_plus=True`` (matches the Michel Magdy benchmark workbook): top 10% →
    A+, next 15% → A, then B/C/D as above. The workbook uses A+ for outlier posts.

    Scoring requires a population so a single post in isolation cannot be graded.
    """
    if not posts:
        return posts

    for p in posts:
        p["score"] = weighted_score(p)

    n = len(posts)
    if n < 2:
        for p in posts:
            p["grade"] = None
        return posts

    # Rank-based quartiles. Sort once, mark rank, restore original order via index.
    indexed = sorted(enumerate(posts), key=lambda t: t[1]["score"], reverse=True)
    for rank_pos, (_orig_idx, post) in enumerate(indexed):
        if use_a_plus:
            if rank_pos < n * 0.10:
                post["grade"] = "A+"
            elif rank_pos < n * 0.25:
                post["grade"] = "A"
            elif rank_pos < n * 0.50:
                post["grade"] = "B"
            elif rank_pos < n * 0.75:
                post["grade"] = "C"
            else:
                post["grade"] = "D"
        else:
            if rank_pos < n * 0.25:
                post["grade"] = "A"
            elif rank_pos < n * 0.50:
                post["grade"] = "B"
            elif rank_pos < n * 0.75:
                post["grade"] = "C"
            else:
                post["grade"] = "D"
    return posts


def grade_distribution(posts: list[dict[str, Any]]) -> dict[str, int]:
    """Count how many posts fell into each grade — drives the A/B/C/D bar chart."""
    out = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    for p in posts:
        g = p.get("grade")
        if g in out:
            out[g] += 1
    return out


# ── Top-of-page averages (marketing-expert spec, "Top of the page" section) ─

def avg(values: Iterable[int | float]) -> float:
    """Mean of a sequence; 0.0 for an empty sequence."""
    vals = [float(v or 0) for v in values]
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 2)


def top_of_page_kpis(
    posts: list[dict[str, Any]],
    *,
    follower_count_start: int | None = None,
    follower_count_end: int | None = None,
) -> dict[str, Any]:
    """Compute the six top-of-page KPI tiles from the marketing-expert spec.

    1. Followers growth rate over the filtered window
    2. Avg total engagements per post
    3. Avg interactions (likes) per post
    4. Avg reach per post
    5. Avg saves per post
    6. Avg shares per post

    ``posts`` is the list of mention/post dicts in the window. Follower counts are
    optional — if absent, growth rate is ``None`` (the FE renders "—" rather than 0%).
    """
    likes = [p.get("likes") or p.get("interactions") or 0 for p in posts]
    reach = [p.get("reach") or 0 for p in posts]
    saves = [p.get("saves") or p.get("saved") or 0 for p in posts]
    shares = [p.get("shares") or 0 for p in posts]
    total_engagements = [
        int(p.get("likes") or 0)
        + int(p.get("comments") or 0)
        + int(p.get("shares") or 0)
        + int(p.get("saves") or p.get("saved") or 0)
        for p in posts
    ]

    growth_rate: float | None = None
    if follower_count_start is not None and follower_count_end is not None and follower_count_start:
        growth_rate = round(
            ((follower_count_end - follower_count_start) / follower_count_start) * 100.0, 2
        )

    return {
        "followers_growth_rate_pct": growth_rate,
        "avg_total_engagements_per_post": avg(total_engagements),
        "avg_likes_per_post": avg(likes),
        "avg_reach_per_post": avg(reach),
        "avg_saves_per_post": avg(saves),
        "avg_shares_per_post": avg(shares),
    }


# ── KPI tile builder ─────────────────────────────────────────────────────────

def build_kpi_tile(label: str, value: float | int | None, delta_pct: float | None, unit: str = "") -> dict[str, Any]:
    """Shape a single KPI tile for the dashboard.

    Centralised so every tile renders with the same fields; the FE can rely on
    {label, value, delta_pct, unit, direction} being present.
    """
    direction: str | None
    if delta_pct is None:
        direction = None
    elif delta_pct > 0:
        direction = "up"
    elif delta_pct < 0:
        direction = "down"
    else:
        direction = "flat"

    return {
        "label": label,
        "value": value,
        "unit": unit,
        "delta_pct": delta_pct,
        "direction": direction,
    }
