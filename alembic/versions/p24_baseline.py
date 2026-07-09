"""p24_baseline — P24 Alembic tracking revision.

The actual database tables are created via SQLAlchemy's
Base.metadata.create_all() from guinevere.memory.models.
This migration exists solely to anchor the Alembic revision chain.
All legacy pre-P24 migrations have been replaced by this baseline.
"""
from alembic import op
import sqlalchemy as sa

revision = "p24_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
