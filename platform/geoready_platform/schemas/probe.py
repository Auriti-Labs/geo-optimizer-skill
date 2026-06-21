"""Probe API schemas (Pydantic v2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProbeEnqueuedOut(BaseModel):
    probe_run_id: str
    status: str


class ProbeRunOut(ORMModel):
    id: str
    entity_id: str
    status: str
    provider: str | None
    model: str | None
    taxonomy_version: str | None
    prompt_count: int
    answered_count: int
    share_of_model: float | None
    recommended_count: int
    competitors: list[dict[str, Any]] | None
    flags: list[dict[str, Any]] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class PerceptionOut(ORMModel):
    id: str
    probe_run_id: str | None
    prompt_category: str | None
    provider: str | None
    model: str | None
    taxonomy_version: str | None
    prompt: str | None
    raw_response: str | None
    recommended: bool | None
    brand_mentioned: bool | None
    domain_cited: bool | None
    competitors_named: list[Any] | None
    flags: list[Any] | None
    probed_at: datetime
