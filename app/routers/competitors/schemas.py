"""Pydantic schemas for the Competitor Analysis API."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CompetitorCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class JobSummary(BaseModel):
    """Compact job snapshot embedded in CompetitorOut."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    actors_total: int
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
    summaries: dict[str, dict[str, Any]] | None = Field(
        default=None,
        description="Per-actor summary dicts from the latest completed job.",
    )


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
    actors_total: int
    actors_done: int
    actors_failed: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    actors: list[ActorResultOut]


class CompetitorResultsOut(BaseModel):
    competitor: CompetitorOut
    job: JobSummary | None = None
    results: dict[str, ActorResultOut]


class JobCreatedOut(BaseModel):
    job_id: int
    status: str
