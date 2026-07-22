"""Adopt the existing T2D schema as the Alembic baseline."""
from pathlib import Path

from alembic import op


revision = "20260715_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "full_schema.sql"
    schema = schema_path.read_text(encoding="utf-8").split("GRANT ALL PRIVILEGES", 1)[0]
    for statement in schema.split(";"):
        statement = statement.strip()
        if statement:
            op.execute(statement)


def downgrade() -> None:
    pass
