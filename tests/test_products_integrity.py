import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, Numeric, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from models import Product


REPO_ROOT = Path(__file__).resolve().parents[1]
PRICE_CONSTRAINT_NAME = "ck_products_price_non_negative"
STOCK_CONSTRAINT_NAME = "ck_products_stock_non_negative"
LOW_STOCK_THRESHOLD_CONSTRAINT_NAME = (
    "ck_products_low_stock_threshold_non_negative"
)
PRODUCT_CONSTRAINTS = {
    PRICE_CONSTRAINT_NAME: "price >= 0",
    STOCK_CONSTRAINT_NAME: "stock >= 0",
    LOW_STOCK_THRESHOLD_CONSTRAINT_NAME: "low_stock_threshold >= 0",
}


def test_product_price_uses_numeric_money_type_in_model_metadata():
    price_type = Product.__table__.c.price.type

    assert isinstance(price_type, Numeric)
    assert price_type.precision == 12
    assert price_type.scale == 2


def test_product_required_fields_are_not_nullable_in_model_metadata():
    assert Product.__table__.c.name.nullable is False
    assert Product.__table__.c.price.nullable is False
    assert Product.__table__.c.description.nullable is False
    assert Product.__table__.c.stock.nullable is False
    assert Product.__table__.c.category_id.nullable is False
    assert Product.__table__.c.low_stock_threshold.nullable is False


def test_product_non_negative_check_constraints_exist_in_model_metadata():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Product.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    for constraint_name, sqltext in PRODUCT_CONSTRAINTS.items():
        assert check_constraints[constraint_name] == sqltext


def test_alembic_upgrade_head_enforces_products_required_fields_on_sqlite(tmp_path):
    database_path = tmp_path / "products_integrity.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        columns = {column["name"]: column for column in inspector.get_columns("products")}

        assert columns["name"]["nullable"] is False
        assert columns["price"]["nullable"] is False
        assert columns["description"]["nullable"] is False
        assert columns["stock"]["nullable"] is False
        assert columns["category_id"]["nullable"] is False
        assert columns["low_stock_threshold"]["nullable"] is False

        check_constraints = {
            constraint["name"]: constraint["sqltext"]
            for constraint in inspector.get_check_constraints("products")
        }
        for constraint_name, sqltext in PRODUCT_CONSTRAINTS.items():
            assert sqltext in check_constraints[constraint_name]

        with engine.begin() as connection:
            connection.execute(text("INSERT INTO categories (name) VALUES ('Integrity')"))
            category_id = connection.execute(
                text("SELECT id FROM categories WHERE name = 'Integrity'")
            ).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO products (
                        name,
                        price,
                        description,
                        stock,
                        low_stock_threshold,
                        category_id
                    ) VALUES (
                        'Valid Product',
                        10.0,
                        'Valid description',
                        5,
                        1,
                        :category_id
                    )
                    """
                ),
                {"category_id": category_id},
            )

        invalid_statements = [
            """
            INSERT INTO products (name, price, description, stock, low_stock_threshold, category_id)
            VALUES (NULL, 10.0, 'Missing name', 5, 1, 1)
            """,
            """
            INSERT INTO products (name, price, description, stock, low_stock_threshold, category_id)
            VALUES ('Negative price', -0.01, 'Negative price', 5, 1, 1)
            """,
            """
            INSERT INTO products (name, price, description, stock, low_stock_threshold, category_id)
            VALUES ('Negative stock', 10.0, 'Negative stock', -1, 1, 1)
            """,
            """
            INSERT INTO products (name, price, description, stock, low_stock_threshold, category_id)
            VALUES ('Negative threshold', 10.0, 'Negative threshold', 5, -1, 1)
            """,
        ]
        for statement in invalid_statements:
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(text(statement))
    finally:
        engine.dispose()
