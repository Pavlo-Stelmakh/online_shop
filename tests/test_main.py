import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import User



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
            "password": password
        }
    )

    assert register_response.status_code == 200

    if role == "admin":
        db = TestingSessionLocal()

        try:
            user = db.query(User).filter(
                User.username == username
            ).first()

            user.role = "admin"
            db.commit()
        finally:
            db.close()

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


def test_admin_dashboard_returns_200():
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Online Shop Admin Dashboard" in response.text


def test_admin_dashboard_contains_dashboard_cards():
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Products" in response.text
    assert "Categories" in response.text
    assert "Customers" in response.text
    assert "Orders" in response.text


def test_admin_dashboard_contains_quick_links():
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Swagger UI" in response.text
    assert "Health Check" in response.text
    assert "Product Catalog API" in response.text
    assert "Low Stock API" in response.text
    assert "Orders API" in response.text
    assert "Categories API" in response.text


def test_admin_products_page_returns_200():
    response = client.get("/admin/products")

    assert response.status_code == 200
    assert "Admin Products" in response.text


def test_admin_products_page_contains_product_table():
    create_test_product(stock=10, price=100)

    response = client.get("/admin/products")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Name" in response.text
    assert "Price" in response.text
    assert "Stock" in response.text
    assert "Category ID" in response.text


def test_admin_dashboard_contains_admin_products_link():
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Admin Products" in response.text
    assert "/admin/products" in response.text
    

def test_admin_orders_page_returns_200():
    response = client.get("/admin/orders")

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

    response = client.get("/admin/orders")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Customer ID" in response.text
    assert "Status" in response.text
    assert "Total Price" in response.text
    assert "Created At" in response.text
    assert "Items Count" in response.text


def test_admin_dashboard_contains_admin_orders_link():
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Admin Orders" in response.text
    assert "/admin/orders" in response.text


def test_admin_categories_page_returns_200():
    response = client.get("/admin/categories")

    assert response.status_code == 200
    assert "Admin Categories" in response.text


def test_admin_categories_page_contains_categories_table_headers():
    create_test_category()

    response = client.get("/admin/categories")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Name" in response.text
    assert "Products Count" in response.text


def test_admin_dashboard_contains_admin_categories_link():
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Admin Categories" in response.text
    assert "/admin/categories" in response.text