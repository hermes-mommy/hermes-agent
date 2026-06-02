"""P5-001: Extend loop_instances with operational columns.

Adds goal, guardian_heartbeat_at, lqs_score, cost_estimate, error_count,
retry_count columns and makes task_id nullable for ad-hoc loops.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "p5_extend_loops"
down_revision = "65f863220922"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend projects.loop_instances with operational tracking columns."""
    op.alter_column(
        "loop_instances",
        "task_id",
        existing_type=sa.UUID(),
        nullable=True,
        schema="projects",
    )
    op.add_column(
        "loop_instances",
        sa.Column("goal", sa.Text(), nullable=True),
        schema="projects",
    )
    op.add_column(
        "loop_instances",
        sa.Column(
            "guardian_heartbeat_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        schema="projects",
    )
    op.add_column(
        "loop_instances",
        sa.Column("lqs_score", sa.Float(), nullable=True),
        schema="projects",
    )
    op.add_column(
        "loop_instances",
        sa.Column("cost_estimate", sa.Float(), nullable=True),
        schema="projects",
    )
    op.add_column(
        "loop_instances",
        sa.Column("error_count", sa.Integer(), server_default="0"),
        schema="projects",
    )
    op.add_column(
        "loop_instances",
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        schema="projects",
    )


def downgrade() -> None:
    """Revert projects.loop_instances to pre-P5 state."""
    op.drop_column("loop_instances", "retry_count", schema="projects")
    op.drop_column("loop_instances", "error_count", schema="projects")
    op.drop_column("loop_instances", "cost_estimate", schema="projects")
    op.drop_column("loop_instances", "lqs_score", schema="projects")
    op.drop_column("loop_instances", "guardian_heartbeat_at", schema="projects")
    op.drop_column("loop_instances", "goal", schema="projects")
    op.alter_column(
        "loop_instances",
        "task_id",
        existing_type=sa.UUID(),
        nullable=False,
        schema="projects",
    )
