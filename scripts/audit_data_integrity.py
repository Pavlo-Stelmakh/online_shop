"""Read-only data integrity audit for the current database."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from database import SessionLocal  # noqa: E402


@dataclass(frozen=True)
class AuditCheck:
    code: str
    description: str
    count_sql: str
    sample_sql: str


CHECKS: Sequence[AuditCheck] = (
    AuditCheck(
        code="orders_customer_missing",
        description="orders.customer_id is NULL",
        count_sql="SELECT COUNT(*) FROM orders WHERE customer_id IS NULL",
        sample_sql="SELECT id FROM orders WHERE customer_id IS NULL ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="orders_customer_orphan",
        description="orders.customer_id references a missing customer",
        count_sql="""
            SELECT COUNT(*)
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.customer_id IS NOT NULL AND c.id IS NULL
        """,
        sample_sql="""
            SELECT o.id
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.customer_id IS NOT NULL AND c.id IS NULL
            ORDER BY o.id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="order_items_order_missing",
        description="order_items.order_id is NULL",
        count_sql="SELECT COUNT(*) FROM order_items WHERE order_id IS NULL",
        sample_sql="SELECT id FROM order_items WHERE order_id IS NULL ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="order_items_order_orphan",
        description="order_items.order_id references a missing order",
        count_sql="""
            SELECT COUNT(*)
            FROM order_items oi
            LEFT JOIN orders o ON o.id = oi.order_id
            WHERE oi.order_id IS NOT NULL AND o.id IS NULL
        """,
        sample_sql="""
            SELECT oi.id
            FROM order_items oi
            LEFT JOIN orders o ON o.id = oi.order_id
            WHERE oi.order_id IS NOT NULL AND o.id IS NULL
            ORDER BY oi.id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="order_items_product_missing",
        description="order_items.product_id is NULL",
        count_sql="SELECT COUNT(*) FROM order_items WHERE product_id IS NULL",
        sample_sql="SELECT id FROM order_items WHERE product_id IS NULL ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="order_items_product_orphan",
        description="order_items.product_id references a missing product",
        count_sql="""
            SELECT COUNT(*)
            FROM order_items oi
            LEFT JOIN products p ON p.id = oi.product_id
            WHERE oi.product_id IS NOT NULL AND p.id IS NULL
        """,
        sample_sql="""
            SELECT oi.id
            FROM order_items oi
            LEFT JOIN products p ON p.id = oi.product_id
            WHERE oi.product_id IS NOT NULL AND p.id IS NULL
            ORDER BY oi.id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="products_category_missing",
        description="products.category_id is NULL",
        count_sql="SELECT COUNT(*) FROM products WHERE category_id IS NULL",
        sample_sql="SELECT id FROM products WHERE category_id IS NULL ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="products_category_orphan",
        description="products.category_id references a missing category",
        count_sql="""
            SELECT COUNT(*)
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.category_id IS NOT NULL AND c.id IS NULL
        """,
        sample_sql="""
            SELECT p.id
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.category_id IS NOT NULL AND c.id IS NULL
            ORDER BY p.id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="customers_user_missing",
        description="customers.user_id is NULL",
        count_sql="SELECT COUNT(*) FROM customers WHERE user_id IS NULL",
        sample_sql="SELECT id FROM customers WHERE user_id IS NULL ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="customers_user_orphan",
        description="customers.user_id references a missing user",
        count_sql="""
            SELECT COUNT(*)
            FROM customers c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE c.user_id IS NOT NULL AND u.id IS NULL
        """,
        sample_sql="""
            SELECT c.id
            FROM customers c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE c.user_id IS NOT NULL AND u.id IS NULL
            ORDER BY c.id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="categories_name_missing",
        description="categories.name is NULL",
        count_sql="SELECT COUNT(*) FROM categories WHERE name IS NULL",
        sample_sql="SELECT id FROM categories WHERE name IS NULL ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="categories_name_empty",
        description="categories.name is empty after trim",
        count_sql="SELECT COUNT(*) FROM categories WHERE trim(name) = ''",
        sample_sql="SELECT id FROM categories WHERE trim(name) = '' ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="products_required_fields_missing",
        description="products.name or description is NULL",
        count_sql="""
            SELECT COUNT(*)
            FROM products
            WHERE name IS NULL OR description IS NULL
        """,
        sample_sql="""
            SELECT id
            FROM products
            WHERE name IS NULL OR description IS NULL
            ORDER BY id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="products_price_invalid",
        description="products.price is NULL or negative",
        count_sql="SELECT COUNT(*) FROM products WHERE price IS NULL OR price < 0",
        sample_sql="SELECT id FROM products WHERE price IS NULL OR price < 0 ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="products_stock_invalid",
        description="products.stock is NULL or negative",
        count_sql="SELECT COUNT(*) FROM products WHERE stock IS NULL OR stock < 0",
        sample_sql="SELECT id FROM products WHERE stock IS NULL OR stock < 0 ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="products_low_stock_threshold_invalid",
        description="products.low_stock_threshold is NULL or negative",
        count_sql="""
            SELECT COUNT(*)
            FROM products
            WHERE low_stock_threshold IS NULL OR low_stock_threshold < 0
        """,
        sample_sql="""
            SELECT id
            FROM products
            WHERE low_stock_threshold IS NULL OR low_stock_threshold < 0
            ORDER BY id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="orders_total_price_invalid",
        description="orders.total_price is NULL or negative",
        count_sql="SELECT COUNT(*) FROM orders WHERE total_price IS NULL OR total_price < 0",
        sample_sql="SELECT id FROM orders WHERE total_price IS NULL OR total_price < 0 ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="order_items_quantity_invalid",
        description="order_items.quantity is NULL or not positive",
        count_sql="SELECT COUNT(*) FROM order_items WHERE quantity IS NULL OR quantity <= 0",
        sample_sql="SELECT id FROM order_items WHERE quantity IS NULL OR quantity <= 0 ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="users_required_fields_missing",
        description="users.username, email, or hashed_password is NULL",
        count_sql="""
            SELECT COUNT(*)
            FROM users
            WHERE username IS NULL OR email IS NULL OR hashed_password IS NULL
        """,
        sample_sql="""
            SELECT id
            FROM users
            WHERE username IS NULL OR email IS NULL OR hashed_password IS NULL
            ORDER BY id
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="users_role_invalid",
        description="users.role is NULL or outside admin/customer",
        count_sql="SELECT COUNT(*) FROM users WHERE role IS NULL OR role NOT IN ('admin', 'customer')",
        sample_sql="SELECT id FROM users WHERE role IS NULL OR role NOT IN ('admin', 'customer') ORDER BY id LIMIT 5",
    ),
    AuditCheck(
        code="users_username_duplicate",
        description="duplicate users.username values",
        count_sql="""
            SELECT COUNT(*)
            FROM (
                SELECT username
                FROM users
                WHERE username IS NOT NULL
                GROUP BY username
                HAVING COUNT(*) > 1
            ) duplicates
        """,
        sample_sql="""
            SELECT username
            FROM users
            WHERE username IS NOT NULL
            GROUP BY username
            HAVING COUNT(*) > 1
            ORDER BY username
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="users_email_duplicate",
        description="duplicate users.email values",
        count_sql="""
            SELECT COUNT(*)
            FROM (
                SELECT email
                FROM users
                WHERE email IS NOT NULL
                GROUP BY email
                HAVING COUNT(*) > 1
            ) duplicates
        """,
        sample_sql="""
            SELECT email
            FROM users
            WHERE email IS NOT NULL
            GROUP BY email
            HAVING COUNT(*) > 1
            ORDER BY email
            LIMIT 5
        """,
    ),
    AuditCheck(
        code="customers_email_duplicate",
        description="duplicate customers.email values",
        count_sql="""
            SELECT COUNT(*)
            FROM (
                SELECT email
                FROM customers
                WHERE email IS NOT NULL
                GROUP BY email
                HAVING COUNT(*) > 1
            ) duplicates
        """,
        sample_sql="""
            SELECT email
            FROM customers
            WHERE email IS NOT NULL
            GROUP BY email
            HAVING COUNT(*) > 1
            ORDER BY email
            LIMIT 5
        """,
    ),
)


