"""Explicit evidence groups and atomic, parse-validated replacement."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evidence", sa.Column("evidence_group", sa.String(), nullable=True))
    op.add_column("evidence", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("evidence", sa.Column("supersedes_evidence_id", sa.String(), nullable=True))
    op.add_column("evidence", sa.Column("status", sa.String(), nullable=False, server_default="active"))
    op.execute("UPDATE evidence SET status='pending' WHERE parse_status='pending'")
    op.execute("UPDATE evidence SET status='failed' WHERE parse_status='failed'")
    op.execute(
        "CREATE UNIQUE INDEX active_evidence_group ON evidence(case_id,module_key,evidence_group) WHERE evidence_group IS NOT NULL AND status='active'"
    )
    op.execute(
        "CREATE UNIQUE INDEX pending_evidence_group ON evidence(case_id,module_key,evidence_group) WHERE evidence_group IS NOT NULL AND status='pending'"
    )


def downgrade():
    op.drop_index("active_evidence_group", table_name="evidence")
    op.drop_index("pending_evidence_group", table_name="evidence")
    for column in ["status", "supersedes_evidence_id", "version", "evidence_group"]:
        op.drop_column("evidence", column)
