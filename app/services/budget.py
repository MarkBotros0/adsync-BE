"""Subscription budget gate for paid Apify scrapes."""
from dataclasses import dataclass
from datetime import datetime

from app.database import get_session_local
from app.models.brand import BrandModel
from app.models.organization import OrganizationModel
from app.models.organization_membership import OrganizationMembershipModel
from app.models.subscription import SubscriptionModel
from app.repositories.apify_run import ApifyRunRepository


DEFAULT_MONTHLY_COMPUTE_UNIT_BUDGET = 50.0  # generous default for plans without an explicit budget
DEFAULT_BUDGET_WARN_AT_PCT = 80


@dataclass
class BudgetStatus:
    used_compute_units: float
    used_usd: float
    monthly_compute_unit_budget: float | None
    warn_at_pct: int
    percent_used: float | None
    will_warn: bool
    will_block: bool
    period_start: datetime


def _resolve_subscription(db, org_id: int | None) -> SubscriptionModel | None:
    if not org_id:
        return None
    org = (
        db.query(OrganizationModel)
        .filter(
            OrganizationModel.id == org_id,
            OrganizationModel.deleted_at.is_(None),
        )
        .first()
    )
    if not org or not getattr(org, "subscription_id", None):
        return None
    return (
        db.query(SubscriptionModel)
        .filter(SubscriptionModel.id == org.subscription_id)
        .first()
    )


def check_budget(brand_id: int, org_id: int | None = None) -> BudgetStatus:
    """Return the current budget status for the brand's organization.

    Reads ``monthly_compute_unit_budget`` and ``budget_warn_at_pct`` from
    ``SubscriptionModel.features`` and computes the brand's month-to-date
    Apify spend. SUPER bypass is handled at the router layer.
    """
    db = get_session_local()()
    try:
        usage = ApifyRunRepository(db).monthly_usage_for_brand(brand_id)

        budget: float | None = DEFAULT_MONTHLY_COMPUTE_UNIT_BUDGET
        warn_at = DEFAULT_BUDGET_WARN_AT_PCT
        sub = _resolve_subscription(db, org_id)
        if sub and isinstance(sub.features, dict):
            features = sub.features
            raw_budget = features.get("monthly_compute_unit_budget")
            if raw_budget is None:
                budget = None  # unlimited if subscription explicitly opts out
            else:
                try:
                    budget = float(raw_budget)
                except (TypeError, ValueError):
                    budget = DEFAULT_MONTHLY_COMPUTE_UNIT_BUDGET
            try:
                warn_at = int(features.get("budget_warn_at_pct", DEFAULT_BUDGET_WARN_AT_PCT))
            except (TypeError, ValueError):
                warn_at = DEFAULT_BUDGET_WARN_AT_PCT
    finally:
        db.close()

    used_cu = float(usage.get("compute_units") or 0)
    used_usd = float(usage.get("usage_usd") or 0)

    percent: float | None = None
    will_warn = False
    will_block = False
    if budget and budget > 0:
        percent = round((used_cu / budget) * 100, 2)
        will_warn = percent >= warn_at
        will_block = percent >= 100

    return BudgetStatus(
        used_compute_units=used_cu,
        used_usd=used_usd,
        monthly_compute_unit_budget=budget,
        warn_at_pct=warn_at,
        percent_used=percent,
        will_warn=will_warn,
        will_block=will_block,
        period_start=usage.get("period_start") or datetime.utcnow(),
    )


def is_super(brand: BrandModel | None) -> bool:
    """Best-effort check for the SUPER role; falls back to looking up org membership."""
    if not brand:
        return False
    if str(getattr(brand, "role", "") or "").upper() == "SUPER":
        return True
    org_id = getattr(brand, "organization_id", None)
    if not org_id:
        return False
    db = get_session_local()()
    try:
        membership = (
            db.query(OrganizationMembershipModel)
            .filter(
                OrganizationMembershipModel.organization_id == org_id,
                OrganizationMembershipModel.deleted_at.is_(None),
            )
            .first()
        )
        if not membership:
            return False
        return str(getattr(membership, "role", "") or "").upper() == "SUPER"
    finally:
        db.close()
