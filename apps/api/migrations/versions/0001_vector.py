"""Enable pgvector in a fresh project database."""

from alembic import op
from sqlalchemy import text

revision = "0001_vector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    exists = (
        op.get_bind()
        .execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        .scalar_one()
    )
    if exists:
        raise RuntimeError("Use a fresh database; refusing to take ownership of existing pgvector")
    op.execute("CREATE EXTENSION vector")


def downgrade() -> None:
    # No CASCADE: refuse to delete objects that a later feature still depends on.
    op.execute("DROP EXTENSION vector")
