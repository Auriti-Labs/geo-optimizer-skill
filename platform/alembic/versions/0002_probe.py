"""Phase 1: AI Perception Probe — probe_run table + perception provenance columns.

Adds the ProbeRun table and extends the (previously stub-only) perception table
with provenance and metric columns. On Postgres, RLS is enabled on probe_run
consistent with the other tenant tables.

IDEMPOTENT BY DESIGN: the 0001 baseline creates tables from current model
metadata, so on a *fresh* DB built at Phase 1+ these objects may already exist
(while on an incremental Phase 0 -> Phase 1 upgrade they will not). Each DDL is
therefore guarded with an inspector check so the migration is safe in both
paths. Uses batch mode so SQLite can alter the perception table.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_probe"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

_NEW_PERCEPTION_COLUMNS = [
    ("probe_run_id", sa.String(length=36), True),
    ("provider", sa.String(length=32), True),
    ("model", sa.String(length=64), True),
    ("taxonomy_version", sa.String(length=16), True),
    ("prompt_category", sa.String(length=32), True),
    ("brand_mentioned", sa.Boolean(), True),
    ("domain_cited", sa.Boolean(), True),
    ("competitors_named", sa.JSON(), True),
    ("flags", sa.JSON(), True),
]


def _inspector(bind):
    return sa.inspect(bind)


def _has_table(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _columns(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def _indexes(insp, table: str) -> set[str]:
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = _inspector(bind)

    if not _has_table(insp, "probe_run"):
        op.create_table(
            "probe_run",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("entity_id", sa.String(length=36), sa.ForeignKey("business_entity.id", ondelete="CASCADE"), nullable=False),
            sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
            sa.Column("provider", sa.String(length=32), nullable=True),
            sa.Column("model", sa.String(length=64), nullable=True),
            sa.Column("taxonomy_version", sa.String(length=16), nullable=True),
            sa.Column("prompt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("answered_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("share_of_model", sa.Float(), nullable=True),
            sa.Column("recommended_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("competitors", sa.JSON(), nullable=True),
            sa.Column("flags", sa.JSON(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )

    insp = _inspector(bind)
    if "ix_probe_entity_created" not in _indexes(insp, "probe_run"):
        op.create_index("ix_probe_entity_created", "probe_run", ["entity_id", "created_at"])

    existing_cols = _columns(insp, "perception")
    missing = [(n, t, nul) for (n, t, nul) in _NEW_PERCEPTION_COLUMNS if n not in existing_cols]
    if missing:
        with op.batch_alter_table("perception") as batch:
            for name, type_, nullable in missing:
                batch.add_column(sa.Column(name, type_, nullable=nullable))

    insp = _inspector(bind)
    if "ix_perception_run" not in _indexes(insp, "perception"):
        op.create_index("ix_perception_run", "perception", ["probe_run_id"])

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE probe_run ENABLE ROW LEVEL SECURITY")
        op.execute(
            "DROP POLICY IF EXISTS probe_run_org_isolation ON probe_run; "
            "CREATE POLICY probe_run_org_isolation ON probe_run "
            "USING (org_id = current_setting('app.current_org', true))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = _inspector(bind)

    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS probe_run_org_isolation ON probe_run")

    if "ix_perception_run" in _indexes(insp, "perception"):
        op.drop_index("ix_perception_run", table_name="perception")

    existing_cols = _columns(insp, "perception")
    to_drop = [n for (n, _t, _nul) in reversed(_NEW_PERCEPTION_COLUMNS) if n in existing_cols]
    if to_drop:
        with op.batch_alter_table("perception") as batch:
            for name in to_drop:
                batch.drop_column(name)

    insp = _inspector(bind)
    if _has_table(insp, "probe_run"):
        if "ix_probe_entity_created" in _indexes(insp, "probe_run"):
            op.drop_index("ix_probe_entity_created", table_name="probe_run")
        op.drop_table("probe_run")
