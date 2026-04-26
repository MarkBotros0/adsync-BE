"""Async wrapper around Apify's run-sync-get-dataset-items endpoint."""
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.utils.exceptions import ApifyActorError


logger = logging.getLogger(__name__)


@dataclass
class RunOutcome:
    """Returned by ``ApifyClient.run_actor`` — items + identifiers needed to
    look up the run's cost stats afterwards."""

    items: list[dict[str, Any]]
    run_id: str | None
    dataset_id: str | None


@dataclass
class RunMeta:
    """Run-level metadata pulled from ``GET /v2/actor-runs/{runId}``."""

    run_id: str
    status: str | None
    compute_units: float | None
    usage_total_usd: float | None
    dataset_id: str | None
    started_at: str | None
    finished_at: str | None


class ApifyClient:
    """Minimal async client for Apify actors.

    Uses the public ``run-sync-get-dataset-items`` endpoint which blocks until
    the actor finishes and returns the dataset items in one call. The Apify
    response surfaces the run id via the ``X-Apify-Pagination-Total`` family of
    headers — we read ``X-Apify-Run-Id`` and ``X-Apify-Dataset-Id`` so callers
    can fetch run-level cost/usage metadata afterwards via ``fetch_run_meta``.
    """

    BASE_URL = "https://api.apify.com/v2"

    def __init__(self, token: str):
        if not token:
            raise ApifyActorError("apify", "APIFY_API_TOKEN is not configured")
        self.token = token

    async def run_actor(
        self,
        actor_id: str,
        run_input: dict[str, Any],
        timeout_seconds: int = 300,
        memory_mb: int = 1024,
    ) -> RunOutcome:
        """Run an actor synchronously and return its dataset items + run id."""
        encoded_id = quote(actor_id, safe="")
        url = (
            f"{self.BASE_URL}/acts/{encoded_id}/run-sync-get-dataset-items"
            f"?token={self.token}&memory={memory_mb}&timeout={timeout_seconds}"
            f"&format=json&clean=true"
        )

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds + 30) as client:
                response = await client.post(
                    url,
                    json=run_input,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise ApifyActorError(actor_id, f"network error: {exc}") from exc

        run_id = _read_run_id(response)
        dataset_id = response.headers.get("x-apify-dataset-id") or response.headers.get(
            "X-Apify-Dataset-Id"
        )

        if response.status_code >= 400:
            body = response.text[:500]
            logger.warning(
                "Apify actor %s failed: %s %s", actor_id, response.status_code, body
            )
            raise ApifyActorError(
                actor_id,
                f"HTTP {response.status_code}: {body}",
                run_id=run_id,
                dataset_id=dataset_id,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApifyActorError(actor_id, "non-JSON response", run_id=run_id) from exc

        if isinstance(payload, dict) and "error" in payload:
            err = payload["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise ApifyActorError(
                actor_id,
                msg or "actor returned error",
                run_id=run_id,
                dataset_id=dataset_id,
            )

        items = payload if isinstance(payload, list) else []
        return RunOutcome(items=items, run_id=run_id, dataset_id=dataset_id)

    async def fetch_run_meta(self, run_id: str) -> RunMeta | None:
        """Fetch run-level cost stats. Returns ``None`` on any failure — cost
        capture is best-effort and must never abort the calling flow."""
        if not run_id:
            return None
        url = f"{self.BASE_URL}/actor-runs/{quote(run_id, safe='')}?token={self.token}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            logger.warning("Apify run-meta fetch failed: run=%s err=%s", run_id, exc)
            return None
        if response.status_code >= 400:
            logger.warning(
                "Apify run-meta non-2xx: run=%s status=%s", run_id, response.status_code
            )
            return None
        try:
            body = response.json()
        except ValueError:
            return None

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            return None

        stats = data.get("stats") or {}
        usage_total_usd = data.get("usageTotalUsd")
        compute_units = stats.get("computeUnits") if isinstance(stats, dict) else None

        return RunMeta(
            run_id=str(data.get("id") or run_id),
            status=data.get("status"),
            compute_units=_to_float(compute_units),
            usage_total_usd=_to_float(usage_total_usd),
            dataset_id=data.get("defaultDatasetId"),
            started_at=data.get("startedAt"),
            finished_at=data.get("finishedAt"),
        )


def _read_run_id(response: httpx.Response) -> str | None:
    for key in (
        "x-apify-run-id",
        "X-Apify-Run-Id",
        "x-apify-actor-run-id",
    ):
        value = response.headers.get(key)
        if value:
            return value
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
