"""add customers user_id foreign key

Revision ID: 2d4d8b7a9c1e
Revises: b818d4971857
Create Date: 2026-06-13 00:00:00.000000

Production precondition: run scripts/audit_data_integrity.py before deploy;
the audit must return PASS and the customers.user_id orphan check must be 0.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2d4d8b7a9c1e"
down_revision: Union[str, Sequence[str], None] = "b818d4971857"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "fk_customers_user_id_users"


def upgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.create_foreign_key(
            CONSTRAINT_NAME,
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="foreignkey")
