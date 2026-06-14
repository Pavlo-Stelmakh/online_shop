import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, Numeric, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from models import Order, OrderItem


REPO_ROOT = Path(__file__).resolve().parents[1]
ORDERS_TOTAL_PRICE_CONSTRAINT_NAME = "ck_orders_total_price_non_negative"
ORDERS_STATUS_CONSTRAINT_NAME = "ck_orders_status_allowed"
ORDER_ITEMS_QUANTITY_CONSTRAINT_NAME = "ck_order_items_quantity_positive"
ORDER_ITEMS_UNIT_PRICE_CONSTRAINT_NAME = "ck_order_items_unit_price_non_negative"
ORDER_CHECK_CONSTRAINTS = {
    ORDERS_TOTAL_PRICE_CONSTRAINT_NAME: "total_price >= 0",
    ORDERS_STATUS_CONSTRAINT_NAME: "status IN ('new', 'paid', 'shipped', 'cancelled')",
}
ORDER_ITEM_CHECK_CONSTRAINTS = {
    ORDER_ITEMS_QUANTITY_CONSTRAINT_NAME: "quantity > 0",
    ORDER_ITEMS_UNIT_PRICE_CONSTRAINT_NAME: "unit_price >= 0",
}


def test_order_money_columns_use_numeric_money_type_in_model_metadata():
    total_price_type = Order.__table__.c.total_price.type
    unit_price_type = OrderItem.__table__.c.unit_price.type

    assert isinstance(total_price_type, Numeric)
    assert total_price_type.precision == 12
    assert total_price_type.scale == 2
    assert isinstance(unit_price_type, Numeric)
    assert unit_price_type.precision == 12
    assert unit_price_type.scale == 2


def test_order_required_fields_are_not_nullable_in_model_metadata():
    assert Order.__table__.c.customer_id.nullable is False
    assert Order.__table__.c.status.nullable is False
    assert Order.__table__.c.total_price.nullable is False
    assert Order.__table__.c.created_at.nullable is False


def test_order_item_required_fields_are_not_nullable_in_model_metadata():
    assert OrderItem.__table__.c.order_id.nullable is False
    assert OrderItem.__table__.c.product_id.nullable is False
    assert OrderItem.__table__.c.quantity.nullable is False
    assert OrderItem.__table__.c.unit_price.nullable is False


def test_order_check_constraints_exist_in_model_metadata():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Order.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    for constraint_name, sqltext in ORDER_CHECK_CONSTRAINTS.items():
        assert check_constraints[constraint_name] == sqltext


def test_order_item_check_constraints_exist_in_model_metadata():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in OrderItem.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    for constraint_name, sqltext in ORDER_ITEM_CHECK_CONSTRAINTS.items():
        assert check_constraints[constraint_name] == sqltext


