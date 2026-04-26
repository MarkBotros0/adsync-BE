"""Pandas-powered summary cards for the Meta Ads, Instagram, and TikTok tabs.

Each ``summarize_*`` function takes the stored normalized items + an optional
filter spec, applies the filters with pandas, and returns a JSON-friendly
summary dict. The frontend re-fetches this whenever filters change so the
summary cards stay in sync with the visible data set.
"""
from collections import Counter
from datetime import datetime
from math import isnan
from typing import Any

import numpy as np
import pandas as pd


# ── Public types (loose dicts on purpose — matches FE schema 1:1) ─────────────

MetaAdsFilters = dict[str, Any]
InstagramFilters = dict[str, Any]
TikTokFilters = dict[str, Any]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_dt(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce", utc=True)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if isnan(f):
        return None
    return f


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _count_value(series: pd.Series, top: int = 10) -> dict[str, int]:
    """value_counts → plain JSON-friendly dict, top N."""
    if series.empty:
        return {}
    counts = series.dropna().astype(str).value_counts().head(top)
    return {str(k): int(v) for k, v in counts.items()}


def _explode_count(series: pd.Series, top: int = 10) -> dict[str, int]:
    """Explode list-valued series and count occurrences."""
    if series.empty:
        return {}
    flat: list[str] = []
    for value in series.dropna():
        if isinstance(value, list):
            flat.extend(str(v) for v in value if v is not None)
        elif isinstance(value, str) and value:
            flat.append(value)
    if not flat:
        return {}
    counts = Counter(flat).most_common(top)
    return {k: int(v) for k, v in counts}


def _hhi(counts: dict[str, int]) -> float | None:
    """Herfindahl-Hirschman Index — concentration of a value distribution.
    1.0 = single dominant value, ~0 = perfectly distributed."""
    total = sum(counts.values())
    if total <= 0:
        return None
    shares = np.array([v / total for v in counts.values()])
    return float(np.sum(shares ** 2))


def _empty_summary(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {"total": 0, "filtered_total": 0}
    if extra:
        base.update(extra)
    return base


def _str_contains(series: pd.Series, needle: str) -> pd.Series:
    if not needle:
        return pd.Series([True] * len(series), index=series.index)
    return series.fillna("").astype(str).str.contains(needle, case=False, na=False, regex=False)


# ── 1. Meta Ads ───────────────────────────────────────────────────────────────

def _apply_meta_filters(df: pd.DataFrame, f: MetaAdsFilters | None) -> pd.DataFrame:
    if not f or df.empty:
        return df
    out = df

    status = (f.get("status") or "all").lower()
    if status == "active":
        out = out[out["is_active"].fillna(False).astype(bool)]
    elif status == "inactive":
        out = out[~out["is_active"].fillna(False).astype(bool)]

    if f.get("has_video"):
        out = out[out["has_video"]]

    if f.get("platform"):
        platform = str(f["platform"]).lower()
        out = out[out["platforms_lc"].apply(lambda lst: platform in lst)]

    if f.get("cta"):
        out = out[out["cta"].fillna("") == f["cta"]]

    if f.get("page_name"):
        out = out[_str_contains(out["page_name"], str(f["page_name"]))]

    if f.get("search"):
        out = out[_str_contains(out["body"], str(f["search"]))]

    return out


def summarize_meta_ads(
    items: list[dict[str, Any]] | None,
    filters: MetaAdsFilters | None = None,
) -> dict[str, Any]:
    if not items:
        return _empty_summary({
            "ads_active": 0,
            "ads_with_video": 0,
            "median_run_days": None,
            "p90_run_days": None,
            "ads_per_week": {},
            "platforms_breakdown": {},
            "regions_top": {},
            "cta_breakdown": {},
            "page_concentration": None,
            "top_pages": {},
        })

    df = pd.DataFrame(items)
    total_unfiltered = int(len(df))

    # Derived columns.
    df["is_active"] = df.get("is_active").fillna(False).astype(bool) if "is_active" in df.columns else False
    df["has_video"] = df.get("media", pd.Series([[]] * len(df))).apply(
        lambda m: any((isinstance(c, dict) and c.get("type") == "video") for c in (m or []))
    )
    df["platforms_lc"] = df.get("platforms", pd.Series([[]] * len(df))).apply(
        lambda lst: [str(x).lower() for x in (lst or [])]
    )

    df = _apply_meta_filters(df, filters)
    if df.empty:
        return _empty_summary({
            "total": total_unfiltered,
            "ads_active": 0,
            "ads_with_video": 0,
            "median_run_days": None,
            "p90_run_days": None,
            "ads_per_week": {},
            "platforms_breakdown": {},
            "regions_top": {},
            "cta_breakdown": {},
            "page_concentration": None,
            "top_pages": {},
        })

    # Run-day stats.
    start = _to_dt(df.get("start_date"))
    end = _to_dt(df.get("end_date"))
    end_filled = end.fillna(pd.Timestamp.utcnow())
    run_days = (end_filled - start).dt.total_seconds() / 86400.0
    run_days = run_days[run_days >= 0]

    # Weekly time-series of new-ad starts.
    weekly: dict[str, int] = {}
    if start.notna().any():
        starts = start.dropna().dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("W").dt.start_time
        weekly = {ts.strftime("%Y-%m-%d"): int(c) for ts, c in starts.value_counts().sort_index().items()}

    page_counts = _count_value(df.get("page_name", pd.Series(dtype=object)), top=20)

    return {
        "total": total_unfiltered,
        "filtered_total": int(len(df)),
        "ads_active": int(df["is_active"].sum()),
        "ads_with_video": int(df["has_video"].sum()),
        "median_run_days": _safe_float(run_days.median()) if not run_days.empty else None,
        "p90_run_days": _safe_float(run_days.quantile(0.9)) if not run_days.empty else None,
        "ads_per_week": weekly,
        "platforms_breakdown": _explode_count(df.get("platforms", pd.Series(dtype=object)), top=10),
        "regions_top": _explode_count(df.get("regions", pd.Series(dtype=object)), top=10),
        "cta_breakdown": _count_value(df.get("cta", pd.Series(dtype=object)), top=10),
        "page_concentration": _hhi(page_counts),
        "top_pages": dict(list(page_counts.items())[:10]),
    }


# ── 2. Instagram (profiles + posts) ──────────────────────────────────────────

def _apply_ig_filters(df: pd.DataFrame, f: InstagramFilters | None) -> pd.DataFrame:
    if not f or df.empty:
        return df
    out = df
    if f.get("type"):
        out = out[out["type"].fillna("").astype(str).str.lower() == str(f["type"]).lower()]
    if f.get("has_caption"):
        out = out[out["caption"].fillna("").astype(str).str.len() > 0]
    if f.get("hashtag"):
        tag = str(f["hashtag"]).lstrip("#").lower()
        out = out[out["caption"].fillna("").astype(str).str.lower().str.contains("#" + tag, na=False)]
    if f.get("search"):
        out = out[_str_contains(out["caption"], str(f["search"]))]
    return out


def summarize_instagram(
    data: dict[str, Any] | None,
    filters: InstagramFilters | None = None,
) -> dict[str, Any]:
    profiles_raw = (data or {}).get("profiles") or []
    posts_raw = (data or {}).get("posts") or []
    top_profile = profiles_raw[0] if profiles_raw else {}
    followers = _safe_int(top_profile.get("followers"))

    if not posts_raw:
        return _empty_summary({
            "followers": followers,
            "engagement_rate": None,
            "posts_per_week": {},
            "top_hashtags": {},
            "type_breakdown": {},
            "median_likes": None,
            "p90_likes": None,
            "median_comments": None,
            "like_to_comment_ratio_p90": None,
            "peak_post_hour": None,
        })

    df = pd.DataFrame(posts_raw)
    total_unfiltered = int(len(df))

    df = _apply_ig_filters(df, filters)
    if df.empty:
        return _empty_summary({
            "total": total_unfiltered,
            "followers": followers,
            "engagement_rate": None,
            "posts_per_week": {},
            "top_hashtags": {},
            "type_breakdown": {},
            "median_likes": None,
            "p90_likes": None,
            "median_comments": None,
            "like_to_comment_ratio_p90": None,
            "peak_post_hour": None,
        })

    likes = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0)
    comments = pd.to_numeric(df.get("comments"), errors="coerce").fillna(0)
    timestamps = _to_dt(df.get("timestamp"))

    engagement_rate = None
    if followers > 0:
        per_post_eng = (likes + comments) / followers
        engagement_rate = _safe_float(per_post_eng.mean())

    weekly: dict[str, int] = {}
    peak_hour: int | None = None
    if timestamps.notna().any():
        ts = timestamps.dropna()
        weekly_starts = ts.dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("W").dt.start_time
        weekly = {dt.strftime("%Y-%m-%d"): int(c) for dt, c in weekly_starts.value_counts().sort_index().items()}
        hour_counts = ts.dt.tz_convert("UTC").dt.hour.value_counts()
        if not hour_counts.empty:
            peak_hour = int(hour_counts.idxmax())

    captions = df.get("caption", pd.Series(dtype=object)).dropna().astype(str)
    hashtags = []
    for caption in captions:
        for token in caption.split():
            if token.startswith("#") and len(token) > 1:
                hashtags.append(token.lstrip("#").lower())
    top_hashtags = {k: int(v) for k, v in Counter(hashtags).most_common(10)}

    ratio_p90 = None
    if (comments > 0).any():
        ratio = (likes / comments.replace(0, np.nan)).dropna()
        if not ratio.empty:
            ratio_p90 = _safe_float(ratio.quantile(0.9))

    return {
        "total": total_unfiltered,
        "filtered_total": int(len(df)),
        "followers": followers,
        "engagement_rate": engagement_rate,
        "posts_per_week": weekly,
        "top_hashtags": top_hashtags,
        "type_breakdown": _count_value(df.get("type", pd.Series(dtype=object)), top=8),
        "median_likes": _safe_float(likes.median()),
        "p90_likes": _safe_float(likes.quantile(0.9)),
        "median_comments": _safe_float(comments.median()),
        "like_to_comment_ratio_p90": ratio_p90,
        "peak_post_hour": peak_hour,
    }


# ── 3. TikTok (authors + videos) ─────────────────────────────────────────────

def _apply_tt_filters(df: pd.DataFrame, f: TikTokFilters | None) -> pd.DataFrame:
    if not f or df.empty:
        return df
    out = df
    if f.get("has_music"):
        out = out[out["music_name"].fillna("").astype(str).str.len() > 0]
    if f.get("hashtag"):
        tag = str(f["hashtag"]).lstrip("#").lower()
        out = out[out["hashtags"].apply(lambda lst: any(tag == str(h).lstrip("#").lower() for h in (lst or [])))]
    if f.get("search"):
        out = out[_str_contains(out["description"], str(f["search"]))]
    if f.get("min_duration") is not None:
        out = out[out["duration"].fillna(0).astype(int) >= int(f["min_duration"])]
    if f.get("max_duration") is not None:
        out = out[out["duration"].fillna(0).astype(int) <= int(f["max_duration"])]
    return out


def summarize_tiktok(
    data: dict[str, Any] | None,
    filters: TikTokFilters | None = None,
) -> dict[str, Any]:
    authors_raw = (data or {}).get("authors") or []
    videos_raw = (data or {}).get("videos") or []
    top_author = authors_raw[0] if authors_raw else {}
    followers = _safe_int(top_author.get("followers"))
    hearts = _safe_int(top_author.get("hearts"))

    if not videos_raw:
        return _empty_summary({
            "followers": followers,
            "hearts": hearts,
            "videos_per_week": {},
            "median_plays": None,
            "p90_plays": None,
            "median_likes": None,
            "like_per_play_p50": None,
            "share_to_play_p90": None,
            "avg_duration": None,
            "top_hashtags": {},
            "music_share": None,
        })

    df = pd.DataFrame(videos_raw)
    total_unfiltered = int(len(df))
    df["hashtags"] = df.get("hashtags", pd.Series([[]] * len(df))).apply(
        lambda lst: list(lst) if isinstance(lst, list) else []
    )

    df = _apply_tt_filters(df, filters)
    if df.empty:
        return _empty_summary({
            "total": total_unfiltered,
            "followers": followers,
            "hearts": hearts,
            "videos_per_week": {},
            "median_plays": None,
            "p90_plays": None,
            "median_likes": None,
            "like_per_play_p50": None,
            "share_to_play_p90": None,
            "avg_duration": None,
            "top_hashtags": {},
            "music_share": None,
        })

    plays = pd.to_numeric(df.get("plays"), errors="coerce").fillna(0)
    likes = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0)
    shares = pd.to_numeric(df.get("shares"), errors="coerce").fillna(0)
    duration = pd.to_numeric(df.get("duration"), errors="coerce").fillna(0)
    create = _to_dt(df.get("create_time"))

    weekly: dict[str, int] = {}
    if create.notna().any():
        ts = create.dropna().dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("W").dt.start_time
        weekly = {dt.strftime("%Y-%m-%d"): int(c) for dt, c in ts.value_counts().sort_index().items()}

    like_per_play = None
    if (plays > 0).any():
        ratio = (likes / plays.replace(0, np.nan)).dropna()
        if not ratio.empty:
            like_per_play = _safe_float(ratio.quantile(0.5))

    share_per_play = None
    if (plays > 0).any():
        ratio = (shares / plays.replace(0, np.nan)).dropna()
        if not ratio.empty:
            share_per_play = _safe_float(ratio.quantile(0.9))

    music_share = None
    if "music_name" in df.columns:
        non_empty = df["music_name"].fillna("").astype(str).str.len() > 0
        music_share = float(non_empty.mean()) if len(non_empty) else None

    flat_hashtags = [
        str(h).lstrip("#").lower()
        for lst in df["hashtags"]
        for h in (lst or [])
        if h
    ]
    top_hashtags = {k: int(v) for k, v in Counter(flat_hashtags).most_common(10)}

    return {
        "total": total_unfiltered,
        "filtered_total": int(len(df)),
        "followers": followers,
        "hearts": hearts,
        "videos_per_week": weekly,
        "median_plays": _safe_float(plays.median()),
        "p90_plays": _safe_float(plays.quantile(0.9)),
        "median_likes": _safe_float(likes.median()),
        "like_per_play_p50": like_per_play,
        "share_to_play_p90": share_per_play,
        "avg_duration": _safe_float(duration.mean()),
        "top_hashtags": top_hashtags,
        "music_share": music_share,
    }


# ── Dispatch ──────────────────────────────────────────────────────────────────

def summarize(
    actor_key: str,
    raw: Any,
    filters: dict[str, Any] | None,
) -> dict[str, Any]:
    """Dispatch to the right summarizer based on actor key.

    Returns ``{}`` for actors that don't have a pandas summary (light tabs do
    their summarization client-side).
    """
    if actor_key == "facebook_ads":
        return summarize_meta_ads(raw if isinstance(raw, list) else [], filters)
    if actor_key == "instagram":
        return summarize_instagram(raw if isinstance(raw, dict) else {}, filters)
    if actor_key == "tiktok":
        return summarize_tiktok(raw if isinstance(raw, dict) else {}, filters)
    return {}
