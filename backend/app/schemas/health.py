"""Response schema for the health endpoint."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    database: bool = Field(description="True when a trivial query succeeded.")
    # Surfaced here so a deployed instance can be checked for which rubric and
    # model it is actually serving — SRS 5.5 auditability, from the outside.
    rubric_version: str
    model_version: str