def run_alembic_upgrade_head(database_path: Path):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path}"

    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def seed_required_parent_rows(connection):
    connection.execute(
        text(
            """
            INSERT INTO users (username, email, hashed_password, role)
            VALUES ('order_user', 'order_user@example.com', 'hash', 'customer')
            """
        )
    )
    user_id = connection.execute(text("SELECT id FROM users")).scalar_one()
    connection.execute(
        text(
            """
            INSERT INTO customers (user_id, name, email, phone)
            VALUES (:user_id, 'Order Customer', 'order_customer@example.com', '+10000000000')
            """
        ),
        {"user_id": user_id},
    )
    customer_id = connection.execute(text("SELECT id FROM customers")).scalar_one()
    connection.execute(text("INSERT INTO categories (name) VALUES ('Order Category')"))
    category_id = connection.execute(text("SELECT id FROM categories")).scalar_one()
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
                'Order Product',
                10.0,
                'Order product',
                5,
                1,
                :category_id
            )
            """
        ),
        {"category_id": category_id},
    )
    product_id = connection.execute(text("SELECT id FROM products")).scalar_one()
    return customer_id, product_id


def test_alembic_upgrade_head_enforces_orders_required_fields_on_sqlite(tmp_path):
    database_path = tmp_path / "orders_integrity.db"

    result = run_alembic_upgrade_head(database_path)

    assert result.returncode == 0, result.stdout + result.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        order_columns = {
            column["name"]: column for column in inspector.get_columns("orders")
        }
        order_item_columns = {
            column["name"]: column for column in inspector.get_columns("order_items")
        }

        assert order_columns["customer_id"]["nullable"] is False
        assert order_columns["status"]["nullable"] is False
        assert order_columns["total_price"]["nullable"] is False
        assert isinstance(order_columns["total_price"]["type"], Numeric)
        assert order_columns["total_price"]["type"].precision == 12
        assert order_columns["total_price"]["type"].scale == 2
        assert order_columns["created_at"]["nullable"] is False
        assert order_item_columns["order_id"]["nullable"] is False
        assert order_item_columns["product_id"]["nullable"] is False
        assert order_item_columns["quantity"]["nullable"] is False
        assert order_item_columns["unit_price"]["nullable"] is False
        assert isinstance(order_item_columns["unit_price"]["type"], Numeric)
        assert order_item_columns["unit_price"]["type"].precision == 12
        assert order_item_columns["unit_price"]["type"].scale == 2

        order_check_constraints = {
            constraint["name"]: constraint["sqltext"]
            for constraint in inspector.get_check_constraints("orders")
        }
        for constraint_name, sqltext in ORDER_CHECK_CONSTRAINTS.items():
            assert sqltext in order_check_constraints[constraint_name]

        order_item_check_constraints = {
            constraint["name"]: constraint["sqltext"]
            for constraint in inspector.get_check_constraints("order_items")
        }
        for constraint_name, sqltext in ORDER_ITEM_CHECK_CONSTRAINTS.items():
            assert sqltext in order_item_check_constraints[constraint_name]
    finally:
        engine.dispose()


def test_database_constraints_reject_null_and_invalid_order_values(tmp_path):
    database_path = tmp_path / "orders_constraint_enforcement.db"
    result = run_alembic_upgrade_head(database_path)
    assert result.returncode == 0, result.stdout + result.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.begin() as connection:
            customer_id, product_id = seed_required_parent_rows(connection)
            connection.execute(
                text(
                    """
                    INSERT INTO orders (customer_id, status, total_price, created_at)
                    VALUES (:customer_id, 'new', 10.0, '2026-06-13 00:00:00')
                    """
                ),
                {"customer_id": customer_id},
            )
            order_id = connection.execute(text("SELECT id FROM orders")).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (:order_id, :product_id, 1, 10.0)
                    """
                ),
                {"order_id": order_id, "product_id": product_id},
            )

        invalid_statements = [
            (
                """
                INSERT INTO orders (customer_id, status, total_price, created_at)
                VALUES (NULL, 'new', 10.0, '2026-06-13 00:00:00')
                """,
                {},
            ),
            (
                """
                INSERT INTO orders (customer_id, status, total_price, created_at)
                VALUES (:customer_id, NULL, 10.0, '2026-06-13 00:00:00')
                """,
                {"customer_id": customer_id},
            ),
            (
                """
                INSERT INTO orders (customer_id, status, total_price, created_at)
                VALUES (:customer_id, 'returned', 10.0, '2026-06-13 00:00:00')
                """,
                {"customer_id": customer_id},
            ),
            (
                """
                INSERT INTO orders (customer_id, status, total_price, created_at)
                VALUES (:customer_id, 'new', NULL, '2026-06-13 00:00:00')
                """,
                {"customer_id": customer_id},
            ),
            (
                """
                INSERT INTO orders (customer_id, status, total_price, created_at)
                VALUES (:customer_id, 'new', -0.01, '2026-06-13 00:00:00')
                """,
                {"customer_id": customer_id},
            ),
            (
                """
                INSERT INTO orders (customer_id, status, total_price, created_at)
                VALUES (:customer_id, 'new', 10.0, NULL)
                """,
                {"customer_id": customer_id},
            ),
            (
                """
                INSERT INTO order_items (order_id, product_id, quantity)
                VALUES (NULL, :product_id, 1)
                """,
                {"product_id": product_id},
            ),
            (
                """
                INSERT INTO order_items (order_id, product_id, quantity)
                VALUES (:order_id, NULL, 1)
                """,
                {"order_id": order_id},
            ),
            (
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (:order_id, :product_id, NULL, 10.0)
                """,
                {"order_id": order_id, "product_id": product_id},
            ),
            (
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (:order_id, :product_id, 0, 10.0)
                """,
                {"order_id": order_id, "product_id": product_id},
            ),
            (
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (:order_id, :product_id, 1, NULL)
                """,
                {"order_id": order_id, "product_id": product_id},
            ),
            (
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (:order_id, :product_id, 1, -0.01)
                """,
                {"order_id": order_id, "product_id": product_id},
            ),
        ]

        for statement, params in invalid_statements:
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(text(statement), params)
    finally:
        engine.dispose()


def test_order_item_unit_price_migration_backfills_existing_rows(tmp_path):
    database_path = tmp_path / "order_item_unit_price_backfill.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path}"

    base_result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "f2a8c9d4e6b7"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert base_result.returncode == 0, base_result.stdout + base_result.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.begin() as connection:
            customer_id, product_id = seed_required_parent_rows(connection)
            connection.execute(
                text(
                    """
                    INSERT INTO orders (customer_id, status, total_price, created_at)
                    VALUES (:customer_id, 'new', 25.5, '2026-06-13 00:00:00')
                    """
                ),
                {"customer_id": customer_id},
            )
            order_id = connection.execute(text("SELECT id FROM orders")).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity)
                    VALUES (:order_id, :product_id, 2)
                    """
                ),
                {"order_id": order_id, "product_id": product_id},
            )
    finally:
        engine.dispose()

    head_result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert head_result.returncode == 0, head_result.stdout + head_result.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            unit_price = connection.execute(
                text("SELECT unit_price FROM order_items")
            ).scalar_one()
        assert unit_price == 10.0
    finally:
        engine.dispose()
