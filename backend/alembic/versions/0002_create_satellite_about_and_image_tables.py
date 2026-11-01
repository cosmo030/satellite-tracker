"""create satellite_about and satellite_image tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-01 18:00:00.000000

Adds two new tables only; existing tables are untouched, so it is safe to apply while the
previous application version is running. Reversible: downgrade() drops both tables, losing the
fetched descriptions and images (the enrich job fetches them again).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "satellite_about",
        sa.Column("norad_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("wikidata_qid", sa.Text(), nullable=True),
        sa.Column("match_method", sa.String(length=10), nullable=True),
        sa.Column("scope", sa.String(length=15), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_source", sa.String(length=10), nullable=True),
        sa.Column("summary_url", sa.Text(), nullable=True),
        sa.Column("summary_revision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("categories", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("operators", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("manufacturers", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('ok', 'no_match', 'error')", name=op.f("ck_satellite_about_status")
        ),
        sa.CheckConstraint(
            "match_method IN ('norad', 'cospar')", name=op.f("ck_satellite_about_match_method")
        ),
        sa.CheckConstraint(
            "scope IN ('object', 'constellation')", name=op.f("ck_satellite_about_scope")
        ),
        sa.CheckConstraint(
            "summary_source IN ('wikipedia', 'wikidata')",
            name=op.f("ck_satellite_about_summary_source"),
        ),
        sa.ForeignKeyConstraint(
            ["norad_id"],
            ["satellites.norad_id"],
            name=op.f("fk_satellite_about_norad_id_satellites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("norad_id", name=op.f("pk_satellite_about")),
    )
    op.create_index(
        op.f("ix_satellite_about_fetched_at"), "satellite_about", ["fetched_at"], unique=False
    )
    op.create_table(
        "satellite_image",
        sa.Column("norad_id", sa.BigInteger(), nullable=False),
        sa.Column("image_480", sa.LargeBinary(), nullable=False),
        sa.Column("image_960", sa.LargeBinary(), nullable=False),
        sa.Column("mime", sa.String(length=20), nullable=False),
        sa.Column("width_480", sa.Integer(), nullable=False),
        sa.Column("height_480", sa.Integer(), nullable=False),
        sa.Column("width_960", sa.Integer(), nullable=False),
        sa.Column("height_960", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("source_file", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("artist", sa.Text(), nullable=False),
        sa.Column("license_short", sa.Text(), nullable=False),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("attribution_required", sa.Boolean(), nullable=False),
        sa.Column("alt_text", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["norad_id"],
            ["satellites.norad_id"],
            name=op.f("fk_satellite_image_norad_id_satellites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("norad_id", name=op.f("pk_satellite_image")),
    )


def downgrade() -> None:
    op.drop_table("satellite_image")
    op.drop_index(op.f("ix_satellite_about_fetched_at"), table_name="satellite_about")
    op.drop_table("satellite_about")
