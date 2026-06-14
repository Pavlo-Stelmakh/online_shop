import importlib
import os
from pathlib import Path
import tempfile
import time
from decimal import Decimal
from datetime import datetime, timedelta, UTC

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
import main as main_module
from auth import SECRET_KEY, ALGORITHM
from models import Category, Customer, Order, OrderItem, Product, User
from routes.admin import (
    ADMIN_SESSION_COOKIE_NAME,
    ADMIN_SESSION_TOKEN_TYPE,
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


def test_importing_app_does_not_create_database_tables(monkeypatch):
    def fail_create_all(*args, **kwargs):
        raise AssertionError("Application import must not create database tables")

    monkeypatch.setattr(Base.metadata, "create_all", fail_create_all)

    reloaded_main = importlib.reload(main_module)

    assert reloaded_main.app is not None


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


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Online Shop API is running",
        "docs": "/docs",
        "health": "/health"
    }


def test_create_category():
    headers = get_auth_headers()

    response = client.post(
        "/categories",
        json={
            "name": f"Test Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["name"].startswith("Test Category")


def test_create_product():
    headers = get_auth_headers()

    category = create_test_category()

    response = client.post(
        "/products",
        json={
            "name": f"Test Product {time.time()}",
            "price": 100,
            "description": "Test product description",
            "stock": 10,
            "category_id": category["id"]
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["price"] == 100
    assert data["stock"] == 10
    assert data["category_id"] == category["id"]

def test_create_customer():
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

    data = response.json()

    assert "id" in data
    assert "user_id" in data
    assert "name" in data
    assert "email" in data

def test_create_order_and_reduce_stock():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=2,
        headers=customer_headers
    )

    assert "id" in order
    assert order["customer_id"] == customer["id"]
    assert order["total_price"] == 200
    assert order["items"][0]["unit_price"] == 100

    product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200

    updated_product = product_response.json()

    assert updated_product["stock"] == 8


def test_order_item_unit_price_is_snapshot_when_product_price_changes():
    product = create_test_product(stock=10, price=12.5)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["total_price"] == 37.5
    assert order["items"][0]["unit_price"] == 12.5

    admin_headers = get_auth_headers(role="admin")
    update_response = client.put(
        f"/products/{product['id']}",
        json={
            "name": product["name"],
            "price": 99.99,
            "description": product["description"],
            "stock": 7,
            "low_stock_threshold": product["low_stock_threshold"],
            "category_id": product["category_id"],
        },
        headers=admin_headers,
    )

    assert update_response.status_code == 200

    order_response = client.get(f"/orders/{order['id']}", headers=customer_headers)

    assert order_response.status_code == 200
    persisted_order = order_response.json()
    assert persisted_order["total_price"] == 37.5
    assert persisted_order["items"][0]["unit_price"] == 12.5
    assert persisted_order["items"][0]["product"]["price"] == 99.99

def test_cancel_order_returns_stock():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers
    )

    product_after_order_response = client.get(f"/products/{product['id']}")

    assert product_after_order_response.status_code == 200
    assert product_after_order_response.json()["stock"] == 7

    cancelled_order = cancel_order(order["id"])

    assert cancelled_order["status"] == "cancelled"

    product_after_cancel_response = client.get(f"/products/{product['id']}")

    assert product_after_cancel_response.status_code == 200
    assert product_after_cancel_response.json()["stock"] == 10


def test_register_user():
    username = f"test_user_{time.time()}"
    email = f"{username}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "123456"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == username
    assert data["email"] == email
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_login_user():
    username = f"login_user_{time.time()}"
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

    login_response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user():
    username = f"me_user_{time.time()}"
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

    login_response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert me_response.status_code == 200

    data = me_response.json()

    assert data["username"] == username
    assert data["email"] == email
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_create_category_requires_auth():
    response = client.post(
        "/categories",
        json={
            "name": f"Protected Category {time.time()}"
        }
    )

    assert response.status_code == 401


def test_create_category_with_auth():
    headers = get_auth_headers()

    response = client.post(
        "/categories",
        json={
            "name": f"Auth Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["name"].startswith("Auth Category")

def test_create_product_requires_auth():
    category = create_test_category()

    response = client.post(
        "/products",
        json={
            "name": f"Protected Product {time.time()}",
            "price": 100,
            "description": "Protected product test",
            "stock": 10,
            "category_id": category["id"]
        }
    )

    assert response.status_code == 401


def test_update_product_requires_auth():
    product = create_test_product()

    response = client.put(
        f"/products/{product['id']}",
        json={
            "name": "Updated Product",
            "price": 150,
            "description": "Updated description",
            "stock": 20,
            "category_id": product["category_id"]
        }
    )

    assert response.status_code == 401

def test_delete_product_requires_auth():
    product = create_test_product()

    response = client.delete(
        f"/products/{product['id']}"
    )

    assert response.status_code == 401


def test_customer_cannot_create_category():
    headers = get_auth_headers(role="customer")

    response = client.post(
        "/categories",
        json={
            "name": f"Customer Forbidden Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_create_category():
    headers = get_auth_headers(role="admin")

    response = client.post(
        "/categories",
        json={
            "name": f"Admin Allowed Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["name"].startswith("Admin Allowed Category")


def test_customer_cannot_create_product():
    category = create_test_category()
    headers = get_auth_headers(role="customer")

    response = client.post(
        "/products",
        json={
            "name": f"Customer Forbidden Product {time.time()}",
            "price": 100,
            "description": "Customer should not create product",
            "stock": 10,
            "category_id": category["id"]
        },
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_create_product():
    category = create_test_category()
    headers = get_auth_headers(role="admin")

    response = client.post(
        "/products",
        json={
            "name": f"Admin Allowed Product {time.time()}",
            "price": 100,
            "description": "Admin can create product",
            "stock": 10,
            "category_id": category["id"]
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["name"].startswith("Admin Allowed Product")
    assert data["stock"] == 10


def test_customer_cannot_update_product():
    product = create_test_product()
    headers = get_auth_headers(role="customer")

    response = client.put(
        f"/products/{product['id']}",
        json={
            "name": "Customer Updated Product",
            "price": 200,
            "description": "Customer should not update product",
            "stock": 20,
            "category_id": product["category_id"]
        },
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

def test_customer_cannot_delete_product():
    product = create_test_product()
    headers = get_auth_headers(role="customer")

    response = client.delete(
        f"/products/{product['id']}",
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_api_cannot_delete_product_used_in_order_items():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/products/{product['id']}",
        headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Product cannot be deleted because it is used in orders"
    )

    db = TestingSessionLocal()

    try:
        product_exists = db.query(Product).filter(
            Product.id == product["id"]
        ).first() is not None
        order_item_exists = db.query(OrderItem).filter(
            OrderItem.order_id == order["id"],
            OrderItem.product_id == product["id"]
        ).first() is not None
    finally:
        db.close()

    assert product_exists
    assert order_item_exists


def test_admin_api_can_delete_product_with_no_order_items():
    product = create_test_product(stock=10, price=100)
    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/products/{product['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Product deleted successfully"

    db = TestingSessionLocal()

    try:
        product_exists = db.query(Product).filter(
            Product.id == product["id"]
        ).first() is not None
    finally:
        db.close()

    assert not product_exists


def test_admin_cannot_delete_customer_who_has_orders():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/customers/{customer['id']}",
        headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Customer cannot be deleted because they have orders"
    )

    db = TestingSessionLocal()

    try:
        customer_exists = db.query(Customer).filter(
            Customer.id == customer["id"]
        ).first() is not None
        order_exists = db.query(Order).filter(
            Order.id == order["id"]
        ).first() is not None
    finally:
        db.close()

    assert customer_exists
    assert order_exists


def test_admin_can_delete_customer_with_no_orders():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/customers/{customer['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Customer deleted successfully"

    db = TestingSessionLocal()

    try:
        customer_exists = db.query(Customer).filter(
            Customer.id == customer["id"]
        ).first() is not None
    finally:
        db.close()

    assert not customer_exists


def test_admin_cannot_physically_delete_order_with_order_items():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/orders/{order['id']}",
        headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Order cannot be deleted because it has order items"
    )

    db = TestingSessionLocal()

    try:
        order_exists = db.query(Order).filter(
            Order.id == order["id"]
        ).first() is not None
        order_item_exists = db.query(OrderItem).filter(
            OrderItem.order_id == order["id"]
        ).first() is not None
    finally:
        db.close()

    assert order_exists
    assert order_item_exists

def test_create_order_requires_auth():
    product = create_test_product()
    customer = create_test_customer()

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1
                }
            ]
        }
    )

    assert response.status_code == 401

def test_customer_can_create_order():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["customer_id"] == customer["id"]
    assert data["total_price"] == 200
    assert data["status"] == "new"

def test_customer_cannot_get_all_orders():
    headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders",
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

def test_admin_can_get_all_orders():
    headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert "total" in body
    assert "skip" in body
    assert "limit" in body
    assert "items" in body
    assert isinstance(body["items"], list)


def test_customer_cannot_update_order_status():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    response = client.put(
        f"/orders/{order['id']}/status",
        params={
            "status": "paid"
        },
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_update_order_status():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        f"/orders/{order['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "paid"


def test_customer_cannot_create_order_for_another_customer():
    product = create_test_product(stock=10, price=100)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer_2["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1
                }
            ]
        },
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You can create orders only for your own customer profile"
    )

def test_customer_can_get_own_profile():
    headers = get_auth_headers(role="customer")

    customer = create_test_customer(headers=headers)

    response = client.get(
        "/customers/me",
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == customer["id"]
    assert data["user_id"] == customer["user_id"]
    assert data["email"] == customer["email"]


def test_customer_me_without_profile_returns_404():
    headers = get_auth_headers(role="customer")

    response = client.get(
        "/customers/me",
        headers=headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer profile not found"

def test_customer_me_requires_auth():
    response = client.get("/customers/me")

    assert response.status_code == 401


def test_get_products_with_pagination():
    create_test_product(stock=10, price=100)
    create_test_product(stock=10, price=200)
    create_test_product(stock=10, price=300)

    response = client.get(
        "/products",
        params={
            "skip": 0,
            "limit": 2
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 2


def test_get_products_filter_by_category():
    category_1 = create_test_category()
    category_2 = create_test_category()

    headers = get_auth_headers(role="admin")

    product_1_response = client.post(
        "/products",
        json={
            "name": f"Category One Product {time.time()}",
            "price": 100,
            "description": "Product in category 1",
            "stock": 10,
            "category_id": category_1["id"]
        },
        headers=headers
    )

    assert product_1_response.status_code == 200

    product_2_response = client.post(
        "/products",
        json={
            "name": f"Category Two Product {time.time()}",
            "price": 200,
            "description": "Product in category 2",
            "stock": 10,
            "category_id": category_2["id"]
        },
        headers=headers
    )

    assert product_2_response.status_code == 200

    response = client.get(
        "/products",
        params={
            "category_id": category_1["id"],
            "skip": 0,
            "limit": 10
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    for product in data:
        assert product["category_id"] == category_1["id"]


def test_get_products_filter_by_price():
    create_test_product(stock=10, price=100)
    create_test_product(stock=10, price=300)
    create_test_product(stock=10, price=700)

    response = client.get(
        "/products",
        params={
            "min_price": 100,
            "max_price": 500,
            "skip": 0,
            "limit": 20
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    for product in data:
        assert product["price"] >= 100
        assert product["price"] <= 500


def test_get_products_filter_in_stock():
    create_test_product(stock=10, price=100)
    create_test_product(stock=0, price=200)

    response = client.get(
        "/products",
        params={
            "in_stock": True,
            "skip": 0,
            "limit": 20
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    for product in data:
        assert product["stock"] > 0


def test_get_products_sort_by_price_asc():
    create_test_product(stock=10, price=300)
    create_test_product(stock=10, price=100)
    create_test_product(stock=10, price=200)

    response = client.get(
        "/products",
        params={
            "sort_by": "price",
            "sort_order": "asc",
            "skip": 0,
            "limit": 20
        }
    )

    assert response.status_code == 200

    data = response.json()

    prices = [product["price"] for product in data]

    assert prices == sorted(prices)


def test_get_products_sort_by_price_desc():
    create_test_product(stock=10, price=300)
    create_test_product(stock=10, price=100)
    create_test_product(stock=10, price=200)

    response = client.get(
        "/products",
        params={
            "sort_by": "price",
            "sort_order": "desc",
            "skip": 0,
            "limit": 20
        }
    )

    assert response.status_code == 200

    data = response.json()

    prices = [product["price"] for product in data]

    assert prices == sorted(prices, reverse=True)


def test_get_products_invalid_sort_by():
    response = client.get(
        "/products",
        params={
            "sort_by": "wrong_field",
            "sort_order": "asc"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid sort_by value"


def test_get_products_invalid_sort_order():
    response = client.get(
        "/products",
        params={
            "sort_by": "price",
            "sort_order": "wrong_order"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid sort_order value"


def test_get_products_catalog_response():
    create_test_product(stock=10, price=300)
    create_test_product(stock=10, price=100)
    create_test_product(stock=0, price=200)

    response = client.get(
        "/products/catalog",
        params={
            "skip": 0,
            "limit": 2,
            "in_stock": True,
            "sort_by": "price",
            "sort_order": "asc"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert "items" in data

    assert data["skip"] == 0
    assert data["limit"] == 2
    assert isinstance(data["total"], int)
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 2

    for product in data["items"]:
        assert product["stock"] > 0

    prices = [product["price"] for product in data["items"]]
    assert prices == sorted(prices)


def test_get_products_invalid_negative_skip():
    response = client.get(
        "/products",
        params={
            "skip": -1,
            "limit": 10
        }
    )

    assert response.status_code == 422


def test_get_products_invalid_limit_zero():
    response = client.get(
        "/products",
        params={
            "skip": 0,
            "limit": 0
        }
    )

    assert response.status_code == 422


def test_get_products_invalid_limit_too_large():
    response = client.get(
        "/products",
        params={
            "skip": 0,
            "limit": 101
        }
    )

    assert response.status_code == 422


def test_get_products_invalid_negative_min_price():
    response = client.get(
        "/products",
        params={
            "min_price": -1
        }
    )

    assert response.status_code == 422


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_user_cannot_create_admin():
    response = client.post(
        "/auth/register",
        json={
            "username": f"not_admin_{time.time()}",
            "email": f"not_admin_{time.time()}@example.com",
            "password": "123456",
            "role": "admin"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["role"] == "customer"

def test_create_product_with_image_url():
    headers = get_auth_headers(role="admin")

    category_response = client.post(
        "/categories",
        json={
            "name": f"Image Category {time.time()}"
        },
        headers=headers
    )

    assert category_response.status_code == 200

    category_id = category_response.json()["id"]

    product_response = client.post(
        "/products",
        json={
            "name": f"Image Product {time.time()}",
            "price": 100,
            "description": "Product with image URL",
            "image_url": "https://example.com/product-image.jpg",
            "stock": 5,
            "category_id": category_id
        },
        headers=headers
    )

    assert product_response.status_code == 200

    data = product_response.json()

    assert data["image_url"] == "https://example.com/product-image.jpg"

def test_create_product_without_image_url():
    headers = get_auth_headers(role="admin")

    category_response = client.post(
        "/categories",
        json={
            "name": f"No Image Category {time.time()}"
        },
        headers=headers
    )

    assert category_response.status_code == 200

    category_id = category_response.json()["id"]

    product_response = client.post(
        "/products",
        json={
            "name": f"No Image Product {time.time()}",
            "price": 150,
            "description": "Product without image URL",
            "stock": 3,
            "category_id": category_id
        },
        headers=headers
    )

    assert product_response.status_code == 200

    data = product_response.json()

    assert data["image_url"] is None


def test_admin_can_get_low_stock_products():
    create_test_product(stock=2, price=100)
    create_test_product(stock=10, price=200)

    headers = get_auth_headers(role="admin")

    response = client.get(
        "/products/low-stock",
        params={
            "threshold": 5
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    for product in data:
        assert product["stock"] <= 5


def test_customer_cannot_get_low_stock_products():
    headers = get_auth_headers(role="customer")

    response = client.get(
        "/products/low-stock",
        params={
            "threshold": 5
        },
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_low_stock_requires_auth():
    response = client.get(
        "/products/low-stock",
        params={
            "threshold": 5
        }
    )

    assert response.status_code == 401


def test_low_stock_invalid_negative_threshold():
    headers = get_auth_headers(role="admin")

    response = client.get(
        "/products/low-stock",
        params={
            "threshold": -1
        },
        headers=headers
    )

    assert response.status_code == 422


def test_customer_can_get_own_orders():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=2,
        headers=customer_headers
    )

    response = client.get(
        "/orders/my",
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids

    for item in data:
        assert item["customer_id"] == customer["id"]


def test_customer_cannot_get_other_customer_orders_in_my_orders():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer_1["id"],
        quantity=1,
        headers=customer_1_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer_2["id"],
        quantity=1,
        headers=customer_2_headers
    )

    response = client.get(
        "/orders/my",
        headers=customer_1_headers
    )

    assert response.status_code == 200

    data = response.json()

    order_ids = [item["id"] for item in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for item in data:
        assert item["customer_id"] == customer_1["id"]


def test_my_orders_requires_auth():
    response = client.get("/orders/my")

    assert response.status_code == 401


def test_my_orders_without_customer_profile_returns_404():
    headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders/my",
        headers=headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer profile not found"


def test_customer_can_get_own_order_by_id():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    response = client.get(
        f"/orders/{order['id']}",
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order["id"]
    assert data["customer_id"] == customer["id"]


def test_customer_cannot_get_other_customer_order_by_id():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    create_test_order(
        product_id=product_1["id"],
        customer_id=customer_1["id"],
        quantity=1,
        headers=customer_1_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer_2["id"],
        quantity=1,
        headers=customer_2_headers
    )

    response = client.get(
        f"/orders/{order_2['id']}",
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_admin_can_get_any_order_by_id():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        f"/orders/{order['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order["id"]


def test_get_order_by_id_requires_auth():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    response = client.get(f"/orders/{order['id']}")

    assert response.status_code == 401


def test_admin_can_filter_orders_by_status():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order_2['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "status": "new"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [order["id"] for order in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for order in data:
        assert order["status"] == "new"


def test_admin_can_filter_paid_orders():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids

    for item in data:
        assert item["status"] == "paid"


def test_get_orders_invalid_status_returns_400():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "status": "wrong_status"
        },
        headers=admin_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid order status"


def test_customer_cannot_get_all_orders_with_status_filter():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders",
        params={
            "status": "new"
        },
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_filter_orders_by_customer_id():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer_1["id"],
        quantity=1,
        headers=customer_1_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer_2["id"],
        quantity=1,
        headers=customer_2_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "customer_id": customer_1["id"]
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [order["id"] for order in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for order in data:
        assert order["customer_id"] == customer_1["id"]


def test_admin_can_filter_orders_by_status_and_customer_id():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order_2['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "customer_id": customer["id"],
            "status": "new"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [order["id"] for order in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for order in data:
        assert order["customer_id"] == customer["id"]
        assert order["status"] == "new"


def test_admin_filter_orders_by_unknown_customer_id_returns_empty_list():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "customer_id": 999999
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()

    assert body["items"] == []
    assert body["total"] == 0


def test_customer_cannot_filter_orders_by_customer_id():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders",
        params={
            "customer_id": 1
        },
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_filter_orders_by_date_from():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    today = order["created_at"][:10]

    response = client.get(
        "/orders",
        params={
            "date_from": today
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids


def test_admin_can_filter_orders_by_date_to():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    today = order["created_at"][:10]

    response = client.get(
        "/orders",
        params={
            "date_to": today
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids


def test_admin_can_filter_orders_by_status_customer_and_date_range():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    today = order["created_at"][:10]

    response = client.get(
        "/orders",
        params={
            "status": "new",
            "customer_id": customer["id"],
            "date_from": today,
            "date_to": today
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids

    for item in data:
        assert item["status"] == "new"
        assert item["customer_id"] == customer["id"]
        assert item["created_at"][:10] == today


def test_get_orders_invalid_date_format_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "date_from": "wrong-date"
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_admin_can_get_orders_with_pagination():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)
    product_3 = create_test_product(stock=10, price=300)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    create_test_order(
        product_id=product_3["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": 0,
            "limit": 2
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    assert body["skip"] == 0
    assert body["limit"] == 2
    assert isinstance(data, list)
    assert len(data) <= 2


def test_admin_can_filter_orders_by_status_with_pagination():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)
    product_3 = create_test_product(stock=10, price=300)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_3 = create_test_order(
        product_id=product_3["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order_3['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "status": "new",
            "skip": 0,
            "limit": 2
        },
        headers=admin_headers
    )

    assert response.status_code == 200
    
    body = response.json()
    data = body["items"]

    assert body["skip"] == 0
    assert body["limit"] == 2
    assert isinstance(data, list)
    assert len(data) <= 2

    for order in data:
        assert order["status"] == "new"

    order_ids = [order["id"] for order in data]

    assert order_3["id"] not in order_ids


def test_get_orders_invalid_negative_skip_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": -1,
            "limit": 10
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_get_orders_invalid_limit_zero_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": 0,
            "limit": 0
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_get_orders_invalid_limit_too_large_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": 0,
            "limit": 101
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_create_order_with_empty_items_returns_400():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": []
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Order must contain at least one item"


def test_create_order_with_zero_quantity_returns_400():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 0
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid quantity"


def test_create_order_with_negative_quantity_returns_400():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": -1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid quantity"


def test_create_order_with_unknown_product_returns_404():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": 999999,
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product with id 999999 not found"


def test_create_order_with_not_enough_stock_returns_400():
    product = create_test_product(stock=1, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Not enough stock for product {product['name']}"


def test_invalid_multi_item_order_does_not_reduce_stock():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                },
                {
                    "product_id": 999999,
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product with id 999999 not found"

    product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 10


def test_invalid_multi_item_order_does_not_create_order():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_headers = get_auth_headers(role="admin")

    before_response = client.get(
        "/orders",
        params={
            "customer_id": customer["id"]
        },
        headers=admin_headers
    )

    assert before_response.status_code == 200

    before_total = before_response.json()["total"]

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                },
                {
                    "product_id": 999999,
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product with id 999999 not found"

    after_response = client.get(
        "/orders",
        params={
            "customer_id": customer["id"]
        },
        headers=admin_headers
    )

    assert after_response.status_code == 200

    after_total = after_response.json()["total"]

    assert after_total == before_total


def test_valid_multi_item_order_calculates_total_price_correctly():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=250)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product_1["id"],
                    "quantity": 2
                },
                {
                    "product_id": product_2["id"],
                    "quantity": 3
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_price"] == 950


def test_valid_multi_item_order_reduces_stock_for_all_products():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=250)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product_1["id"],
                    "quantity": 2
                },
                {
                    "product_id": product_2["id"],
                    "quantity": 3
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 200

    product_1_response = client.get(f"/products/{product_1['id']}")
    product_2_response = client.get(f"/products/{product_2['id']}")

    assert product_1_response.status_code == 200
    assert product_2_response.status_code == 200

    assert product_1_response.json()["stock"] == 8
    assert product_2_response.json()["stock"] == 7


def test_create_order_with_duplicate_product_returns_400():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                },
                {
                    "product_id": product["id"],
                    "quantity": 3
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Duplicate product in order items"


def test_update_product_with_negative_stock_returns_422():
    product = create_test_product(stock=10, price=100)
    category = create_test_category()
    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        f"/products/{product['id']}",
        json={
            "name": "Updated Product",
            "price": 100,
            "description": "Updated product description",
            "image_url": None,
            "stock": -1,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_update_product_with_zero_price_returns_422():
    product = create_test_product(stock=10, price=100)
    category = create_test_category()
    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        f"/products/{product['id']}",
        json={
            "name": "Updated Product",
            "price": 0,
            "description": "Updated product description",
            "image_url": None,
            "stock": 10,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_update_product_with_empty_name_returns_422():
    product = create_test_product(stock=10, price=100)
    category = create_test_category()
    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        f"/products/{product['id']}",
        json={
            "name": "",
            "price": 100,
            "description": "Updated product description",
            "image_url": None,
            "stock": 10,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_update_product_with_unknown_category_returns_404():
    product = create_test_product(stock=10, price=100)
    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        f"/products/{product['id']}",
        json={
            "name": "Updated Product",
            "price": 100,
            "description": "Updated product description",
            "image_url": None,
            "stock": 10,
            "category_id": 999999
        },
        headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_products_catalog_search_by_name():
    category = create_test_category()
    admin_headers = get_auth_headers(role="admin")

    product_response = client.post(
        "/products",
        json={
            "name": f"Searchable Mouse {time.time()}",
            "price": 100,
            "description": "Regular product description",
            "image_url": None,
            "stock": 10,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert product_response.status_code == 200

    product = product_response.json()

    response = client.get(
        "/products/catalog",
        params={
            "search": "Mouse"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "total" in data
    assert "items" in data

    product_ids = [item["id"] for item in data["items"]]

    assert product["id"] in product_ids


def test_products_catalog_search_by_description():
    category = create_test_category()
    admin_headers = get_auth_headers(role="admin")

    product_response = client.post(
        "/products",
        json={
            "name": f"Regular Product {time.time()}",
            "price": 100,
            "description": "Wireless keyboard for search test",
            "image_url": None,
            "stock": 10,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert product_response.status_code == 200

    product = product_response.json()

    response = client.get(
        "/products/catalog",
        params={
            "search": "Wireless"
        }
    )

    assert response.status_code == 200

    data = response.json()

    product_ids = [item["id"] for item in data["items"]]

    assert product["id"] in product_ids


def test_products_catalog_search_with_in_stock_filter():
    category = create_test_category()
    admin_headers = get_auth_headers(role="admin")

    in_stock_response = client.post(
        "/products",
        json={
            "name": f"Search Filter Product In Stock {time.time()}",
            "price": 100,
            "description": "Product for search and stock filter",
            "image_url": None,
            "stock": 5,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert in_stock_response.status_code == 200

    out_of_stock_response = client.post(
        "/products",
        json={
            "name": f"Search Filter Product Out Of Stock {time.time()}",
            "price": 100,
            "description": "Product for search and stock filter",
            "image_url": None,
            "stock": 0,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert out_of_stock_response.status_code == 200

    in_stock_product = in_stock_response.json()
    out_of_stock_product = out_of_stock_response.json()

    response = client.get(
        "/products/catalog",
        params={
            "search": "Search Filter Product",
            "in_stock": True
        }
    )

    assert response.status_code == 200

    data = response.json()
    product_ids = [item["id"] for item in data["items"]]

    assert in_stock_product["id"] in product_ids
    assert out_of_stock_product["id"] not in product_ids

    for item in data["items"]:
        assert item["stock"] > 0


def test_products_catalog_invalid_sort_by_returns_400():
    response = client.get(
        "/products/catalog",
        params={
            "sort_by": "wrong_field",
            "sort_order": "asc"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid sort_by value"


def test_products_catalog_invalid_sort_order_returns_400():
    response = client.get(
        "/products/catalog",
        params={
            "sort_by": "price",
            "sort_order": "wrong_order"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid sort_order value"


def test_products_catalog_sort_by_price_desc():
    create_test_product(stock=10, price=100)
    create_test_product(stock=10, price=300)
    create_test_product(stock=10, price=200)

    response = client.get(
        "/products/catalog",
        params={
            "sort_by": "price",
            "sort_order": "desc",
            "skip": 0,
            "limit": 20
        }
    )

    assert response.status_code == 200

    data = response.json()
    prices = [product["price"] for product in data["items"]]

    assert prices == sorted(prices, reverse=True)


def test_products_catalog_invalid_price_range_returns_400():
    response = client.get(
        "/products/catalog",
        params={
            "min_price": 500,
            "max_price": 100
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "min_price cannot be greater than max_price"


def test_products_catalog_empty_search_returns_400():
    response = client.get(
        "/products/catalog",
        params={
            "search": ""
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "search cannot be empty"


def test_products_catalog_blank_search_returns_400():
    response = client.get(
        "/products/catalog",
        params={
            "search": "   "
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "search cannot be empty"


def test_admin_can_update_category():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    response = client.put(
        f"/categories/{category['id']}",
        json={
            "name": f"Updated Category {time.time()}"
        },
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == category["id"]
    assert response.json()["name"].startswith("Updated Category")


def test_update_category_not_found_returns_404():
    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        "/categories/999999",
        json={
            "name": "Updated Category"
        },
        headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_update_category_with_duplicate_name_returns_400():
    admin_headers = get_auth_headers(role="admin")

    category_1 = create_test_category()
    category_2 = create_test_category()

    response = client.put(
        f"/categories/{category_2['id']}",
        json={
            "name": category_1["name"]
        },
        headers=admin_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category already exists"


def test_update_category_with_empty_name_returns_422():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    response = client.put(
        f"/categories/{category['id']}",
        json={
            "name": ""
        },
        headers=admin_headers
    )

    assert response.status_code == 422

def test_admin_can_delete_empty_category():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    response = client.delete(
        f"/categories/{category['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Category deleted successfully"


def test_delete_category_not_found_returns_404():
    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        "/categories/999999",
        headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_cannot_delete_category_with_products():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    product_response = client.post(
        "/products",
        json={
            "name": f"Product In Category {time.time()}",
            "price": 100,
            "description": "Product linked to category",
            "image_url": None,
            "stock": 10,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert product_response.status_code == 200

    response = client.delete(
        f"/categories/{category['id']}",
        headers=admin_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete category with products"


def test_customer_cannot_delete_category():
    category = create_test_category()
    customer_headers = get_auth_headers(role="customer")

    response = client.delete(
        f"/categories/{category['id']}",
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_delete_category_requires_auth():
    category = create_test_category()

    response = client.delete(
        f"/categories/{category['id']}"
    )

    assert response.status_code == 401



def build_isolated_admin_dashboard_response(order_totals_by_status):
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

        low_stock_product = Product(
            name=f"Dashboard Low Stock Product {time.time_ns()}",
            price=Decimal("1.00"),
            description="Dashboard low stock product",
            stock=2,
            category_id=category.id,
        )
        in_stock_product = Product(
            name=f"Dashboard Product {time.time_ns()}",
            price=Decimal("2.00"),
            description="Dashboard product",
            stock=10,
            category_id=category.id,
        )
        db.add_all([low_stock_product, in_stock_product])

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

def test_admin_dashboard_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Online Shop Admin Dashboard" in response.text


def test_admin_dashboard_contains_dashboard_cards():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Products" in response.text
    assert "Categories" in response.text
    assert "Customers" in response.text
    assert "Orders" in response.text


def test_admin_dashboard_displays_total_revenue():
    response = build_isolated_admin_dashboard_response({"paid": ["200.00"]})

    assert response.status_code == 200
    assert "Total Revenue" in response.text
    assert "200.00" in response.text


def test_admin_dashboard_revenue_includes_paid_and_shipped_orders():
    response = build_isolated_admin_dashboard_response(
        {
            "paid": ["200.00"],
            "shipped": ["19.90"],
        }
    )

    assert response.status_code == 200
    assert "219.90" in response.text


def test_admin_dashboard_revenue_excludes_new_and_cancelled_orders():
    response = build_isolated_admin_dashboard_response(
        {
            "paid": ["0.30"],
            "new": ["200.00"],
            "cancelled": ["19.90"],
        }
    )

    assert response.status_code == 200
    assert "0.30" in response.text
    assert "219.90" not in response.text


def test_admin_dashboard_revenue_is_displayed_with_two_decimal_places():
    response = build_isolated_admin_dashboard_response(
        {
            "paid": ["19.90"],
            "shipped": ["0.30"],
        }
    )

    assert response.status_code == 200
    assert "<p>20.20</p>" in response.text


def test_admin_dashboard_continues_to_show_basic_counts():
    response = build_isolated_admin_dashboard_response(
        {
            "new": ["1.00"],
            "paid": ["2.00"],
            "shipped": ["3.00"],
            "cancelled": ["4.00"],
        }
    )

    assert response.status_code == 200
    assert "Products" in response.text
    assert "Categories" in response.text
    assert "Customers" in response.text
    assert "Orders" in response.text
    assert "Low Stock Products" in response.text
    assert "New Orders" in response.text
    assert "Paid Orders" in response.text
    assert "Shipped Orders" in response.text
    assert "Cancelled Orders" in response.text

def test_admin_dashboard_contains_quick_links():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "Products" in response.text
    assert "Orders" in response.text
    assert "Categories" in response.text
    assert "Customers" in response.text
    assert "Low Stock" in response.text
    assert "Swagger UI" in response.text
    assert "Health Check" in response.text

    assert "/admin" in response.text
    assert "/admin/products" in response.text
    assert "/admin/orders" in response.text
    assert "/admin/categories" in response.text
    assert "/admin/customers" in response.text
    assert "/admin/low-stock" in response.text
    assert "/docs" in response.text
    assert "/health" in response.text


def test_admin_products_page_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Admin Products" in response.text


def test_admin_products_page_contains_product_table():
    create_test_product(stock=10, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Name" in response.text
    assert "Price" in response.text
    assert "Stock" in response.text
    assert "Category ID" in response.text


def test_admin_dashboard_contains_admin_products_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Products" in response.text
    assert "/admin/products" in response.text
    

def test_admin_orders_page_returns_200():


    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "Admin Orders" in response.text


def test_admin_orders_page_contains_orders_table_headers():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Customer ID" in response.text
    assert "Status" in response.text
    assert "Total Price" in response.text
    assert "Created At" in response.text
    assert "Items Count" in response.text


def test_admin_dashboard_contains_admin_orders_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Orders" in response.text
    assert "/admin/orders" in response.text


def test_admin_categories_page_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert "Admin Categories" in response.text


def test_admin_categories_page_contains_categories_table_headers():
    create_test_category()

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Name" in response.text
    assert "Products Count" in response.text


def test_admin_dashboard_contains_admin_categories_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Categories" in response.text
    assert "/admin/categories" in response.text


def test_admin_customers_page_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/customers")

    assert response.status_code == 200
    assert "Admin Customers" in response.text


def test_admin_customers_page_contains_customers_table_headers():
    customer_headers = get_auth_headers(role="customer")
    create_test_customer(headers=customer_headers)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/customers")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "User ID" in response.text
    assert "Name" in response.text
    assert "Email" in response.text
    assert "Phone" in response.text


def test_admin_dashboard_contains_admin_customers_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Customers" in response.text
    assert "/admin/customers" in response.text


def test_admin_low_stock_page_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert "Admin Low Stock" in response.text


def test_admin_low_stock_page_contains_table_headers():
    create_test_product(stock=2, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Name" in response.text
    assert "Price" in response.text
    assert "Stock" in response.text
    assert "Category ID" in response.text


def test_admin_low_stock_page_shows_only_low_stock_products():
    low_stock_product = create_test_product(stock=2, price=100)
    normal_stock_product = create_test_product(stock=10, price=200)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert low_stock_product["name"] in response.text
    assert normal_stock_product["name"] not in response.text


def test_admin_dashboard_contains_admin_low_stock_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Low Stock" in response.text
    assert "/admin/low-stock" in response.text


def test_admin_orders_page_contains_status_badge_class():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "status status-new" in response.text


def test_admin_dashboard_contains_extended_stats_cards():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Low Stock Products" in response.text
    assert "New Orders" in response.text
    assert "Paid Orders" in response.text
    assert "Cancelled Orders" in response.text


def test_admin_dashboard_low_stock_count_is_displayed():
    create_test_product(stock=2, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Low Stock Products" in response.text


def test_admin_dashboard_final_polish_content():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Version: <strong>v4.0.0</strong>" in response.text
    assert "This dashboard provides a visual overview" in response.text
    assert "Admin pages:" in response.text


def test_admin_pages_have_final_footer():
    admin_client = get_admin_ui_client()

    urls = [
        "/admin/products",
        "/admin/orders",
        "/admin/categories",
        "/admin/customers",
        "/admin/low-stock"
    ]

    for url in urls:
        response = admin_client.get(url)

        assert response.status_code == 200
        assert "Online Shop Admin Dashboard — v4.0.0" in response.text

def test_admin_dashboard_order_status_cards_have_filtered_links():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200

    assert "New Orders" in response.text
    assert "Paid Orders" in response.text
    assert "Shipped Orders" in response.text
    assert "Cancelled Orders" in response.text

    assert "/admin/orders?status=new" in response.text
    assert "/admin/orders?status=paid" in response.text
    assert "/admin/orders?status=shipped" in response.text
    assert "/admin/orders?status=cancelled" in response.text




def test_admin_orders_page_can_filter_by_status():

    product = create_test_product(stock=10, price=100)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    create_test_order(

        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers

    )

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders?status=new")

    assert response.status_code == 200
    assert "Filtered by status" in response.text
    assert "new" in response.text


def test_admin_orders_page_contains_status_filter_links():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "Filter by status" in response.text

    assert "/admin/orders" in response.text
    assert "/admin/orders?status=new" in response.text
    assert "/admin/orders?status=paid" in response.text
    assert "/admin/orders?status=shipped" in response.text
    assert "/admin/orders?status=cancelled" in response.text

    assert "All" in response.text
    assert "New" in response.text
    assert "Paid" in response.text
    assert "Shipped" in response.text
    assert "Cancelled" in response.text


def test_admin_orders_status_filter_marks_active_status():
    admin_client = get_admin_ui_client()
    response = admin_client.get(
        "/admin/orders",
        params={
            "status": "paid"
        },
    )

    assert response.status_code == 200
    assert 'class="active"' in response.text
    assert "Filtered by status" in response.text
    assert "paid" in response.text


def test_admin_products_page_contains_filter_ui():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Product filters" in response.text
    assert "Search by name or description" in response.text
    assert "/admin/products?in_stock=true" in response.text
    assert "/admin/products?in_stock=false" in response.text

def test_admin_products_page_can_filter_by_search():
    searchable_product = create_test_product(stock=10, price=100)
    other_product = create_test_product(stock=10, price=200)

    admin_client = get_admin_ui_client()

    response = admin_client.get(
        "/admin/products",
        params={
            "search": searchable_product["name"]
        }
    )

    assert response.status_code == 200
    assert searchable_product["name"] in response.text
    assert other_product["name"] not in response.text


def test_admin_products_page_can_filter_out_of_stock_products():
    in_stock_product = create_test_product(stock=5, price=100)
    out_of_stock_product = create_test_product(stock=0, price=200)

    admin_client = get_admin_ui_client()

    response = admin_client.get(
        "/admin/products",
        params={
            "in_stock": False
        },
    )

    assert response.status_code == 200
    assert out_of_stock_product["name"] in response.text
    assert in_stock_product["name"] not in response.text


def test_admin_categories_page_contains_search_ui():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert "Category search" in response.text
    assert "Search by category name" in response.text
    assert "Reset" in response.text


def test_admin_categories_page_can_filter_by_search():
    searchable_category = create_test_category()
    other_category = create_test_category()

    admin_client = get_admin_ui_client()

    response = admin_client.get(
        "/admin/categories",
        params={
            "search": searchable_category["name"]
        },
    )


    assert response.status_code == 200
    assert searchable_category["name"] in response.text
    assert other_category["name"] not in response.text


def test_admin_customers_page_contains_search_ui():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/customers")

    assert response.status_code == 200
    assert "Customer search" in response.text
    assert "Search by name, email or phone" in response.text
    assert "Reset" in response.text


def test_admin_customers_page_can_filter_by_search():
    customer_headers = get_auth_headers(role="customer")

    searchable_customer = create_test_customer(headers=customer_headers)

    admin_client = get_admin_ui_client()

    response = admin_client.get(
        "/admin/customers",
        params={
            "search": searchable_customer["email"]
        },
    )

    assert response.status_code == 200
    assert searchable_customer["email"] in response.text


def test_admin_low_stock_page_uses_product_specific_threshold():
    low_stock_product = create_test_product(stock=8, price=100)
    normal_stock_product = create_test_product(stock=8, price=200)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert "Low Stock Threshold" in response.text

    # Both products currently use the default threshold.
    assert low_stock_product["name"] not in response.text
    assert normal_stock_product["name"] not in response.text


def test_admin_products_page_displays_low_stock_threshold():
    product = create_test_product(stock=3, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Low Stock Threshold" in response.text
    assert product["name"] in response.text


def test_admin_low_stock_page_includes_product_when_stock_is_below_custom_threshold():
    low_stock_product = create_test_product(
        stock=8,
        price=100,
        low_stock_threshold=10
    )

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert low_stock_product["name"] in response.text
    assert "Low Stock Threshold" in response.text


def test_product_response_includes_low_stock_threshold():
    product = create_test_product(
        stock=8,
        price=100,
        low_stock_threshold=10
    )

    assert product["low_stock_threshold"] == 10

def test_admin_login_page_returns_200():
    anonymous_client = TestClient(app)

    response = anonymous_client.get("/admin/login")

    assert response.status_code == 200
    assert "Admin Login" in response.text
    assert "Username" in response.text
    assert "Password" in response.text

def test_admin_pages_redirect_to_login_without_cookie():
    anonymous_client = TestClient(app)

    protected_urls = [
        "/admin",
        "/admin/products",
        "/admin/orders",
        "/admin/categories",
        "/admin/customers",
        "/admin/low-stock"
    ]

    for url in protected_urls:
        response = anonymous_client.get(
            url,
            follow_redirects=False
        )

        assert response.status_code == 303, f"{url} returned {response.status_code}"
        assert response.headers["location"] == "/admin/login"

def test_admin_login_rejects_invalid_credentials():
    response = client.post(
        "/admin/login",
        data={
            "username": "wrong-admin",
            "password": "wrong-password"
        }
    )

    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_admin_can_login_through_admin_ui():
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
    assert "admin_username" not in admin_client.cookies
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()
    assert "max-age=" in response.headers["set-cookie"].lower()


def test_forged_plain_admin_username_cookie_cannot_access_admin_ui():
    admin_user = create_registered_user(role="admin")
    forged_client = TestClient(app)
    forged_client.cookies.set("admin_username", admin_user["username"])

    response = forged_client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_customer_cannot_login_to_admin_ui():
    customer_user = create_registered_user(role="customer")

    response = client.post(
        "/admin/login",
        data={
            "username": customer_user["username"],
            "password": customer_user["password"]
        }
    )

    assert response.status_code == 403
    assert "Admin access required" in response.text


def test_admin_logout_deletes_admin_session_cookie():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"
    assert ADMIN_SESSION_COOKIE_NAME not in admin_client.cookies
    assert f"{ADMIN_SESSION_COOKIE_NAME}=" in response.headers["set-cookie"]


def test_invalid_admin_session_token_cannot_access_admin_ui():
    invalid_client = TestClient(app)
    invalid_client.cookies.set(ADMIN_SESSION_COOKIE_NAME, "not-a-valid-token")

    response = invalid_client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_expired_admin_session_token_cannot_access_admin_ui():
    admin_user = create_registered_user(role="admin")
    expired_token = jwt.encode(
        {
            "sub": admin_user["username"],
            "user_id": admin_user["id"],
            "role": "admin",
            "typ": ADMIN_SESSION_TOKEN_TYPE,
            "exp": datetime.now(UTC) - timedelta(seconds=1)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    expired_client = TestClient(app)
    expired_client.cookies.set(ADMIN_SESSION_COOKIE_NAME, expired_token)

    response = expired_client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_logout_redirects_to_login():
    response = client.get("/admin/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_ui_client_can_access_dashboard():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Online Shop Admin Dashboard" in response.text


def test_admin_product_create_page_returns_200_for_admin():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/products/create")

    assert response.status_code == 200
    assert "Create Product" in response.text
    assert "Low Stock Threshold" in response.text
    assert "Category ID" in response.text


def test_admin_product_create_page_redirects_without_login():
    anonymous_client = TestClient(app)

    response = anonymous_client.get(
        "/admin/products/create",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_can_create_product_from_ui():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    product_name = f"Admin UI Product {time.time()}"

    response = admin_client.post(
        "/admin/products/create",
        data={
            "name": product_name,
            "price": 150,
            "description": "Created from admin UI",
            "image_url": "https://example.com/admin-product.jpg",
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": category["id"]
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"

    products_response = admin_client.get("/admin/products")

    assert products_response.status_code == 200
    assert product_name in products_response.text


def test_admin_product_create_rejects_invalid_category():
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/products/create",
        data={
            "name": f"Invalid Category Product {time.time()}",
            "price": 150,
            "description": "Invalid category test",
            "image_url": "https://example.com/admin-product.jpg",
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": 999999
        }
    )

    assert response.status_code == 404
    assert "Category not found" in response.text


def test_admin_products_page_contains_create_product_link():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Create Product" in response.text
    assert "/admin/products/create" in response.text


def test_admin_product_edit_page_returns_200_for_admin():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get(f"/admin/products/{product['id']}/edit")

    assert response.status_code == 200
    assert "Edit Product" in response.text
    assert product["name"] in response.text
    assert "Low Stock Threshold" in response.text
    assert "Update Product" in response.text


def test_admin_product_edit_page_redirects_without_login():
    product = create_test_product(stock=5, price=100)
    anonymous_client = TestClient(app)

    response = anonymous_client.get(
        f"/admin/products/{product['id']}/edit",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_can_update_product_from_ui():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)
    category = create_test_category()

    updated_name = f"Updated Admin Product {time.time()}"

    response = admin_client.post(
        f"/admin/products/{product['id']}/edit",
        data={
            "name": updated_name,
            "price": 250,
            "description": "Updated from admin UI",
            "image_url": "https://example.com/updated-product.jpg",
            "stock": 12,
            "low_stock_threshold": 20,
            "category_id": category["id"]
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"

    products_response = admin_client.get("/admin/products")

    assert products_response.status_code == 200
    assert updated_name in products_response.text
    assert "20" in products_response.text


def test_admin_product_edit_rejects_invalid_category():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.post(
        f"/admin/products/{product['id']}/edit",
        data={
            "name": product["name"],
            "price": 250,
            "description": "Invalid category update",
            "image_url": "https://example.com/updated-product.jpg",
            "stock": 12,
            "low_stock_threshold": 20,
            "category_id": 999999
        }
    )

    assert response.status_code == 404
    assert "Category not found" in response.text


def test_admin_products_page_contains_edit_product_link():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Edit" in response.text
    assert f"/admin/products/{product['id']}/edit" in response.text


def test_admin_products_page_contains_delete_button_and_modal():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Delete" in response.text
    assert f"/admin/products/{product['id']}/delete" in response.text
    assert "Delete product?" in response.text
    assert "Are you sure you want to delete this product?" in response.text
    assert "Cancel" in response.text


def test_admin_product_edit_page_contains_update_confirmation_modal():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get(f"/admin/products/{product['id']}/edit")

    assert response.status_code == 200
    assert "Update product?" in response.text
    assert "Are you sure you want to save these product changes?" in response.text
    assert "Cancel" in response.text
    assert "Update" in response.text


def test_admin_product_delete_redirects_without_login():
    product = create_test_product(stock=5, price=100)
    anonymous_client = TestClient(app)

    response = anonymous_client.post(
        f"/admin/products/{product['id']}/delete",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_can_delete_product_without_orders():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.post(
        f"/admin/products/{product['id']}/delete",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"

    products_response = admin_client.get("/admin/products")

    assert products_response.status_code == 200
    assert product["name"] not in products_response.text


def test_admin_product_delete_blocked_when_product_is_used_in_orders():
    admin_client = get_admin_ui_client()

    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    response = admin_client.post(
        f"/admin/products/{product['id']}/delete"
    )

    assert response.status_code == 400
    assert "Product cannot be deleted because it is used in orders." in response.text

def test_anonymous_cannot_read_customer_profile():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.get(f"/customers/{customer['id']}")

    assert response.status_code == 401


def test_anonymous_cannot_update_customer_profile():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.put(
        f"/customers/{customer['id']}",
        json={
            "name": "Anonymous Update",
            "email": f"anonymous_update_{time.time()}@example.com",
            "phone": "+380501112244"
        }
    )

    assert response.status_code == 401


def test_anonymous_cannot_delete_customer():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.delete(f"/customers/{customer['id']}")

    assert response.status_code == 401


def test_customer_cannot_read_other_customer_profile():
    customer_1_headers = get_auth_headers(role="customer")
    create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    response = client.get(
        f"/customers/{customer_2['id']}",
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_customer_cannot_update_other_customer_profile():
    customer_1_headers = get_auth_headers(role="customer")
    create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    response = client.put(
        f"/customers/{customer_2['id']}",
        json={
            "name": "Unauthorized Update",
            "email": f"unauthorized_update_{time.time()}@example.com",
            "phone": "+380501112255"
        },
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_admin_can_read_customer_profiles_by_id():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        f"/customers/{customer['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == customer["id"]


def test_admin_can_update_customer_profiles_by_id():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_headers = get_auth_headers(role="admin")
    updated_email = f"admin_update_{time.time()}@example.com"

    response = client.put(
        f"/customers/{customer['id']}",
        json={
            "name": "Admin Updated Customer",
            "email": updated_email,
            "phone": "+380501112266"
        },
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Admin Updated Customer"
    assert response.json()["email"] == updated_email


def test_non_admin_cannot_get_orders_by_status():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders/by-status",
        params={"status": "new"},
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_non_admin_cannot_get_stats_summary():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/stats/summary",
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_stats_summary_api_returns_numeric_total_revenue():
    product = create_test_product(stock=10, price=19.9)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers,
    )

    admin_headers = get_auth_headers(role="admin")
    status_response = client.put(
        f"/orders/{order['id']}/status",
        params={"status": "paid"},
        headers=admin_headers,
    )

    assert status_response.status_code == 200

    response = client.get(
        "/stats/summary",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json()["total_revenue"], (int, float))
    assert not isinstance(response.json()["total_revenue"], str)


def test_customer_orders_route_is_registered_and_admin_only():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    anonymous_response = client.get(f"/customers/{customer['id']}/orders")

    assert anonymous_response.status_code == 401

    customer_response = client.get(
        f"/customers/{customer['id']}/orders",
        headers=customer_headers
    )

    assert customer_response.status_code == 403
    assert customer_response.json()["detail"] == "Admin access required"

    admin_headers = get_auth_headers(role="admin")

    admin_response = client.get(
        f"/customers/{customer['id']}/orders",
        headers=admin_headers
    )

    assert admin_response.status_code == 200

    data = admin_response.json()
    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids


def test_start_script_runs_migrations_before_uvicorn():
    script_path = Path("scripts/start.sh")

    assert script_path.exists()

    script = script_path.read_text()
    assert "alembic upgrade head" in script
    assert "uvicorn main:app --host 0.0.0.0 --port" in script
    assert "${PORT:-8000}" in script
    assert script.index("alembic upgrade head") < script.index("uvicorn main:app")


def build_product_payload(category_id: int, price):
    return {
        "name": f"Money Test Product {time.time()}",
        "price": price,
        "description": "Money validation test product",
        "stock": 10,
        "low_stock_threshold": 5,
        "category_id": category_id,
    }


def test_api_create_product_accepts_money_with_two_decimal_places():
    category = create_test_category()
    headers = get_auth_headers(role="admin")

    response = client.post(
        "/products",
        json=build_product_payload(category["id"], 19.99),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["price"] == 19.99


def test_api_create_product_rejects_more_than_two_decimal_places():
    category = create_test_category()
    headers = get_auth_headers(role="admin")

    response = client.post(
        "/products",
        json=build_product_payload(category["id"], 19.999),
        headers=headers,
    )

    assert response.status_code == 422
    assert "more than 2 decimal places" in response.text


def test_api_create_product_rejects_negative_price():
    category = create_test_category()
    headers = get_auth_headers(role="admin")

    response = client.post(
        "/products",
        json=build_product_payload(category["id"], -1),
        headers=headers,
    )

    assert response.status_code == 422
    assert "greater than or equal to 0" in response.text


def test_api_create_product_rejects_zero_price():
    category = create_test_category()
    headers = get_auth_headers(role="admin")

    response = client.post(
        "/products",
        json=build_product_payload(category["id"], 0),
        headers=headers,
    )

    assert response.status_code == 422
    assert "greater than 0" in response.text


def test_api_update_product_rejects_more_than_two_decimal_places():
    product = create_test_product(stock=10, price=100)
    headers = get_auth_headers(role="admin")

    response = client.put(
        f"/products/{product['id']}",
        json=build_product_payload(product["category_id"], 19.999),
        headers=headers,
    )

    assert response.status_code == 422
    assert "more than 2 decimal places" in response.text


def test_admin_product_create_rejects_more_than_two_decimal_places():
    category = create_test_category()
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/products/create",
        data={
            "name": f"Admin Money Product {time.time()}",
            "price": "19.999",
            "description": "Created from admin UI",
            "image_url": "https://example.com/admin-product.jpg",
            "stock": "5",
            "low_stock_threshold": "5",
            "category_id": str(category["id"]),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "more than 2 decimal places" in response.text


def test_admin_product_edit_rejects_more_than_two_decimal_places():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.post(
        f"/admin/products/{product['id']}/edit",
        data={
            "name": product["name"],
            "price": "19.999",
            "description": product["description"],
            "image_url": "https://example.com/updated-product.jpg",
            "stock": "5",
            "low_stock_threshold": "5",
            "category_id": str(product["category_id"]),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "more than 2 decimal places" in response.text


def test_admin_products_page_displays_money_with_two_decimal_places():
    create_test_product(stock=10, price=19.9)
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "19.90" in response.text


def test_admin_low_stock_page_displays_product_price_with_two_decimal_places():
    create_test_product(stock=2, price=19.9)
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert "19.90" in response.text


def test_admin_orders_page_displays_total_price_with_two_decimal_places():
    product = create_test_product(stock=10, price=19.9)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers,
    )
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "19.90" in response.text


def test_product_filters_continue_working_with_money_validation():
    create_test_product(stock=10, price=100)
    create_test_product(stock=10, price=300)
    create_test_product(stock=10, price=700)

    response = client.get(
        "/products",
        params={
            "min_price": 100,
            "max_price": 500,
            "sort_by": "price",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    prices = [product["price"] for product in data]
    assert prices == sorted(prices)
    for product in data:
        assert product["price"] >= 100
        assert product["price"] <= 500


def test_create_order_decimal_total_for_19_99_times_3():
    product = create_test_product(stock=10, price=19.99)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["total_price"] == 59.97
    assert order["items"][0]["unit_price"] == 19.99


def test_create_order_decimal_total_for_0_10_times_3_has_no_float_artifact():
    product = create_test_product(stock=10, price=0.10)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["total_price"] == 0.30
    assert str(order["total_price"]) == "0.3"


def test_create_order_multi_item_total_is_exact():
    product_1 = create_test_product(stock=10, price=0.10)
    product_2 = create_test_product(stock=10, price=19.99)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {"product_id": product_1["id"], "quantity": 3},
                {"product_id": product_2["id"], "quantity": 2},
            ],
        },
        headers=customer_headers,
    )

    assert response.status_code == 200
    order = response.json()
    assert order["total_price"] == 40.28
    assert [item["unit_price"] for item in order["items"]] == [0.10, 19.99]


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


def test_stats_revenue_includes_paid_orders():
    response = build_isolated_stats_response({"paid": ["12.34"]})

    assert response["total_revenue"] == Decimal("12.34")


def test_stats_revenue_includes_shipped_orders():
    response = build_isolated_stats_response({"shipped": ["23.45"]})

    assert response["total_revenue"] == Decimal("23.45")


def test_stats_revenue_excludes_new_orders():
    response = build_isolated_stats_response({"new": ["99.99"]})

    assert response["total_revenue"] == Decimal("0.00")


def test_stats_revenue_excludes_cancelled_orders():
    response = build_isolated_stats_response({"cancelled": ["99.99"]})

    assert response["total_revenue"] == Decimal("0.00")


def test_stats_revenue_sums_fractional_orders_exactly():
    response = build_isolated_stats_response(
        {
            "paid": ["0.10", "0.20"],
            "shipped": ["19.99"],
        }
    )

    assert response["total_revenue"] == Decimal("20.29")
    assert str(response["total_revenue"]) == "20.29"


def test_stats_revenue_is_zero_for_empty_orders():
    response = build_isolated_stats_response({})

    assert response["total_revenue"] == Decimal("0.00")
