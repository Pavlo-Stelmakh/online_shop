"""require users core fields

Revision ID: 9f1c2d3e4a5b
Revises: 2d4d8b7a9c1e
Create Date: 2026-06-13 00:00:00.000000

Production precondition: production data integrity audit was run before this
migration and returned PASS. Re-run the audit before deploy; it must remain PASS.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9f1c2d3e4a5b"
down_revision: Union[str, Sequence[str], None] = "2d4d8b7a9c1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_CONSTRAINT_NAME = "ck_users_role_admin_customer"


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "username",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "hashed_password",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "role",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            ROLE_CONSTRAINT_NAME,
            "role IN ('admin', 'customer')",
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(ROLE_CONSTRAINT_NAME, type_="check")
        batch_op.alter_column(
            "role",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "hashed_password",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "username",
            existing_type=sa.String(),
            nullable=True,
        )
