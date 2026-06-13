"""require orders required fields

Revision ID: f2a8c9d4e6b7
Revises: e5c1a7d9b2f0
Create Date: 2026-06-13 00:00:00.000000

Production precondition: production data integrity audit was run before this
migration and returned PASS. Re-run the audit before deploy; it must remain PASS.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f2a8c9d4e6b7"
down_revision: Union[str, Sequence[str], None] = "e5c1a7d9b2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORDERS_TOTAL_PRICE_CONSTRAINT_NAME = "ck_orders_total_price_non_negative"
ORDERS_STATUS_CONSTRAINT_NAME = "ck_orders_status_allowed"
ORDER_ITEMS_QUANTITY_CONSTRAINT_NAME = "ck_order_items_quantity_positive"


ORDER_STATUS_CHECK_SQL = "status IN ('new', 'paid', 'shipped', 'cancelled')"


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column(
            "customer_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "total_price",
            existing_type=sa.Float(),
            nullable=False,
        )
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            ORDERS_TOTAL_PRICE_CONSTRAINT_NAME,
            "total_price >= 0",
        )
        batch_op.create_check_constraint(
            ORDERS_STATUS_CONSTRAINT_NAME,
            ORDER_STATUS_CHECK_SQL,
        )

    with op.batch_alter_table("order_items") as batch_op:
        batch_op.alter_column(
            "order_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "product_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            ORDER_ITEMS_QUANTITY_CONSTRAINT_NAME,
            "quantity > 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_constraint(ORDER_ITEMS_QUANTITY_CONSTRAINT_NAME, type_="check")
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "product_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "order_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint(ORDERS_STATUS_CONSTRAINT_NAME, type_="check")
        batch_op.drop_constraint(ORDERS_TOTAL_PRICE_CONSTRAINT_NAME, type_="check")
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            nullable=True,
        )
        batch_op.alter_column(
            "total_price",
            existing_type=sa.Float(),
            nullable=True,
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "customer_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
