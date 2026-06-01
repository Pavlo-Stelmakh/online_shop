import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_shop.db"

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


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def get_auth_headers(role: str = "admin"):
    username = f"{role}_user_{time.time()}"
    email = f"{username}@example.com"
    password = "123456"

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "role": role
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

    return {
        "Authorization": f"Bearer {token}"
    }


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


def create_test_product(stock: int = 10, price: float = 100):
    headers = get_auth_headers()
    category = create_test_category()

    response = client.post(
        "/products",
        json={
            "name": f"Test Product {time.time()}",
            "price": price,
            "description": "Test product description",
            "stock": stock,
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
        "message": "Online shop API with SQLite is working"
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

    product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200

    updated_product = product_response.json()

    assert updated_product["stock"] == 8

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
    assert isinstance(response.json(), list)

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