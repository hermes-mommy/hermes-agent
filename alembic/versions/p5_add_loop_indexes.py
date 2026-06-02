"""add_loop_indexes — add performance indexes to loop_instances.

Adds indexes on status, task_id (FK), and started_at (temporal queries).
"""
from alembic import op

revision = "p5_add_loop_indexes"
down_revision = "p5_extend_loops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_loop_instances_status",
        "loop_instances",
        ["status"],
        schema="projects",
    )
    op.create_index(
        "ix_loop_instances_task_id",
        "loop_instances",
        ["task_id"],
        schema="projects",
    )
    op.create_index(
        "ix_loop_instances_started_at",
        "loop_instances",
        [op.text("started_at DESC")],
        schema="projects",
    )


def downgrade() -> None:
    op.drop_index("ix_loop_instances_started_at", table_name="loop_instances", schema="projects")
    op.drop_index("ix_loop_instances_task_id", table_name="loop_instances", schema="projects")
    op.drop_index("ix_loop_instances_status", table_name="loop_instances", schema="projects")
