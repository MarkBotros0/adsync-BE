"""Pydantic schemas for the Competitor Analysis API."""
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Targets ───────────────────────────────────────────────────────────────────

class CompetitorTargetIn(BaseModel):
    actor_key: str = Field(..., min_length=1, max_length=40)
    target_value: str = Field(..., min_length=1, max_length=600)
    target_type: str = Field(..., min_length=1, max_length=20)
    is_enabled: bool = True


class CompetitorTargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor_key: str
    target_value: str
    target_type: str
    is_enabled: bool
    last_run_at: datetime | None = None
    last_cost_usd: Decimal | None = None


# ── Competitors ───────────────────────────────────────────────────────────────

class CompetitorCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    targets: list[CompetitorTargetIn] = Field(default_factory=list)


class CompetitorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)


class JobSummary(BaseModel):
    """Compact job snapshot embedded in CompetitorOut."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    actors_total: int | None = None
    actors_done: int
    actors_failed: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime
    last_job: JobSummary | None = None
    targets: list[CompetitorTargetOut] = Field(default_factory=list)
    summaries: dict[str, dict[str, Any]] | None = Field(
        default=None,
        description="Per-actor summary dicts from the latest completed run.",
    )


# ── Per-actor results / runs ──────────────────────────────────────────────────

class ActorResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor_key: str
    status: str
    summary: dict[str, Any] | None = None
    data: Any | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    actors_total: int | None = None
    actors_done: int
    actors_failed: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    actors: list[ActorResultOut]


class JobCreatedOut(BaseModel):
    job_id: int
    status: str
    actor_key: str | None = None
    estimated_cost_usd: float | None = None


class EstimatedCostOut(BaseModel):
    actor_key: str
    avg_compute_units: float | None = None
    avg_usage_usd: float | None = None
    low_usd: float | None = None
    high_usd: float | None = None
    samples: int = 0
    basis: str = "no-data"


class ActorSummaryRequest(BaseModel):
    filters: dict[str, Any] | None = None


# ── Usage ─────────────────────────────────────────────────────────────────────

class BudgetSnapshot(BaseModel):
    used_compute_units: float
    used_usd: float
    monthly_compute_unit_budget: float | None = None
    warn_at_pct: int
    percent_used: float | None = None
    will_warn: bool = False
    will_block: bool = False
    period_start: datetime


class BrandUsageOut(BaseModel):
    period_start: datetime
    compute_units_used: float
    usage_usd: float
    runs: int
    by_actor: dict[str, dict[str, float | int]]
    budget: BudgetSnapshot


class ApifyRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_key: str
    apify_run_id: str | None = None
    competitor_id: int | None = None
    status: str
    compute_units: Decimal | None = None
    usage_total_usd: Decimal | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
