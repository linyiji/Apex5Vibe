"""Persist immutable aggregate snapshots, alongside module run history."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Tolerates early local builds that created this table before the migration froze.
    if not sa.inspect(op.get_bind()).has_table("assessment_snapshots"):
        op.create_table(
            "assessment_snapshots",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("case_id", sa.String(), nullable=False),
            sa.Column("document", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
        )
        op.create_index("ix_assessment_snapshots_case_id", "assessment_snapshots", ["case_id"])


def downgrade():
    op.drop_table("assessment_snapshots")
