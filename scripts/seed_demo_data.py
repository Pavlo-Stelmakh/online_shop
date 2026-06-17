"""Safely reset demo/test catalog data and seed polished demo products.

This script is intentionally gated for demo environments. It only runs when
DEMO_MODE=true is set or when --force-demo-reset is passed explicitly.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import Session, sessionmaker

# Allow running as `python scripts/seed_demo_data.py` from the repository root.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Category, Customer, Order, OrderItem, Product  # noqa: E402

DEMO_CATEGORY_NAMES = ["Electronics", "Accessories", "Office", "Home"]

DEMO_PRODUCTS = [
    {
        "name": "Wireless Mouse",
        "price": Decimal("29.99"),
        "stock": 120,
        "category": "Accessories",
        "description": "Ergonomic wireless mouse with adjustable DPI.",
    },
    {
        "name": "Mechanical Keyboard",
        "price": Decimal("89.99"),
        "stock": 75,
        "category": "Accessories",
        "description": "Compact mechanical keyboard with tactile switches.",
    },
    {
        "name": "USB-C Hub",
        "price": Decimal("49.99"),
        "stock": 90,
        "category": "Electronics",
        "description": "Multi-port USB-C hub with HDMI, USB-A and card reader.",
    },
    {
        "name": "Laptop Stand",
        "price": Decimal("39.99"),
        "stock": 65,
        "category": "Office",
        "description": "Adjustable aluminum laptop stand for comfortable work.",
    },
    {
        "name": "Noise Cancelling Headphones",
        "price": Decimal("149.99"),
        "stock": 48,
        "category": "Electronics",
        "description": "Wireless over-ear headphones with active noise cancellation.",
    },
    {
        "name": "External SSD 1TB",
        "price": Decimal("119.99"),
        "stock": 56,
        "category": "Electronics",
        "description": "Portable 1TB solid-state drive with fast USB-C transfer speeds.",
    },
    {
        "name": "Office Desk Lamp",
        "price": Decimal("34.99"),
        "stock": 82,
        "category": "Office",
        "description": "LED desk lamp with dimming control and warm/cool light modes.",
    },
    {
        "name": "Smart Plug",
        "price": Decimal("19.99"),
        "stock": 140,
        "category": "Home",
        "description": "Wi-Fi smart plug for scheduled and remote appliance control.",
    },
    {
        "name": "Monitor 27 inch",
        "price": Decimal("219.99"),
        "stock": 32,
        "category": "Electronics",
        "description": "27-inch full HD monitor with slim bezels.",
    },
    {
        "name": "Backpack",
        "price": Decimal("59.99"),
        "stock": 70,
        "category": "Accessories",
        "description": "Durable laptop backpack with organizer pockets.",
    },
]

TEST_MARKERS = ("test", "swagger", "render", "validation")


def is_demo_mode_enabled(force: bool = False) -> bool:
    return force or os.getenv("DEMO_MODE", "").strip().lower() == "true"


def _contains_any_marker(column):
    lowered = func.lower(column)
    return or_(*(lowered.like(f"%{marker}%") for marker in TEST_MARKERS))


def reset_demo_data(session: Session) -> dict[str, int]:
    demo_product_names = [product["name"] for product in DEMO_PRODUCTS]

    demo_product_ids = [
        product_id
        for (product_id,) in session.query(Product.id).filter(
            or_(
                Product.name.in_(demo_product_names),
                _contains_any_marker(Product.name),
                _contains_any_marker(Product.description),
            )
        )
    ]
    demo_customer_ids = [
        customer_id
        for (customer_id,) in session.query(Customer.id).filter(
            or_(
                _contains_any_marker(Customer.name),
                _contains_any_marker(Customer.email),
            )
        )
    ]
    demo_order_ids = set()
    if demo_customer_ids:
        demo_order_ids.update(
            order_id
            for (order_id,) in session.query(Order.id).filter(
                Order.customer_id.in_(demo_customer_ids)
            )
        )
    if demo_product_ids:
        demo_order_ids.update(
            order_id
            for (order_id,) in session.query(OrderItem.order_id).filter(
                OrderItem.product_id.in_(demo_product_ids)
            )
        )

    stats = {
        "order_items_deleted": 0,
        "orders_deleted": 0,
        "customers_deleted": 0,
        "products_deleted": 0,
        "categories_deleted": 0,
        "categories_created": 0,
        "products_created": 0,
    }

    if demo_order_ids:
        stats["order_items_deleted"] += session.query(OrderItem).filter(
            OrderItem.order_id.in_(demo_order_ids)
        ).delete(synchronize_session=False)
        stats["orders_deleted"] += session.query(Order).filter(
            Order.id.in_(demo_order_ids)
        ).delete(synchronize_session=False)

    if demo_customer_ids:
        stats["customers_deleted"] += session.query(Customer).filter(
            Customer.id.in_(demo_customer_ids)
        ).delete(synchronize_session=False)

    if demo_product_ids:
        stats["products_deleted"] += session.query(Product).filter(
            Product.id.in_(demo_product_ids)
        ).delete(synchronize_session=False)

    disposable_categories = [
        category_id
        for (category_id,) in session.query(Category.id).outerjoin(Product).filter(
            or_(
                Category.name.in_(DEMO_CATEGORY_NAMES),
                _contains_any_marker(Category.name),
            ),
            Product.id.is_(None),
        )
    ]
    if disposable_categories:
        stats["categories_deleted"] += session.query(Category).filter(
            Category.id.in_(disposable_categories)
        ).delete(synchronize_session=False)

    categories_by_name: dict[str, Category] = {}
    for category_name in DEMO_CATEGORY_NAMES:
        category = session.query(Category).filter(Category.name == category_name).one_or_none()
        if category is None:
            category = Category(name=category_name)
            session.add(category)
            session.flush()
            stats["categories_created"] += 1
        categories_by_name[category_name] = category

    for product_data in DEMO_PRODUCTS:
        category = categories_by_name[product_data["category"]]
        session.add(
            Product(
                name=product_data["name"],
                price=product_data["price"],
                description=product_data["description"],
                image_url="",
                stock=product_data["stock"],
                low_stock_threshold=5,
                category_id=category.id,
            )
        )
        stats["products_created"] += 1

    session.commit()
    return stats


def run(database_url: str) -> dict[str, int]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with SessionLocal() as session:
        return reset_demo_data(session)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely seed portfolio demo data.")
    parser.add_argument(
        "--force-demo-reset",
        action="store_true",
        help="Explicitly allow the demo reset when DEMO_MODE is not true.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not is_demo_mode_enabled(args.force_demo_reset):
        print(
            "Refusing to run demo seed. Set DEMO_MODE=true or pass "
            "--force-demo-reset. This script is only for demo databases.",
            file=sys.stderr,
        )
        return 1

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required to run demo seed.", file=sys.stderr)
        return 1

    stats = run(database_url)
    print("Demo data reset completed safely:")
    for key, value in stats.items():
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
