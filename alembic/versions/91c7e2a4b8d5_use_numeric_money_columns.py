"""use numeric money columns

Revision ID: 91c7e2a4b8d5
Revises: 7b2c9d1e4f6a
Create Date: 2026-06-14 00:00:00.000000

Production precondition: production data integrity audit must return PASS before
this migration is deployed.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "91c7e2a4b8d5"
down_revision: Union[str, Sequence[str], None] = "7b2c9d1e4f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY_NUMERIC = sa.Numeric(12, 2)


def _round_existing_money_values() -> None:
    connection = op.get_bind()
    dialect_name = connection.dialect.name

    if dialect_name == "postgresql":
        statements = [
            "UPDATE products SET price = ROUND(price::numeric, 2)",
            "UPDATE orders SET total_price = ROUND(total_price::numeric, 2)",
            "UPDATE order_items SET unit_price = ROUND(unit_price::numeric, 2)",
        ]
    else:
        statements = [
            "UPDATE products SET price = ROUND(price, 2)",
            "UPDATE orders SET total_price = ROUND(total_price, 2)",
            "UPDATE order_items SET unit_price = ROUND(unit_price, 2)",
        ]

    for statement in statements:
        connection.execute(sa.text(statement))


def upgrade() -> None:
    _round_existing_money_values()

    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Float(),
            type_=MONEY_NUMERIC,
            existing_nullable=False,
            postgresql_using="ROUND(price::numeric, 2)",
        )

    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column(
            "total_price",
            existing_type=sa.Float(),
            type_=MONEY_NUMERIC,
            existing_nullable=False,
            postgresql_using="ROUND(total_price::numeric, 2)",
        )

    with op.batch_alter_table("order_items") as batch_op:
        batch_op.alter_column(
            "unit_price",
            existing_type=sa.Float(),
            type_=MONEY_NUMERIC,
            existing_nullable=False,
            postgresql_using="ROUND(unit_price::numeric, 2)",
        )


def downgrade() -> None:
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.alter_column(
            "unit_price",
            existing_type=MONEY_NUMERIC,
            type_=sa.Float(),
            existing_nullable=False,
        )

    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column(
            "total_price",
            existing_type=MONEY_NUMERIC,
            type_=sa.Float(),
            existing_nullable=False,
        )

    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=MONEY_NUMERIC,
            type_=sa.Float(),
            existing_nullable=False,
        )
