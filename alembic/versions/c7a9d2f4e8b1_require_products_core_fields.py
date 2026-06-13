"""require products core fields

Revision ID: c7a9d2f4e8b1
Revises: 9f1c2d3e4a5b
Create Date: 2026-06-13 00:00:00.000000

Production precondition: production data integrity audit was run before this
migration and returned PASS. Re-run the audit before deploy; it must remain PASS.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c7a9d2f4e8b1"
down_revision: Union[str, Sequence[str], None] = "9f1c2d3e4a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRICE_CONSTRAINT_NAME = "ck_products_price_non_negative"
STOCK_CONSTRAINT_NAME = "ck_products_stock_non_negative"
LOW_STOCK_THRESHOLD_CONSTRAINT_NAME = (
    "ck_products_low_stock_threshold_non_negative"
)


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "price",
            existing_type=sa.Float(),
            nullable=False,
        )
        batch_op.alter_column(
            "description",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "stock",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "category_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            PRICE_CONSTRAINT_NAME,
            "price >= 0",
        )
        batch_op.create_check_constraint(
            STOCK_CONSTRAINT_NAME,
            "stock >= 0",
        )
        batch_op.create_check_constraint(
            LOW_STOCK_THRESHOLD_CONSTRAINT_NAME,
            "low_stock_threshold >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint(
            LOW_STOCK_THRESHOLD_CONSTRAINT_NAME,
            type_="check",
        )
        batch_op.drop_constraint(STOCK_CONSTRAINT_NAME, type_="check")
        batch_op.drop_constraint(PRICE_CONSTRAINT_NAME, type_="check")
        batch_op.alter_column(
            "category_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "stock",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "description",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "price",
            existing_type=sa.Float(),
            nullable=True,
        )
        batch_op.alter_column(
            "name",
            existing_type=sa.String(),
            nullable=True,
        )
