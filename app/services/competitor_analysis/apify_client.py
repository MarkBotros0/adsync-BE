"""Async wrapper around Apify's run-sync-get-dataset-items endpoint."""
import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.utils.exceptions import ApifyActorError


logger = logging.getLogger(__name__)


class ApifyClient:
    """Minimal async client for Apify actors.

    Uses the public ``run-sync-get-dataset-items`` endpoint which blocks until
    the actor finishes and returns the dataset items in one call.
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
    ) -> list[dict[str, Any]]:
        """Run an actor synchronously and return its dataset items.

        ``actor_id`` is either the human form ``username/actor-name`` or the
        16-char actor id. The slash is URL-encoded.
        """
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

        if response.status_code >= 400:
            body = response.text[:500]
            logger.warning(
                "Apify actor %s failed: %s %s", actor_id, response.status_code, body
            )
            raise ApifyActorError(
                actor_id,
                f"HTTP {response.status_code}: {body}",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApifyActorError(actor_id, "non-JSON response") from exc

        if isinstance(payload, dict) and "error" in payload:
            err = payload["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise ApifyActorError(actor_id, msg or "actor returned error")

        if not isinstance(payload, list):
            return []

        return payload
