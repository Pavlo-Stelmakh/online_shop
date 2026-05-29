import os
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app


TEST_DATABASE_URL = "sqlite:///./test_shop.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


if os.path.exists("test_shop.db"):
    os.remove("test_shop.db")

Base.metadata.create_all(bind=engine)

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Online shop API with SQLite is working"
    }


def test_create_category():
    category_name = f"Test Category {time.time()}"

    response = client.post(
        "/categories",
        json={
            "name": category_name
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == category_name
    assert "id" in data

def test_create_product():
    category_name = f"Product Category {time.time()}"

    category_response = client.post(
        "/categories",
        json={
            "name": category_name
        }
    )

    assert category_response.status_code == 200

    category_data = category_response.json()
    category_id = category_data["id"]

    product_response = client.post(
        "/products",
        json={
            "name": "Test Product",
            "price": 100,
            "description": "Test product description",
            "stock": 10,
            "category_id": category_id
        }
    )

    assert product_response.status_code == 200

    product_data = product_response.json()

    assert product_data["name"] == "Test Product"
    assert product_data["price"] == 100
    assert product_data["description"] == "Test product description"
    assert product_data["stock"] == 10
    assert product_data["category_id"] == category_id
    assert "id" in product_data

def test_create_customer():
    email = f"customer_{time.time()}@example.com"

    response = client.post(
        "/customers",
        json={
            "name": "Test Customer",
            "email": email,
            "phone": "+380501112233"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Test Customer"
    assert data["email"] == email
    assert data["phone"] == "+380501112233"
    assert "id" in data

def test_create_order_and_reduce_stock():
    category_response = client.post(
        "/categories",
        json={
            "name": f"Order Category {time.time()}"
        }
    )

    assert category_response.status_code == 200
    category_id = category_response.json()["id"]

    product_response = client.post(
        "/products",
        json={
            "name": "Order Test Product",
            "price": 100,
            "description": "Product for order test",
            "stock": 10,
            "category_id": category_id
        }
    )

    assert product_response.status_code == 200
    product_data = product_response.json()
    product_id = product_data["id"]

    customer_response = client.post(
        "/customers",
        json={
            "name": "Order Test Customer",
            "email": f"order_customer_{time.time()}@example.com",
            "phone": "+380501112233"
        }
    )

    assert customer_response.status_code == 200
    customer_id = customer_response.json()["id"]

    order_response = client.post(
        "/orders",
        json={
            "customer_id": customer_id,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 2
                }
            ]
        }
    )

    assert order_response.status_code == 200
    order_data = order_response.json()

    assert order_data["customer_id"] == customer_id
    assert order_data["status"] == "new"
    assert order_data["total_price"] == 200
    assert len(order_data["items"]) == 1
    assert order_data["items"][0]["product_id"] == product_id
    assert order_data["items"][0]["quantity"] == 2

    updated_product_response = client.get(f"/products/{product_id}")

    assert updated_product_response.status_code == 200
    updated_product_data = updated_product_response.json()

    assert updated_product_data["stock"] == 8

def test_cancel_order_returns_stock():
    category_response = client.post(
        "/categories",
        json={
            "name": f"Cancel Category {time.time()}"
        }
    )

    assert category_response.status_code == 200
    category_id = category_response.json()["id"]

    product_response = client.post(
        "/products",
        json={
            "name": "Cancel Test Product",
            "price": 50,
            "description": "Product for cancel test",
            "stock": 10,
            "category_id": category_id
        }
    )

    assert product_response.status_code == 200
    product_id = product_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={
            "name": "Cancel Test Customer",
            "email": f"cancel_customer_{time.time()}@example.com",
            "phone": "+380501112233"
        }
    )

    assert customer_response.status_code == 200
    customer_id = customer_response.json()["id"]

    order_response = client.post(
        "/orders",
        json={
            "customer_id": customer_id,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 2
                }
            ]
        }
    )

    assert order_response.status_code == 200
    order_id = order_response.json()["id"]

    product_after_order_response = client.get(f"/products/{product_id}")
    assert product_after_order_response.status_code == 200
    assert product_after_order_response.json()["stock"] == 8

    cancel_response = client.put(
        f"/orders/{order_id}/status",
        params={
            "status": "cancelled"
        }
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    product_after_cancel_response = client.get(f"/products/{product_id}")
    assert product_after_cancel_response.status_code == 200
    assert product_after_cancel_response.json()["stock"] == 10