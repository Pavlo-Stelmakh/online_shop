import os
import re
from pathlib import Path
import tempfile
import time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
import main as main_module
from models import Category, Customer, Order, Product, User
from routes.admin import (
    ADMIN_SESSION_COOKIE_NAME,
    create_admin_session_token,
)


TEST_DB_PATH = Path(tempfile.gettempdir()) / f"online_shop_test_{os.getpid()}.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    TEST_DB_PATH.unlink(missing_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app = main_module.app
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def create_registered_user(role: str = "admin"):
    username = f"{role}_user_{time.time()}"
    email = f"{username}@example.com"
    password = "123456"

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )

    assert register_response.status_code == 200

    db = TestingSessionLocal()

    try:
        user = db.query(User).filter(
            User.username == username
        ).first()

        if role == "admin":
            user.role = "admin"
            db.commit()
            db.refresh(user)

        user_id = user.id
        user_role = user.role
    finally:
        db.close()

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "password": password,
        "role": user_role
    }


def get_auth_headers(role: str = "admin"):
    user = create_registered_user(role=role)

    login_response = client.post(
        "/auth/login",
        data={
            "username": user["username"],
            "password": user["password"]
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def extract_admin_csrf_token(response):
    match = re.search(
        r'name="csrf_token" value="([^"]+)"',
        response.text
    )

    assert match is not None

    return match.group(1)


def get_admin_ui_csrf_token(admin_client, path: str = "/admin/products/create"):
    response = admin_client.get(path)

    assert response.status_code == 200

    return extract_admin_csrf_token(response)


def get_admin_ui_client():
    admin_user = create_registered_user(role="admin")
    admin_client = TestClient(app)

    response = admin_client.post(
        "/admin/login",
        data={
            "username": admin_user["username"],
            "password": admin_user["password"]
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    assert ADMIN_SESSION_COOKIE_NAME in admin_client.cookies

    return admin_client

def create_test_category():
    headers = get_auth_headers()

    response = client.post(
        "/categories",
        json={
            "name": f"Test Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 200

    return response.json()

def create_test_product(
    stock: int = 10,
    price: float = 100,
    low_stock_threshold: int = 5
):
    category = create_test_category()
    headers = get_auth_headers(role="admin")

    response = client.post(
    "/products",
        json={
            "name": f"Test Product {time.time()}",
            "price": price,
            "description": "Test product description",
            "stock": stock,
            "low_stock_threshold": low_stock_threshold,
            "category_id": category["id"]
        },
        headers=headers
    )

    assert response.status_code == 200

    return response.json()


def create_test_customer(headers=None):
    if headers is None:
        headers = get_auth_headers(role="customer")

    response = client.post(
        "/customers",
        json={
            "name": f"Test Customer {time.time()}",
            "email": f"customer_{time.time()}@example.com",
            "phone": "+380501112233"
        },
        headers=headers
    )

    assert response.status_code == 200

    return response.json()

def create_test_order(
    product_id: int,
    customer_id: int,
    quantity: int = 2,
    headers=None
):
    if headers is None:
        headers = get_auth_headers(role="customer")

    response = client.post(
        "/orders",
        json={
            "customer_id": customer_id,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": quantity
                }
            ]
        },
        headers=headers
    )

    assert response.status_code == 200

    return response.json()

def cancel_order(order_id: int):
    headers = get_auth_headers(role="admin")

    response = client.put(
        f"/orders/{order_id}/status",
        params={
            "status": "cancelled"
        },
        headers=headers
    )

    if response.status_code == 422:
        response = client.put(
            f"/orders/{order_id}/status",
            params={
                "new_status": "cancelled"
            },
            headers=headers
        )

    assert response.status_code == 200

    return response.json()


def build_isolated_admin_dashboard_response(
    order_totals_by_status,
    products=None,
):
    dashboard_db_path = Path(tempfile.gettempdir()) / f"online_shop_admin_dashboard_{time.time_ns()}.db"
    dashboard_engine = create_engine(
        f"sqlite:///{dashboard_db_path}",
        connect_args={"check_same_thread": False},
    )
    DashboardSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=dashboard_engine,
    )
    Base.metadata.create_all(bind=dashboard_engine)
    db = DashboardSessionLocal()

    def override_dashboard_db():
        dashboard_db = DashboardSessionLocal()

        try:
            yield dashboard_db
        finally:
            dashboard_db.close()

    previous_override = app.dependency_overrides.get(get_db)

    try:
        admin_user = User(
            username=f"dashboard_admin_{time.time_ns()}",
            email=f"dashboard_admin_{time.time_ns()}@example.com",
            hashed_password="test",
            role="admin",
        )
        customer_user = User(
            username=f"dashboard_customer_{time.time_ns()}",
            email=f"dashboard_customer_{time.time_ns()}@example.com",
            hashed_password="test",
            role="customer",
        )
        db.add_all([admin_user, customer_user])
        db.commit()
        db.refresh(admin_user)
        db.refresh(customer_user)

        category = Category(name=f"Dashboard Category {time.time_ns()}")
        db.add(category)
        db.commit()
        db.refresh(category)

        if products is None:
            products = [
                {
                    "name": f"Dashboard Low Stock Product {time.time_ns()}",
                    "price": Decimal("1.00"),
                    "description": "Dashboard low stock product",
                    "stock": 2,
                    "low_stock_threshold": 5,
                },
                {
                    "name": f"Dashboard Product {time.time_ns()}",
                    "price": Decimal("2.00"),
                    "description": "Dashboard product",
                    "stock": 10,
                    "low_stock_threshold": 5,
                },
            ]

        db.add_all([
            Product(
                name=product["name"],
                price=product["price"],
                description=product["description"],
                stock=product["stock"],
                low_stock_threshold=product["low_stock_threshold"],
                category_id=category.id,
            )
            for product in products
        ])

        customer = Customer(
            user_id=customer_user.id,
            name="Dashboard Customer",
            email=f"dashboard_customer_{time.time_ns()}@example.com",
            phone="+380501112233",
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        for status, totals in order_totals_by_status.items():
            for total in totals:
                db.add(
                    Order(
                        customer_id=customer.id,
                        status=status,
                        total_price=Decimal(total),
                    )
                )

        db.commit()

        app.dependency_overrides[get_db] = override_dashboard_db
        dashboard_client = TestClient(app)
        dashboard_client.cookies.set(
            ADMIN_SESSION_COOKIE_NAME,
            create_admin_session_token(admin_user),
        )

        return dashboard_client.get("/admin")
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

        db.close()
        Base.metadata.drop_all(bind=dashboard_engine)
        dashboard_engine.dispose()
        dashboard_db_path.unlink(missing_ok=True)

def build_isolated_stats_response(order_totals_by_status):
    stats_db_path = Path(tempfile.gettempdir()) / f"online_shop_stats_{time.time_ns()}.db"
    stats_engine = create_engine(
        f"sqlite:///{stats_db_path}",
        connect_args={"check_same_thread": False},
    )
    StatsSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=stats_engine,
    )
    Base.metadata.create_all(bind=stats_engine)
    db = StatsSessionLocal()

    try:
        user = User(
            username=f"stats_user_{time.time_ns()}",
            email=f"stats_user_{time.time_ns()}@example.com",
            hashed_password="test",
            role="customer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        customer = Customer(
            user_id=user.id,
            name="Stats Customer",
            email=f"stats_customer_{time.time_ns()}@example.com",
            phone="+380501112233",
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        for status, totals in order_totals_by_status.items():
            for total in totals:
                db.add(
                    Order(
                        customer_id=customer.id,
                        status=status,
                        total_price=Decimal(total),
                    )
                )

        db.commit()

        from routes.stats import get_stats_summary

        return get_stats_summary(
            db=db,
            current_user=User(role="admin"),
        )
    finally:
        db.close()
        Base.metadata.drop_all(bind=stats_engine)
        stats_engine.dispose()
        stats_db_path.unlink(missing_ok=True)
