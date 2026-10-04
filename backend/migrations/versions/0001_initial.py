"""Initial local assessment schema."""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Frozen SQL keeps historical migrations independent from future ORM changes.
    for statement in Path(__file__).with_name("0001_schema.sql").read_text().split(";"):
        if statement.strip():
            op.execute(statement)
    op.execute(
        "CREATE UNIQUE INDEX active_module_job ON jobs(case_id,module_key) "
        "WHERE kind='module_run' AND status IN ('queued','running')"
    )
    op.execute(
        "CREATE UNIQUE INDEX active_adjustment ON manual_adjustments(case_id,module_key) "
        "WHERE status='active'"
    )


def downgrade():
    for table in [
        "idempotency_records",
        "reference_records",
        "audit_events",
        "manual_adjustments",
        "evidence",
        "jobs",
        "module_runs",
        "modules",
        "cases",
    ]:
        op.drop_table(table)
