"""add user id to customers

Revision ID: 0706b18c8fa3
Revises: 134f1414fd05
Create Date: 2026-05-31 21:34:56.660418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0706b18c8fa3'
down_revision: Union[str, Sequence[str], None] = '134f1414fd05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("user_id", sa.Integer(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column("customers", "user_id")