def scalar_count(session, sql: str) -> int:
    value = session.execute(text(sql)).scalar_one()
    return int(value or 0)


def sample_values(session, sql: str) -> list[str]:
    rows = session.execute(text(sql)).fetchall()
    return [str(row[0]) for row in rows]


def run_audit() -> int:
    problems: list[tuple[AuditCheck, int, list[str]]] = []

    print("Data integrity audit")
    print("====================")
    print(f"Checks run: {len(CHECKS)}")

    session = SessionLocal()
    try:
        for check in CHECKS:
            count = scalar_count(session, check.count_sql)
            if count:
                problems.append((check, count, sample_values(session, check.sample_sql)))
    except SQLAlchemyError as exc:
        print("Result: FAIL")
        print("Audit could not complete against the configured database.")
        print(f"Database error: {exc}")
        return 1
    finally:
        session.rollback()
        session.close()

    if not problems:
        print("Result: PASS")
        print("No data integrity problems found.")
        return 0

    print("Result: FAIL")
    print(f"Problems found: {len(problems)}")
    print()

    for check, count, samples in problems:
        print(f"[{check.code}] {check.description}")
        print(f"  matching rows/groups: {count}")
        if samples:
            print(f"  sample ids/values: {', '.join(samples)}")
        print()

    return 1


if __name__ == "__main__":
    raise SystemExit(run_audit())
