"""add order item unit price snapshot

Revision ID: 7b2c9d1e4f6a
Revises: f2a8c9d4e6b7
Create Date: 2026-06-13 00:00:00.000000

Production precondition: production data integrity audit must return PASS before
this migration is deployed.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7b2c9d1e4f6a"
down_revision: Union[str, Sequence[str], None] = "f2a8c9d4e6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORDER_ITEMS_UNIT_PRICE_CONSTRAINT_NAME = "ck_order_items_unit_price_non_negative"


def upgrade() -> None:
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.add_column(sa.Column("unit_price", sa.Float(), nullable=True))

    connection = op.get_bind()
    orphan_count = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM order_items AS oi
            LEFT JOIN products AS p ON p.id = oi.product_id
            WHERE p.id IS NULL
            """
        )
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(
            "Cannot backfill order_items.unit_price: found order_items with missing products"
        )

    # Best-effort backfill: historical order item unit prices were not stored
    # before this migration, so existing rows use the current products.price.
    connection.execute(
        sa.text(
            """
            UPDATE order_items
            SET unit_price = (
                SELECT products.price
                FROM products
                WHERE products.id = order_items.product_id
            )
            """
        )
    )

    with op.batch_alter_table("order_items") as batch_op:
        batch_op.alter_column(
            "unit_price",
            existing_type=sa.Float(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            ORDER_ITEMS_UNIT_PRICE_CONSTRAINT_NAME,
            "unit_price >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_constraint(ORDER_ITEMS_UNIT_PRICE_CONSTRAINT_NAME, type_="check")
        batch_op.drop_column("unit_price")
