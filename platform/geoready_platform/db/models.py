"""ORM models — the entity spine.

Design principles (Phase 0):
- The **business entity** is the root object; audits write *signals onto an
  entity*. Audits are demoted to one signal source, not the product.
- Every tenant-scoped table carries ``org_id`` so isolation can be enforced at
  both the application layer (always) and via PostgreSQL RLS (production).
- ``perception``, ``intervention``, ``impact`` are created **stub-only** now so
  their shape is fixed and future phases avoid migrations. They carry no logic
  in Phase 0.
- Portable types only (String UUIDs, generic JSON) so the suite runs on SQLite
  in tests and Postgres in production.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoready_platform.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class AuditStatus(str, Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class TriggeredBy(str, Enum):
    manual = "manual"
    scheduled = "scheduled"
    api = "api"
    verify = "verify"


# ─── Tenancy ────────────────────────────────────────────────────────────────


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    members: Mapped[list[OrgMember]] = relationship(back_populates="org", cascade="all, delete-orphan")
    entities: Mapped[list[BusinessEntity]] = relationship(back_populates="org", cascade="all, delete-orphan")
    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="org", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class OrgMember(Base):
    __tablename__ = "org_members"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_org_member"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=Role.owner.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    org: Mapped[Org] = relationship(back_populates="members")


class ApiKey(Base):
    """Org-scoped API key. Only the bcrypt/pbkdf2 hash is stored, never the key."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # non-secret lookup hint
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    org: Mapped[Org] = relationship(back_populates="api_keys")


# ─── Entity spine ───────────────────────────────────────────────────────────


class BusinessEntity(Base):
    __tablename__ = "business_entity"
    __table_args__ = (Index("ix_entity_org", "org_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geo: Mapped[str | None] = mapped_column(String(128), nullable=True)
    website_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Ownership verification (Phase 0 gate for any crawl/fix).
    verification_method: Mapped[str | None] = mapped_column(String(16), nullable=True)  # dns | file
    verification_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    org: Mapped[Org] = relationship(back_populates="entities")
    signals: Mapped[list[EntitySignal]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    audits: Mapped[list[AuditJob]] = relationship(back_populates="entity", cascade="all, delete-orphan")

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None


class EntitySignal(Base):
    """A perceived fact about the entity from one source (e.g. website audit)."""

    __tablename__ = "entity_signal"
    __table_args__ = (Index("ix_signal_entity_created", "entity_id", "fetched_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("business_entity.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "website_audit"
    signal_type: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. "robots", "schema"
    value: Mapped[dict] = mapped_column("value_jsonb", JSON, nullable=False, default=dict)
    ai_reachable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    entity: Mapped[BusinessEntity] = relationship(back_populates="signals")


class AuditJob(Base):
    __tablename__ = "audit_jobs"
    __table_args__ = (
        Index("ix_audit_entity_created", "entity_id", "created_at"),
        Index("ix_audit_org_status", "org_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("business_entity.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=AuditStatus.queued.value)
    triggered_by: Mapped[str] = mapped_column(String(16), nullable=False, default=TriggeredBy.api.value)

    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column("score_breakdown_jsonb", JSON, nullable=True)
    full_result: Mapped[dict | None] = mapped_column("full_result_jsonb", JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    entity: Mapped[BusinessEntity] = relationship(back_populates="audits")


# ─── Stub tables (shape only — NO Phase 0 logic) ────────────────────────────
# Created now so future phases (perception probe, execution, attribution) do not
# require migrations. Intentionally minimal; columns will be extended later.


class ProbeRun(Base):
    """One AI Perception Probe execution — groups the per-prompt Perception rows.

    This is the unit users poll and trend. Provenance (provider, model,
    taxonomy_version) is recorded at run level AND on each Perception row so
    historical comparisons stay valid as scoring/taxonomy evolve.
    """

    __tablename__ = "probe_run"
    __table_args__ = (Index("ix_probe_entity_created", "entity_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("business_entity.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=AuditStatus.queued.value)

    # Provenance (run level)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taxonomy_version: Mapped[str | None] = mapped_column(String(16), nullable=True)

    prompt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Metrics (v1)
    share_of_model: Mapped[float | None] = mapped_column(nullable=True)
    recommended_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    competitors: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{name, mentions}]
    flags: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{type, severity, perception_id, evidence}]

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    perceptions: Mapped[list[Perception]] = relationship(back_populates="probe_run", cascade="all, delete-orphan")


class Perception(Base):
    """What an AI engine said about an entity for a single prompt.

    Every row is a self-contained, immutable record of one AI answer with full
    provenance — provider, model, taxonomy version, the exact prompt, the raw
    response, and the timestamp — so re-scoring or taxonomy changes never
    invalidate historical data.
    """

    __tablename__ = "perception"
    __table_args__ = (Index("ix_perception_run", "probe_run_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("business_entity.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    probe_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("probe_run.id", ondelete="CASCADE"), nullable=True
    )

    # Provenance (per response) — required for valid historical comparison.
    engine: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taxonomy_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    prompt_category: Mapped[str | None] = mapped_column(String(32), nullable=True)

    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    recommended: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    brand_mentioned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    domain_cited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    competitors_named: Mapped[list | None] = mapped_column(JSON, nullable=True)
    flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    probed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    probe_run: Mapped[ProbeRun | None] = relationship(back_populates="perceptions")


class Intervention(Base):
    """A change proposed/executed to improve perception. Populated in Phase 1+."""

    __tablename__ = "intervention"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("business_entity.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    fix_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proposed_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    executed_via: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Impact(Base):
    """Measured/attributed business impact. Populated in Phase 2+."""

    __tablename__ = "impact"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("business_entity.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    intervention_id: Mapped[str | None] = mapped_column(
        ForeignKey("intervention.id", ondelete="SET NULL"), nullable=True
    )
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


__all__ = [
    "Role",
    "AuditStatus",
    "TriggeredBy",
    "Org",
    "User",
    "OrgMember",
    "ApiKey",
    "BusinessEntity",
    "EntitySignal",
    "AuditJob",
    "ProbeRun",
    "Perception",
    "Intervention",
    "Impact",
]
