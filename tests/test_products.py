import time

from models import OrderItem, Product
from tests.helpers import (
    TestingSessionLocal,
    client,
    create_test_category,
    create_test_customer,
    create_test_order,
    create_test_product,
    get_auth_headers,
)


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


def test_products_catalog_offset_shape_excludes_page_fields():
    create_test_product(stock=10, price=100)

    response = client.get(
        "/products/catalog",
        params={"skip": 0, "limit": 1}
    )

    assert response.status_code == 200

    data = response.json()

    assert set(["total", "skip", "limit", "items"]).issubset(data)
    assert "page" not in data
    assert "pages" not in data
    assert data["skip"] == 0
    assert data["limit"] == 1
    assert isinstance(data["items"], list)


def test_products_catalog_pages_shape_excludes_skip():
    create_test_product(stock=10, price=100)

    response = client.get(
        "/products/catalog/pages",
        params={"page": 1, "limit": 1}
    )

    assert response.status_code == 200

    data = response.json()

    assert set(["items", "total", "page", "limit", "pages"]).issubset(data)
    assert "skip" not in data
    assert data["page"] == 1
    assert data["limit"] == 1
    assert isinstance(data["items"], list)


def test_openapi_catalog_response_schemas_match_payload_shapes():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()
    catalog_response = openapi["paths"]["/products/catalog"]["get"]["responses"]["200"]
    pages_response = openapi["paths"]["/products/catalog/pages"]["get"]["responses"]["200"]
    catalog_schema = catalog_response["content"]["application/json"]["schema"]
    pages_schema = pages_response["content"]["application/json"]["schema"]

    assert (
        catalog_schema.get("$ref", "").endswith("/ProductCatalogOffsetResponse")
        or "skip" in catalog_schema.get("properties", {})
    )
    assert (
        pages_schema.get("$ref", "").endswith("/ProductCatalogPageResponse")
        or {"page", "pages"}.issubset(pages_schema.get("properties", {}))
    )


def test_legacy_product_endpoints_return_plain_lists():
    create_test_product(stock=10, price=100)

    endpoints = [
        ("/products/search", {"query": "Product"}),
        ("/products/filter", {"min_price": 0}),
        ("/products/sort", {"order": "asc"}),
        ("/products/limited", {"limit": 1}),
    ]

    for path, params in endpoints:
        response = client.get(path, params=params)

        assert response.status_code == 200
        assert isinstance(response.json(), list)


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


def test_product_response_includes_low_stock_threshold():
    product = create_test_product(
        stock=8,
        price=100,
        low_stock_threshold=10
    )

    assert product["low_stock_threshold"] == 10


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
