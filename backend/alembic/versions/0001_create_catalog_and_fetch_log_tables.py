"""create catalog and fetch log tables

Revision ID: 0001
Revises:
Create Date: 2026-10-31 22:02:26.154420

Reversible: downgrade() drops every table, so all ingested data is lost.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fetch_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("group_slug", sa.String(length=50), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fetch_log")),
    )
    op.create_index(
        "ix_fetch_log_source_group_started",
        "fetch_log",
        ["source", "group_slug", "started_at"],
        unique=False,
    )
    op.create_table(
        "groups",
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("slug", name=op.f("pk_groups")),
    )
    op.create_table(
        "satellites",
        sa.Column("norad_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("intl_designator", sa.String(length=20), nullable=True),
        sa.Column("object_type", sa.String(length=10), nullable=True),
        sa.Column("country", sa.String(length=10), nullable=True),
        sa.Column("launch_date", sa.Date(), nullable=True),
        sa.Column("orbit_class", sa.String(length=10), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("norad_id", name=op.f("pk_satellites")),
    )
    op.create_index(op.f("ix_satellites_country"), "satellites", ["country"], unique=False)
    op.create_index(op.f("ix_satellites_launch_date"), "satellites", ["launch_date"], unique=False)
    op.create_index(op.f("ix_satellites_orbit_class"), "satellites", ["orbit_class"], unique=False)
    op.create_table(
        "orbital_elements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("norad_id", sa.BigInteger(), nullable=False),
        sa.Column("epoch", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mean_motion", sa.Double(), nullable=False),
        sa.Column("eccentricity", sa.Double(), nullable=False),
        sa.Column("inclination_deg", sa.Double(), nullable=False),
        sa.Column("raan_deg", sa.Double(), nullable=False),
        sa.Column("arg_of_pericenter_deg", sa.Double(), nullable=False),
        sa.Column("mean_anomaly_deg", sa.Double(), nullable=False),
        sa.Column("bstar", sa.Double(), nullable=False),
        sa.Column("mean_motion_dot", sa.Double(), nullable=False),
        sa.Column("mean_motion_ddot", sa.Double(), nullable=False),
        sa.Column("element_set_no", sa.Integer(), nullable=True),
        sa.Column("rev_at_epoch", sa.Integer(), nullable=True),
        sa.Column("classification_type", sa.String(length=1), nullable=False),
        sa.Column("ephemeris_type", sa.Integer(), nullable=False),
        sa.Column("raw_omm", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["norad_id"],
            ["satellites.norad_id"],
            name=op.f("fk_orbital_elements_norad_id_satellites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orbital_elements")),
        sa.UniqueConstraint("norad_id", "epoch", name="uq_orbital_elements_norad_epoch"),
    )
    op.create_table(
        "satellite_groups",
        sa.Column("group_slug", sa.String(length=50), nullable=False),
        sa.Column("norad_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_slug"],
            ["groups.slug"],
            name=op.f("fk_satellite_groups_group_slug_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["norad_id"],
            ["satellites.norad_id"],
            name=op.f("fk_satellite_groups_norad_id_satellites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("group_slug", "norad_id", name=op.f("pk_satellite_groups")),
    )


def downgrade() -> None:
    op.drop_table("satellite_groups")
    op.drop_table("orbital_elements")
    op.drop_index(op.f("ix_satellites_orbit_class"), table_name="satellites")
    op.drop_index(op.f("ix_satellites_launch_date"), table_name="satellites")
    op.drop_index(op.f("ix_satellites_country"), table_name="satellites")
    op.drop_table("satellites")
    op.drop_table("groups")
    op.drop_index("ix_fetch_log_source_group_started", table_name="fetch_log")
    op.drop_table("fetch_log")
