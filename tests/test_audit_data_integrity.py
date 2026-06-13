import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Category, Customer, Order, OrderItem, Product, User  # noqa: F401


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_data_integrity.py"


def create_engine_for(path: Path):
    return create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )


def run_audit(database_path: Path):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path}"
    return subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def seed_clean_database(database_path: Path):
    engine = create_engine_for(database_path)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    try:
        user = User(
            username="clean_user",
            email="clean_user@example.com",
            hashed_password="hash",
            role="customer",
        )
        category = Category(name="Clean Category")
        session.add_all([user, category])
        session.flush()

        customer = Customer(
            user_id=user.id,
            name="Clean Customer",
            email="clean_customer@example.com",
            phone="+10000000000",
        )
        product = Product(
            name="Clean Product",
            price=10.0,
            description="Clean product",
            stock=5,
            low_stock_threshold=1,
            category_id=category.id,
        )
        session.add_all([customer, product])
        session.flush()

        order = Order(customer_id=customer.id, total_price=20.0)
        session.add(order)
        session.flush()

        session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=2))
        session.commit()
    finally:
        session.close()
        engine.dispose()


def seed_bad_database(database_path: Path):
    seed_clean_database(database_path)
    engine = create_engine_for(database_path)

    with engine.begin() as connection:
        connection.execute(text("PRAGMA ignore_check_constraints = ON"))
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
                    'Bad Product',
                    -1,
                    'Invalid product row',
                    0,
                    1,
                    1
                )
                """
            )
        )
        connection.execute(text("INSERT INTO categories (name) VALUES ('   ')"))
        connection.execute(
            text(
                """
                INSERT INTO customers (
                    user_id,
                    name,
                    email,
                    phone
                ) VALUES (
                    1,
                    '   ',
                    '',
                    '   '
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO orders (
                    customer_id,
                    status,
                    total_price,
                    created_at
                ) VALUES (
                    1,
                    'returned',
                    -1,
                    '2026-06-13 00:00:00'
                )
                """
            )
        )
        bad_order_id = connection.execute(
            text("SELECT id FROM orders WHERE status = 'returned'")
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity
                ) VALUES (
                    :bad_order_id,
                    1,
                    0
                )
                """
            ),
            {"bad_order_id": bad_order_id},
        )
        connection.execute(text("PRAGMA ignore_check_constraints = OFF"))

    engine.dispose()


def test_audit_script_exists():
    assert AUDIT_SCRIPT.is_file()


def test_audit_script_does_not_contain_write_statements():
    source = AUDIT_SCRIPT.read_text(encoding="utf-8").upper()

    assert "INSERT" not in source
    assert "UPDATE" not in source
    assert "DELETE" not in source


def test_audit_script_succeeds_for_clean_database(tmp_path):
    database_path = tmp_path / "clean.db"
    seed_clean_database(database_path)

    result = run_audit(database_path)

    assert result.returncode == 0
    assert "Result: PASS" in result.stdout
    assert "No data integrity problems found." in result.stdout


def test_audit_script_fails_for_bad_database(tmp_path):
    database_path = tmp_path / "bad.db"
    seed_bad_database(database_path)

    result = run_audit(database_path)

    assert result.returncode == 1
    assert "Result: FAIL" in result.stdout
    assert "products_price_invalid" in result.stdout
    assert "categories_name_empty" in result.stdout
    assert "customers_name_empty" in result.stdout
    assert "customers_email_empty" in result.stdout
    assert "customers_phone_empty" in result.stdout
    assert "orders_status_invalid" in result.stdout
    assert "orders_total_price_invalid" in result.stdout
    assert "order_items_quantity_invalid" in result.stdout
