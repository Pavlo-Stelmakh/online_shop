"""require customers required fields

Revision ID: e5c1a7d9b2f0
Revises: a4f6c8d9e2b3
Create Date: 2026-06-13 00:00:00.000000

Production precondition: production data integrity audit was run before this
migration and returned PASS. Re-run the audit before deploy; it must remain PASS.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e5c1a7d9b2f0"
down_revision: Union[str, Sequence[str], None] = "a4f6c8d9e2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CUSTOMER_NAME_CONSTRAINT_NAME = "ck_customers_name_not_empty"
CUSTOMER_EMAIL_CONSTRAINT_NAME = "ck_customers_email_not_empty"
CUSTOMER_PHONE_CONSTRAINT_NAME = "ck_customers_phone_not_empty"


def upgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "name",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "phone",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            CUSTOMER_NAME_CONSTRAINT_NAME,
            "trim(name) <> ''",
        )
        batch_op.create_check_constraint(
            CUSTOMER_EMAIL_CONSTRAINT_NAME,
            "trim(email) <> ''",
        )
        batch_op.create_check_constraint(
            CUSTOMER_PHONE_CONSTRAINT_NAME,
            "trim(phone) <> ''",
        )


def downgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_constraint(CUSTOMER_PHONE_CONSTRAINT_NAME, type_="check")
        batch_op.drop_constraint(CUSTOMER_EMAIL_CONSTRAINT_NAME, type_="check")
        batch_op.drop_constraint(CUSTOMER_NAME_CONSTRAINT_NAME, type_="check")
        batch_op.alter_column(
            "phone",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "name",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
