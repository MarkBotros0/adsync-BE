from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.apify_run import (
    APIFY_RUN_STATUS_FAILED,
    APIFY_RUN_STATUS_RUNNING,
    APIFY_RUN_STATUS_SUCCEEDED,
    ApifyRunModel,
)
from app.repositories.base import BaseRepository


class ApifyRunRepository(BaseRepository[ApifyRunModel]):
    def __init__(self, db: Session):
        super().__init__(ApifyRunModel, db)

    def start_run(
        self,
        *,
        brand_id: int,
        actor_key: str,
        competitor_id: int | None = None,
        result_id: int | None = None,
        apify_run_id: str | None = None,
    ) -> ApifyRunModel:
        run = ApifyRunModel(
            brand_id=brand_id,
            competitor_id=competitor_id,
            result_id=result_id,
            actor_key=actor_key,
            apify_run_id=apify_run_id,
            status=APIFY_RUN_STATUS_RUNNING,
            started_at=datetime.utcnow(),
        )
        return self.create(run)

    def finalize_success(
        self,
        run_pk: int,
        *,
        apify_run_id: str | None,
        compute_units: float | None,
        usage_total_usd: float | None,
        dataset_id: str | None,
    ) -> None:
        row = self.get(run_pk)
        if not row:
            return
        row.status = APIFY_RUN_STATUS_SUCCEEDED
        if apify_run_id and not row.apify_run_id:
            row.apify_run_id = apify_run_id
        if compute_units is not None:
            row.compute_units = Decimal(str(compute_units))
        if usage_total_usd is not None:
            row.usage_total_usd = Decimal(str(usage_total_usd))
        if dataset_id:
            row.dataset_id = dataset_id
        row.finished_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.commit()

    def finalize_failure(
        self,
        run_pk: int,
        *,
        apify_run_id: str | None = None,
        compute_units: float | None = None,
        usage_total_usd: float | None = None,
    ) -> None:
        row = self.get(run_pk)
        if not row:
            return
        row.status = APIFY_RUN_STATUS_FAILED
        if apify_run_id and not row.apify_run_id:
            row.apify_run_id = apify_run_id
        if compute_units is not None:
            row.compute_units = Decimal(str(compute_units))
        if usage_total_usd is not None:
            row.usage_total_usd = Decimal(str(usage_total_usd))
        row.finished_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.commit()

    def monthly_usage_for_brand(
        self,
        brand_id: int,
        period_start: datetime | None = None,
    ) -> dict[str, float | int | dict[str, float]]:
        """Sum compute units and USD for the brand within the period.

        Returns ``{compute_units, usage_usd, runs, by_actor: {actor_key: {...}}}``.
        """
        if period_start is None:
            now = datetime.utcnow()
            period_start = datetime(now.year, now.month, 1)

        base = (
            self.db.query(ApifyRunModel)
            .filter(
                ApifyRunModel.brand_id == brand_id,
                ApifyRunModel.deleted_at.is_(None),
                ApifyRunModel.created_at >= period_start,
            )
        )

        totals_row = (
            base.with_entities(
                func.coalesce(func.sum(ApifyRunModel.compute_units), 0),
                func.coalesce(func.sum(ApifyRunModel.usage_total_usd), 0),
                func.count(ApifyRunModel.id),
            )
            .one()
        )
        cu_total, usd_total, run_count = totals_row

        by_actor_rows = (
            base.with_entities(
                ApifyRunModel.actor_key,
                func.coalesce(func.sum(ApifyRunModel.compute_units), 0),
                func.coalesce(func.sum(ApifyRunModel.usage_total_usd), 0),
                func.count(ApifyRunModel.id),
            )
            .group_by(ApifyRunModel.actor_key)
            .all()
        )

        by_actor: dict[str, dict[str, float | int]] = {}
        for actor_key, cu, usd, count in by_actor_rows:
            by_actor[actor_key] = {
                "compute_units": float(cu or 0),
                "usage_usd": float(usd or 0),
                "runs": int(count or 0),
            }

        return {
            "compute_units": float(cu_total or 0),
            "usage_usd": float(usd_total or 0),
            "runs": int(run_count or 0),
            "by_actor": by_actor,
            "period_start": period_start,
        }

    def rolling_avg_cost(
        self,
        brand_id: int,
        actor_key: str,
        n: int = 10,
    ) -> dict[str, float | int | None]:
        """Return rolling-average cost from the last ``n`` succeeded runs.

        Falls back to a global per-actor average if the brand has no history.
        """
        rows = (
            self.db.query(
                ApifyRunModel.compute_units,
                ApifyRunModel.usage_total_usd,
            )
            .filter(
                ApifyRunModel.brand_id == brand_id,
                ApifyRunModel.actor_key == actor_key,
                ApifyRunModel.status == APIFY_RUN_STATUS_SUCCEEDED,
                ApifyRunModel.usage_total_usd.isnot(None),
                ApifyRunModel.deleted_at.is_(None),
            )
            .order_by(ApifyRunModel.created_at.desc())
            .limit(n)
            .all()
        )

        basis = "rolling-avg"
        if not rows:
            rows = (
                self.db.query(
                    ApifyRunModel.compute_units,
                    ApifyRunModel.usage_total_usd,
                )
                .filter(
                    ApifyRunModel.actor_key == actor_key,
                    ApifyRunModel.status == APIFY_RUN_STATUS_SUCCEEDED,
                    ApifyRunModel.usage_total_usd.isnot(None),
                    ApifyRunModel.deleted_at.is_(None),
                )
                .order_by(ApifyRunModel.created_at.desc())
                .limit(n)
                .all()
            )
            basis = "global-avg"

        if not rows:
            return {"avg_compute_units": None, "avg_usage_usd": None, "samples": 0, "basis": "no-data"}

        cu_values = [float(r[0] or 0) for r in rows]
        usd_values = [float(r[1] or 0) for r in rows]
        return {
            "avg_compute_units": sum(cu_values) / len(cu_values),
            "avg_usage_usd": sum(usd_values) / len(usd_values),
            "samples": len(rows),
            "basis": basis,
        }

    def list_for_brand(
        self,
        brand_id: int,
        *,
        limit: int = 50,
        before_id: int | None = None,
    ) -> list[ApifyRunModel]:
        """Cursor-paginated ledger view (cursor = id, descending)."""
        query = (
            self.db.query(ApifyRunModel)
            .filter(
                ApifyRunModel.brand_id == brand_id,
                ApifyRunModel.deleted_at.is_(None),
            )
        )
        if before_id is not None:
            query = query.filter(ApifyRunModel.id < before_id)
        return query.order_by(ApifyRunModel.id.desc()).limit(limit).all()
