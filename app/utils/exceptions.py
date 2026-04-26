class FacebookAPIError(Exception):
    """Raised when Facebook API returns an error"""
    pass


class InstagramAPIError(Exception):
    """Raised when Instagram Graph API returns an error"""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class SessionNotFoundError(Exception):
    """Raised when session is not found or expired"""
    pass


class ApifyActorError(Exception):
    """Raised when an Apify actor run fails or times out.

    Carries ``run_id`` / ``dataset_id`` when available so callers can still
    persist a cost-ledger row for the failed run.
    """

    def __init__(
        self,
        actor_id: str,
        message: str,
        run_id: str | None = None,
        dataset_id: str | None = None,
    ):
        self.actor_id = actor_id
        self.run_id = run_id
        self.dataset_id = dataset_id
        super().__init__(f"[{actor_id}] {message}")

