"""add low stock threshold to products

Revision ID: b818d4971857
Revises: 4625e3aa4704
Create Date: 2026-06-10 11:02:26.911083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b818d4971857'
down_revision: Union[str, Sequence[str], None] = '4625e3aa4704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "low_stock_threshold",
            sa.Integer(),
            nullable=False,
            server_default="5"
        )
    )

def downgrade() -> None:
    op.drop_column("products", "low_stock_threshold")
