"""Generic period-over-period comparison helper.

Wraps any insights coroutine with a parallel call for the immediately preceding window
of equal length, returning current + previous values plus a percentage delta. Used by
every new KPI tile on the analytics dashboard so the ▲/▼ rendering is uniform.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import Any, TypeVar

T = TypeVar("T")


def previous_window(since: date, until: date) -> tuple[date, date]:
    """Given (since, until], return the immediately preceding equal-length window."""
    span = until - since
    return (since - span, since)


def _coerce_total(value: Any, aggregator: Callable[[Any], float] | None) -> float:
    if aggregator is not None:
        try:
            return float(aggregator(value))
        except (TypeError, ValueError):
            return 0.0
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict) and "value" in value:
        return _coerce_total(value["value"], None)
    return 0.0


def _delta_pct(current: float, previous: float) -> float | None:
    """Return % change from previous → current. None if there is no usable baseline."""
    if previous == 0:
        # Both zero → flat, no change. Going from zero → positive is "new", not a percentage.
        return 0.0 if current == 0 else None
    return round(((current - previous) / previous) * 100.0, 2)


async def compare_periods(
    fetch: Callable[[date, date], Awaitable[T]],
    since: date,
    until: date,
    aggregator: Callable[[T], float] | None = None,
) -> dict[str, Any]:
    """Run `fetch` for the current and previous equal-length window in parallel.

    Args:
        fetch: async callable taking (since, until) and returning either a number or a
            structure that ``aggregator`` can reduce to a number.
        since, until: current window (until is exclusive in the spirit of the existing
            insights services).
        aggregator: optional reducer that turns ``T`` into a float for delta calc. If
            omitted, ``fetch`` is expected to return a number directly.

    Returns:
        dict with keys: ``current``, ``previous`` (raw fetch results),
        ``current_total``, ``previous_total`` (floats),
        ``delta_pct`` (float or None — None means no comparable baseline),
        ``period`` (the two windows as ISO strings).
    """
    prev_since, prev_until = previous_window(since, until)

    current_raw, previous_raw = await asyncio.gather(
        fetch(since, until),
        fetch(prev_since, prev_until),
        return_exceptions=False,
    )

    current_total = _coerce_total(current_raw, aggregator)
    previous_total = _coerce_total(previous_raw, aggregator)

    return {
        "current": current_raw,
        "previous": previous_raw,
        "current_total": current_total,
        "previous_total": previous_total,
        "delta_pct": _delta_pct(current_total, previous_total),
        "period": {
            "current": {"since": since.isoformat(), "until": until.isoformat()},
            "previous": {"since": prev_since.isoformat(), "until": prev_until.isoformat()},
        },
    }


async def compare_kpi_set(
    kpis: dict[str, Callable[[date, date], Awaitable[float]]],
    since: date,
    until: date,
) -> dict[str, dict[str, Any]]:
    """Run `compare_periods` for many KPI fetchers in parallel and return one dict.

    Designed for the KPI tile row on the analytics overview tab — give it a mapping
    of ``{ "reach": fetch_reach, "engagement_rate": fetch_er, ... }`` and get back the
    same keys with the comparison payload for each.
    """
    keys = list(kpis.keys())
    results = await asyncio.gather(
        *(compare_periods(fetch, since, until) for fetch in kpis.values())
    )
    return dict(zip(keys, results, strict=True))


def parse_window(since_str: str | None, until_str: str | None, default_days: int = 30) -> tuple[date, date]:
    """Parse query-string ``since`` / ``until`` (ISO date) into ``date`` objects.

    Defaults to the last ``default_days`` ending today when either is missing. Centralised
    so every new analytics endpoint accepts the same shape.
    """
    today = date.today()
    if until_str:
        until = date.fromisoformat(until_str)
    else:
        until = today
    if since_str:
        since = date.fromisoformat(since_str)
    else:
        since = until - timedelta(days=default_days)
    if since > until:
        raise ValueError("`since` must be on or before `until`")
    return since, until
