"""baseline_init — initial Alembic tracking revision.

The actual database tables are created via SQLAlchemy's Base.metadata.create_all().
This migration exists solely to anchor the Alembic revision chain.
"""
from alembic import op
import sqlalchemy as sa

revision = "2bed93fd1dd0"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
