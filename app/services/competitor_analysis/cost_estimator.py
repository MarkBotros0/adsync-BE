"""Pre-run cost estimates from past Apify runs."""
from dataclasses import dataclass

from app.database import get_session_local
from app.repositories.apify_run import ApifyRunRepository


@dataclass
class EstimatedCost:
    actor_key: str
    avg_compute_units: float | None
    avg_usage_usd: float | None
    low_usd: float | None
    high_usd: float | None
    samples: int
    basis: str  # "rolling-avg" | "global-avg" | "no-data"


def estimate(brand_id: int, actor_key: str) -> EstimatedCost:
    """Cheap rolling-average estimate of what the next run will cost.

    Uses the brand's last 10 runs of this actor; falls back to a global average
    across all brands; returns ``no-data`` for first-run users. The ±25% band
    is a heuristic guard for the UI — actual cost is recorded after the run.
    """
    db = get_session_local()()
    try:
        stats = ApifyRunRepository(db).rolling_avg_cost(brand_id, actor_key, n=10)
    finally:
        db.close()

    avg_usd = stats.get("avg_usage_usd")
    avg_cu = stats.get("avg_compute_units")
    samples = int(stats.get("samples") or 0)
    basis = str(stats.get("basis") or "no-data")

    low: float | None = None
    high: float | None = None
    if isinstance(avg_usd, (int, float)) and avg_usd > 0:
        low = round(avg_usd * 0.75, 4)
        high = round(avg_usd * 1.5, 4)

    return EstimatedCost(
        actor_key=actor_key,
        avg_compute_units=avg_cu if isinstance(avg_cu, (int, float)) else None,
        avg_usage_usd=avg_usd if isinstance(avg_usd, (int, float)) else None,
        low_usd=low,
        high_usd=high,
        samples=samples,
        basis=basis,
    )
