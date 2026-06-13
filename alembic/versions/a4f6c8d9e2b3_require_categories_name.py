"""require categories name

Revision ID: a4f6c8d9e2b3
Revises: c7a9d2f4e8b1
Create Date: 2026-06-13 00:00:00.000000

Production precondition: production data integrity audit was run before this
migration and returned PASS. Re-run the audit before deploy; it must remain PASS.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a4f6c8d9e2b3"
down_revision: Union[str, Sequence[str], None] = "c7a9d2f4e8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORY_NAME_CONSTRAINT_NAME = "ck_categories_name_not_empty"


def upgrade() -> None:
    with op.batch_alter_table("categories") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            CATEGORY_NAME_CONSTRAINT_NAME,
            "trim(name) <> ''",
        )


def downgrade() -> None:
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_constraint(CATEGORY_NAME_CONSTRAINT_NAME, type_="check")
        batch_op.alter_column(
            "name",
            existing_type=sa.String(),
            nullable=True,
        )
