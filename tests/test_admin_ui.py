import time
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from fastapi.testclient import TestClient
from jose import jwt

from auth import SECRET_KEY, ALGORITHM
from routes.admin import (
    ADMIN_SESSION_COOKIE_NAME,
    ADMIN_SESSION_TOKEN_TYPE,
    create_admin_session_token,
    format_admin_datetime,
)
from tests.helpers import (
    app,
    build_isolated_admin_dashboard_response,
    client,
    create_registered_user,
    create_test_category,
    create_test_customer,
    create_test_order,
    create_test_product,
    get_admin_ui_client,
    get_admin_ui_csrf_token,
    get_auth_headers,
    TestingSessionLocal,
)
from models import Order, User



def _set_order_admin_display_fields(order_id, created_at=None, status=None):
    db = TestingSessionLocal()

    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        assert order is not None

        if created_at is not None:
            order.created_at = created_at

        if status is not None:
            order.status = status

        db.commit()
    finally:
        db.close()


def test_admin_datetime_formatter_handles_none_safely():
    assert format_admin_datetime(None) == ""


def test_admin_datetime_formatter_uses_consistent_human_readable_format():
    value = datetime(2026, 6, 15, 9, 7, 33, tzinfo=UTC)

    assert format_admin_datetime(value) == "2026-06-15 09:07"

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


def test_admin_dashboard_low_stock_count_uses_product_specific_threshold():
    response = build_isolated_admin_dashboard_response(
        {},
        products=[
            {
                "name": f"Dashboard Custom Low Stock {time.time_ns()}",
                "price": Decimal("1.00"),
                "description": "Uses product-specific threshold",
                "stock": 8,
                "low_stock_threshold": 10,
            },
            {
                "name": f"Dashboard Hardcoded Five Regression {time.time_ns()}",
                "price": Decimal("2.00"),
                "description": "Would be low only with the old hardcoded rule",
                "stock": 6,
                "low_stock_threshold": 5,
            },
        ],
    )

    assert response.status_code == 200
    assert "Low Stock Products" in response.text
    assert "<h2>Low Stock Products</h2>\n                <p>1</p>" in response.text

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


def test_admin_products_page_stock_badge_uses_product_specific_threshold():
    create_test_product(stock=88, price=100, low_stock_threshold=90)
    create_test_product(stock=66, price=100, low_stock_threshold=65)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert '<span class="stock-low">88</span>' in response.text
    assert '<span class="stock-ok">66</span>' in response.text

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

def test_admin_can_open_new_product_form():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/products/new")

    assert response.status_code == 200
    assert "Add product" in response.text
    assert "Low Stock Threshold" in response.text
    assert "Category ID" in response.text

def test_admin_product_create_page_redirects_without_login():
    anonymous_client = TestClient(app)

    response = anonymous_client.get(
        "/admin/products/new",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"

def test_admin_can_create_product_from_ui():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    product_name = f"Admin UI Product {time.time()}"

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": product_name,
            "price": 150,
            "description": "Created from admin UI",
            "image_url": "https://example.com/admin-product.jpg",
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": category["id"],
            "csrf_token": get_admin_ui_csrf_token(admin_client)
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"

    products_response = admin_client.get("/admin/products")

    assert products_response.status_code == 200
    assert product_name in products_response.text


def test_admin_products_page_shows_product_image_preview():
    admin_client = get_admin_ui_client()
    category = create_test_category()
    image_url = f"https://example.com/admin-preview-{time.time()}.jpg"
    product_name = f"Image Preview Product {time.time()}"

    create_response = admin_client.post(
        "/admin/products/new",
        data={
            "name": product_name,
            "price": 150,
            "description": "Product with preview image",
            "image_url": image_url,
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": category["id"],
            "csrf_token": get_admin_ui_csrf_token(admin_client),
        },
        follow_redirects=False,
    )

    assert create_response.status_code == 303

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert 'class="product-image-preview"' in response.text
    assert f'src="{image_url}"' in response.text
    assert f'alt="{product_name} preview"' in response.text


def test_admin_products_page_shows_no_image_fallback_for_missing_image_url():
    admin_client = get_admin_ui_client()
    create_test_product(stock=10, price=100)

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "No image" in response.text


def test_admin_product_create_rejects_invalid_image_url():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": f"Invalid Image Create {time.time()}",
            "price": 150,
            "description": "Invalid image URL",
            "image_url": "ftp://example.com/image.jpg",
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": category["id"],
            "csrf_token": get_admin_ui_csrf_token(admin_client),
        },
    )

    assert response.status_code == 400
    assert "Image URL must start with http:// or https://" in response.text
    assert 'value="ftp://example.com/image.jpg"' in response.text


def test_admin_product_edit_rejects_invalid_image_url():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.post(
        f"/admin/products/{product['id']}/edit",
        data={
            "name": product["name"],
            "price": 250,
            "description": "Invalid image update",
            "image_url": "example.com/image.jpg",
            "stock": 12,
            "low_stock_threshold": 20,
            "category_id": product["category_id"],
            "csrf_token": get_admin_ui_csrf_token(admin_client, f"/admin/products/{product['id']}/edit"),
        },
    )

    assert response.status_code == 400
    assert "Image URL must start with http:// or https://" in response.text
    assert 'value="example.com/image.jpg"' in response.text

def test_admin_product_create_without_csrf_fails():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": f"Missing CSRF Product {time.time()}",
            "price": 150,
            "description": "Missing csrf",
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": category["id"],
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_admin_product_edit_without_csrf_fails():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.post(
        f"/admin/products/{product['id']}/edit",
        data={
            "name": product["name"],
            "price": 250,
            "description": "Missing csrf",
            "stock": 12,
            "low_stock_threshold": 20,
            "category_id": product["category_id"],
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_admin_product_delete_without_csrf_fails():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.post(
        f"/admin/products/{product['id']}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 403

def test_admin_product_create_rejects_invalid_category():
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": f"Invalid Category Product {time.time()}",
            "price": 150,
            "description": "Invalid category test",
            "image_url": "https://example.com/admin-product.jpg",
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": 999999,
            "csrf_token": get_admin_ui_csrf_token(admin_client)
        }
    )

    assert response.status_code == 404
    assert "Category not found" in response.text



def test_admin_product_create_invalid_price_preserves_submitted_values():
    category = create_test_category()
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": "Attempted Create Product",
            "price": "19.999",
            "description": "Attempted create description",
            "image_url": "https://example.com/attempted-create.jpg",
            "stock": "11",
            "low_stock_threshold": "4",
            "category_id": str(category["id"]),
            "csrf_token": get_admin_ui_csrf_token(admin_client),
        },
    )

    assert response.status_code == 400
    assert 'value="Attempted Create Product"' in response.text
    assert "Attempted create description" in response.text
    assert 'value="https://example.com/attempted-create.jpg"' in response.text
    assert 'value="11"' in response.text
    assert 'value="4"' in response.text
    assert f'value="{category["id"]}"' in response.text


def test_admin_product_create_invalid_category_preserves_submitted_fields():
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": "Invalid Category Attempt",
            "price": "29.99",
            "description": "Invalid category description",
            "image_url": "https://example.com/invalid-category.jpg",
            "stock": "9",
            "low_stock_threshold": "3",
            "category_id": "999999",
            "csrf_token": get_admin_ui_csrf_token(admin_client),
        },
    )

    assert response.status_code == 404
    assert 'value="Invalid Category Attempt"' in response.text
    assert 'value="29.99"' in response.text
    assert "Invalid category description" in response.text
    assert 'value="https://example.com/invalid-category.jpg"' in response.text
    assert 'value="9"' in response.text
    assert 'value="3"' in response.text
    assert 'value="999999"' in response.text


def test_admin_product_edit_invalid_price_shows_attempted_values_not_persisted_values():
    product = create_test_product(stock=5, price=100, low_stock_threshold=5)
    category = create_test_category()
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        f"/admin/products/{product['id']}/edit",
        data={
            "name": "Attempted Edit Product",
            "price": "12.999",
            "description": "Attempted edit description",
            "image_url": "https://example.com/attempted-edit.jpg",
            "stock": "14",
            "low_stock_threshold": "6",
            "category_id": str(category["id"]),
            "csrf_token": get_admin_ui_csrf_token(admin_client, f"/admin/products/{product['id']}/edit"),
        },
    )

    assert response.status_code == 400
    assert 'value="Attempted Edit Product"' in response.text
    assert 'value="12.999"' in response.text
    assert "Attempted edit description" in response.text
    assert 'value="https://example.com/attempted-edit.jpg"' in response.text
    assert 'value="14"' in response.text
    assert 'value="6"' in response.text
    assert f'value="{category["id"]}"' in response.text
    assert f'value="{product["name"]}"' not in response.text
    assert 'value="100.00"' not in response.text


def test_admin_product_edit_invalid_stock_or_threshold_preserves_attempted_fields():
    product = create_test_product(stock=5, price=100, low_stock_threshold=5)
    category = create_test_category()
    admin_client = get_admin_ui_client()
    path = f"/admin/products/{product['id']}/edit"

    stock_response = admin_client.post(
        path,
        data={
            "name": "Negative Stock Attempt",
            "price": "45.50",
            "description": "Negative stock description",
            "image_url": "https://example.com/negative-stock.jpg",
            "stock": "-1",
            "low_stock_threshold": "8",
            "category_id": str(category["id"]),
            "csrf_token": get_admin_ui_csrf_token(admin_client, path),
        },
    )
    threshold_response = admin_client.post(
        path,
        data={
            "name": "Bad Threshold Attempt",
            "price": "55.50",
            "description": "Bad threshold description",
            "image_url": "https://example.com/bad-threshold.jpg",
            "stock": "10",
            "low_stock_threshold": "101",
            "category_id": str(category["id"]),
            "csrf_token": get_admin_ui_csrf_token(admin_client, path),
        },
    )

    assert stock_response.status_code == 400
    assert 'value="Negative Stock Attempt"' in stock_response.text
    assert 'value="45.50"' in stock_response.text
    assert "Negative stock description" in stock_response.text
    assert 'value="-1"' in stock_response.text
    assert 'value="8"' in stock_response.text

    assert threshold_response.status_code == 400
    assert 'value="Bad Threshold Attempt"' in threshold_response.text
    assert 'value="55.50"' in threshold_response.text
    assert "Bad threshold description" in threshold_response.text
    assert 'value="10"' in threshold_response.text
    assert 'value="101"' in threshold_response.text


def test_admin_customer_edit_duplicate_email_preserves_attempted_values():
    customer = create_test_customer()
    other_customer = create_test_customer()
    admin_client = get_admin_ui_client()
    path = f'/admin/customers/{customer["id"]}'

    response = admin_client.post(
        f'{path}/edit',
        data={
            "name": "Attempted Duplicate Customer",
            "email": other_customer["email"],
            "phone": "+380509990001",
            "csrf_token": get_admin_ui_csrf_token(admin_client, path),
        },
    )

    assert response.status_code == 400
    assert 'value="Attempted Duplicate Customer"' in response.text
    assert f'value="{other_customer["email"]}"' in response.text
    assert 'value="+380509990001"' in response.text
    assert f'value="{customer["email"]}"' not in response.text


def test_admin_customer_edit_empty_field_preserves_attempted_values():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()
    path = f'/admin/customers/{customer["id"]}'

    response = admin_client.post(
        f'{path}/edit',
        data={
            "name": " ",
            "email": "attempted-empty@example.com",
            "phone": "+380509990002",
            "csrf_token": get_admin_ui_csrf_token(admin_client, path),
        },
    )

    assert response.status_code == 400
    assert 'value=" "' in response.text
    assert 'value="attempted-empty@example.com"' in response.text
    assert 'value="+380509990002"' in response.text


def test_failed_admin_login_preserves_username():
    response = client.post(
        "/admin/login",
        data={
            "username": "attempted-admin",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert 'value="attempted-admin"' in response.text


def test_failed_admin_login_does_not_preserve_password_in_response_html():
    response = client.post(
        "/admin/login",
        data={
            "username": "attempted-admin",
            "password": "super-secret-password",
        },
    )

    assert response.status_code == 401
    assert "super-secret-password" not in response.text
    assert '<input id="password" type="password" name="password" required>' in response.text

def test_api_bearer_product_create_does_not_require_csrf():
    category = create_test_category()
    admin_headers = get_auth_headers(role="admin")

    response = client.post(
        "/products",
        json={
            "name": f"Bearer API Product {time.time()}",
            "price": 99.99,
            "description": "Created through bearer API without csrf",
            "stock": 4,
            "low_stock_threshold": 2,
            "category_id": category["id"],
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

def test_admin_products_page_contains_create_product_link():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Add product" in response.text
    assert "/admin/products/new" in response.text

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
            "category_id": category["id"],
            "csrf_token": get_admin_ui_csrf_token(admin_client)
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
            "category_id": 999999,
            "csrf_token": get_admin_ui_csrf_token(admin_client, f"/admin/products/{product['id']}/edit")
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
    assert "Are you sure you want to delete this product?" in response.text
    assert "Products used in existing orders cannot be deleted." in response.text
    assert "Cancel" in response.text
    assert "Archive" not in response.text
    assert f"/admin/products/{product['id']}/archive" not in response.text

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
        data={"csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/products")},
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
        f"/admin/products/{product['id']}/delete",
        data={"csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/products")}
    )

    assert response.status_code == 400
    assert "Cannot delete product because it is used in existing orders." in response.text

def test_anonymous_and_customer_cannot_access_product_management_pages():
    product = create_test_product(stock=5, price=100)
    anonymous_client = TestClient(app)

    anonymous_response = anonymous_client.get(
        "/admin/products/new",
        follow_redirects=False,
    )

    assert anonymous_response.status_code == 303
    assert anonymous_response.headers["location"] == "/admin/login"

    customer_user = create_registered_user(role="customer")
    customer_client = TestClient(app)
    customer_client.cookies.set(
        ADMIN_SESSION_COOKIE_NAME,
        create_admin_session_token(type("SessionUser", (), customer_user)()),
    )

    customer_new_response = customer_client.get(
        "/admin/products/new",
        follow_redirects=False,
    )
    customer_edit_response = customer_client.get(
        f"/admin/products/{product['id']}/edit",
        follow_redirects=False,
    )
    customer_delete_response = customer_client.post(
        f"/admin/products/{product['id']}/delete",
        follow_redirects=False,
    )

    assert customer_new_response.status_code == 303
    assert customer_new_response.headers["location"] == "/admin/login"
    assert customer_edit_response.status_code == 303
    assert customer_edit_response.headers["location"] == "/admin/login"
    assert customer_delete_response.status_code == 303
    assert customer_delete_response.headers["location"] == "/admin/login"


def test_admin_product_create_shows_clear_validation_errors():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": "   ",
            "price": "19.99",
            "description": "Valid description",
            "stock": "5",
            "low_stock_threshold": "2",
            "category_id": str(category["id"]),
            "csrf_token": get_admin_ui_csrf_token(admin_client),
        },
    )

    assert response.status_code == 400
    assert "Product name is required" in response.text

def test_admin_product_create_rejects_more_than_two_decimal_places():
    category = create_test_category()
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": f"Admin Money Product {time.time()}",
            "price": "19.999",
            "description": "Created from admin UI",
            "image_url": "https://example.com/admin-product.jpg",
            "stock": "5",
            "low_stock_threshold": "5",
            "category_id": str(category["id"]),
            "csrf_token": get_admin_ui_csrf_token(admin_client),
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
            "csrf_token": get_admin_ui_csrf_token(admin_client, f"/admin/products/{product['id']}/edit"),
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


def _create_admin_ui_order(quantity: int = 2, price: float = 19.9, stock: int = 10):
    product = create_test_product(stock=stock, price=price)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=quantity,
        headers=customer_headers,
    )

    return product, customer, order


def test_admin_can_open_order_detail():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 200
    assert "Admin Order Detail" in response.text
    assert f"Order #{order['id']}" in response.text


def test_anonymous_and_non_admin_cannot_access_order_detail():
    product, customer, order = _create_admin_ui_order()

    anonymous_client = TestClient(app)
    anonymous_response = anonymous_client.get(
        f"/admin/orders/{order['id']}",
        follow_redirects=False,
    )

    non_admin_user = create_registered_user(role="customer")
    non_admin_client = TestClient(app)
    non_admin_client.cookies.set(
        ADMIN_SESSION_COOKIE_NAME,
        create_admin_session_token(type("UserLike", (), non_admin_user)()),
    )
    non_admin_response = non_admin_client.get(
        f"/admin/orders/{order['id']}",
        follow_redirects=False,
    )

    assert anonymous_response.status_code == 303
    assert anonymous_response.headers["location"] == "/admin/login"
    assert non_admin_response.status_code == 303
    assert non_admin_response.headers["location"] == "/admin/login"


def test_unknown_admin_order_detail_returns_404():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/orders/999999")

    assert response.status_code == 404
    assert "Order not found" in response.text


def test_admin_order_detail_shows_customer_items_and_money():
    product, customer, order = _create_admin_ui_order(quantity=2, price=19.9)

    admin_client = get_admin_ui_client()
    response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 200
    assert customer["name"] in response.text
    assert customer["email"] in response.text
    assert product["name"] in response.text
    assert "19.90" in response.text
    assert "39.80" in response.text


def test_admin_order_detail_contains_full_admin_navigation():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 200
    expected_links = [
        ("Dashboard", "/admin"),
        ("Products", "/admin/products"),
        ("Categories", "/admin/categories"),
        ("Customers", "/admin/customers"),
        ("Orders", "/admin/orders"),
        ("Low Stock", "/admin/low-stock"),
        ("Swagger UI", "/docs"),
        ("Logout", "/admin/logout"),
    ]
    for label, href in expected_links:
        assert label in response.text
        assert f'href="{href}"' in response.text
    assert "Admin Order Detail" in response.text
    assert f"Order #{order['id']}" in response.text


def test_admin_order_detail_contains_back_to_orders_link():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 200
    assert "Back to Orders" in response.text
    assert 'href="/admin/orders"' in response.text


def test_admin_orders_list_contains_order_detail_link():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert f'<a href="/admin/orders/{order["id"]}">{order["id"]}</a>' in response.text
    assert "View Details" in response.text



def test_admin_orders_page_displays_formatted_created_at_not_raw_default_repr():
    product, customer, order = _create_admin_ui_order()
    created_at = datetime(2026, 6, 15, 9, 7, 33, tzinfo=UTC)
    _set_order_admin_display_fields(order["id"], created_at=created_at)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "2026-06-15 09:07" in response.text
    assert "2026-06-15 09:07:33" not in response.text


def test_admin_order_detail_displays_formatted_created_at():
    product, customer, order = _create_admin_ui_order()
    created_at = datetime(2026, 6, 15, 10, 8, 44, tzinfo=UTC)
    _set_order_admin_display_fields(order["id"], created_at=created_at)

    admin_client = get_admin_ui_client()
    response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 200
    assert "Created At" in response.text
    assert "2026-06-15 10:08" in response.text
    assert "2026-06-15 10:08:44" not in response.text


def test_admin_customer_detail_embedded_orders_display_formatted_created_at():
    product, customer, order = _create_admin_ui_order()
    created_at = datetime(2026, 6, 15, 11, 9, 55, tzinfo=UTC)
    _set_order_admin_display_fields(order["id"], created_at=created_at)

    admin_client = get_admin_ui_client()
    response = admin_client.get(f"/admin/customers/{customer['id']}")

    assert response.status_code == 200
    assert "2026-06-15 11:09" in response.text
    assert "2026-06-15 11:09:55" not in response.text


def test_admin_customer_detail_embedded_orders_use_status_badges_for_all_statuses():
    expected_statuses = ["new", "paid", "shipped", "cancelled"]

    for status in expected_statuses:
        product, customer, order = _create_admin_ui_order()
        _set_order_admin_display_fields(order["id"], status=status)

        admin_client = get_admin_ui_client()
        response = admin_client.get(f"/admin/customers/{customer['id']}")

        assert response.status_code == 200
        assert f'class="status status-{status}"' in response.text
        assert f">{status}</span>" in response.text
        assert f"<td>{status}</td>" not in response.text

def test_admin_can_mark_new_order_as_paid_from_admin_ui():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(
        admin_client,
        path=f"/admin/orders/{order['id']}",
    )
    response = admin_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "paid", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    detail_response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 303
    assert response.headers["location"] == f"/admin/orders/{order['id']}"
    assert detail_response.status_code == 200
    assert "status-paid" in detail_response.text


def test_admin_can_mark_paid_order_as_shipped_from_admin_ui():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{order['id']}")
    paid_response = admin_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "paid", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{order['id']}")
    shipped_response = admin_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "shipped", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    detail_response = admin_client.get(f"/admin/orders/{order['id']}")

    assert paid_response.status_code == 303
    assert shipped_response.status_code == 303
    assert "status-shipped" in detail_response.text


def test_status_action_uses_existing_stock_restore_logic_when_cancelling():
    product, customer, order = _create_admin_ui_order(quantity=2, stock=5)

    product_after_order = client.get(f"/products/{product['id']}")
    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{order['id']}")
    cancel_response = admin_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "cancelled", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    product_after_cancel = client.get(f"/products/{product['id']}")

    assert product_after_order.status_code == 200
    assert product_after_order.json()["stock"] == 3
    assert cancel_response.status_code == 303
    assert product_after_cancel.status_code == 200
    assert product_after_cancel.json()["stock"] == 5



def test_admin_can_cancel_new_and_paid_order_from_admin_ui():
    admin_client = get_admin_ui_client()

    product, customer, new_order = _create_admin_ui_order()
    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{new_order['id']}")
    new_cancel_response = admin_client.post(
        f"/admin/orders/{new_order['id']}/status",
        data={"status": "cancelled", "csrf_token": csrf_token},
        follow_redirects=False,
    )

    product, customer, paid_order = _create_admin_ui_order()
    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{paid_order['id']}")
    paid_response = admin_client.post(
        f"/admin/orders/{paid_order['id']}/status",
        data={"status": "paid", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{paid_order['id']}")
    paid_cancel_response = admin_client.post(
        f"/admin/orders/{paid_order['id']}/status",
        data={"status": "cancelled", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    paid_detail_response = admin_client.get(f"/admin/orders/{paid_order['id']}")

    assert new_cancel_response.status_code == 303
    assert paid_response.status_code == 303
    assert paid_cancel_response.status_code == 303
    assert "status-cancelled" in paid_detail_response.text


def test_anonymous_and_customer_cannot_change_status_from_admin_ui():
    product, customer, order = _create_admin_ui_order()

    anonymous_client = TestClient(app)
    anonymous_response = anonymous_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "paid", "csrf_token": "irrelevant"},
        follow_redirects=False,
    )

    customer_user = create_registered_user(role="customer")
    customer_client = TestClient(app)
    customer_client.cookies.set(
        ADMIN_SESSION_COOKIE_NAME,
        create_admin_session_token(type("UserLike", (), customer_user)()),
    )
    customer_response = customer_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "paid", "csrf_token": "irrelevant"},
        follow_redirects=False,
    )
    detail_response = get_admin_ui_client().get(f"/admin/orders/{order['id']}")

    assert anonymous_response.status_code == 303
    assert anonymous_response.headers["location"] == "/admin/login"
    assert customer_response.status_code == 303
    assert customer_response.headers["location"] == "/admin/login"
    assert "status-new" in detail_response.text

def test_admin_order_status_missing_csrf_returns_403():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    response = admin_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "paid"},
    )

    assert response.status_code == 403


def test_admin_order_status_invalid_transition_is_rejected():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{order['id']}")
    response = admin_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "shipped", "csrf_token": csrf_token},
    )
    detail_response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 400
    assert "Cannot change order status from &#39;new&#39; to &#39;shipped&#39;" in response.text
    assert detail_response.status_code == 200
    assert "status-new" in detail_response.text


def test_admin_can_open_categories_page():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert "Admin Categories" in response.text
    assert "Create category" in response.text


def test_anonymous_cannot_open_categories_page():
    anonymous_client = TestClient(app)

    response = anonymous_client.get("/admin/categories", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_non_admin_cannot_open_categories_page():
    customer_user = create_registered_user(role="customer")
    non_admin_client = TestClient(app)
    non_admin_client.cookies.set(
        ADMIN_SESSION_COOKIE_NAME,
        create_admin_session_token(type("UserLike", (), customer_user)()),
    )

    response = non_admin_client.get("/admin/categories", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_can_create_category_from_ui_with_valid_csrf():
    admin_client = get_admin_ui_client()
    category_name = f"Admin UI Category {time.time()}"

    response = admin_client.post(
        "/admin/categories/create",
        data={
            "name": category_name,
            "csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/categories"),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/categories"

    categories_response = admin_client.get("/admin/categories")
    assert category_name in categories_response.text


def test_admin_category_create_missing_csrf_returns_403():
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/categories/create",
        data={"name": f"Missing CSRF Category {time.time()}"},
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_admin_category_create_empty_name_returns_controlled_error():
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        "/admin/categories/create",
        data={
            "name": "   ",
            "csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/categories"),
        },
    )

    assert response.status_code == 400
    assert "Category name is required" in response.text


def test_admin_category_create_duplicate_name_returns_controlled_error():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.post(
        "/admin/categories/create",
        data={
            "name": category["name"],
            "csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/categories"),
        },
    )

    assert response.status_code == 400
    assert "Category already exists" in response.text


def test_admin_can_edit_category_from_ui_with_valid_csrf():
    admin_client = get_admin_ui_client()
    category = create_test_category()
    updated_name = f"Edited Admin UI Category {time.time()}"

    response = admin_client.post(
        f"/admin/categories/{category['id']}/edit",
        data={
            "name": updated_name,
            "csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/categories"),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/categories"

    categories_response = admin_client.get("/admin/categories")
    assert updated_name in categories_response.text


def test_admin_category_edit_missing_csrf_returns_403():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.post(
        f"/admin/categories/{category['id']}/edit",
        data={"name": f"Missing Edit CSRF {time.time()}"},
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_admin_categories_empty_category_delete_ui_has_warning_confirmation_and_csrf():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert category["name"] in response.text
    assert f'/admin/categories/{category["id"]}/delete' in response.text
    assert "Deleting this empty category is permanent and cannot be undone." in response.text
    assert (
        "return confirm('Delete this category? This action cannot be undone.');"
        in response.text
    )
    assert 'name="csrf_token"' in response.text


def test_admin_categories_category_with_products_shows_blocked_delete_explanation():
    admin_client = get_admin_ui_client()
    product = create_test_product()

    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert (
        "Delete unavailable: this category has products. Move or delete those products first."
        in response.text
    )
    assert f'/admin/categories/{product["category_id"]}/delete' not in response.text


def test_admin_can_delete_empty_category_from_ui_with_valid_csrf():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.post(
        f"/admin/categories/{category['id']}/delete",
        data={"csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/categories")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/categories"

    categories_response = admin_client.get("/admin/categories")
    assert category["name"] not in categories_response.text


def test_admin_cannot_delete_category_that_has_products():
    admin_client = get_admin_ui_client()
    product = create_test_product()

    response = admin_client.post(
        f"/admin/categories/{product['category_id']}/delete",
        data={"csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/categories")},
    )

    assert response.status_code == 400
    assert "Cannot delete category with products" in response.text


def test_admin_category_delete_missing_csrf_returns_403():
    admin_client = get_admin_ui_client()
    category = create_test_category()

    response = admin_client.post(
        f"/admin/categories/{category['id']}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_categories_page_shows_created_and_edited_categories():
    admin_client = get_admin_ui_client()
    category_name = f"Visible Admin UI Category {time.time()}"
    edited_name = f"Visible Edited Admin UI Category {time.time()}"
    csrf_token = get_admin_ui_csrf_token(admin_client, "/admin/categories")

    create_response = admin_client.post(
        "/admin/categories/create",
        data={"name": category_name, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert create_response.status_code == 303

    categories_response = admin_client.get("/admin/categories")
    assert category_name in categories_response.text

    category_id = create_test_category()["id"]
    edit_response = admin_client.post(
        f"/admin/categories/{category_id}/edit",
        data={
            "name": edited_name,
            "csrf_token": get_admin_ui_csrf_token(admin_client, "/admin/categories"),
        },
        follow_redirects=False,
    )
    assert edit_response.status_code == 303

    edited_response = admin_client.get("/admin/categories")
    assert edited_name in edited_response.text


def test_admin_customers_list_contains_detail_links():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/customers")

    assert response.status_code == 200
    assert f'/admin/customers/{customer["id"]}' in response.text
    assert "View Details" in response.text


def test_admin_can_view_customer_detail():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Admin Customer Detail" in response.text
    assert f"Customer #{customer['id']}" in response.text
    assert str(customer["user_id"]) in response.text
    assert customer["name"] in response.text
    assert customer["email"] in response.text
    assert customer["phone"] in response.text


def test_anonymous_and_customer_cannot_access_customer_detail():
    customer = create_test_customer()

    anonymous_client = TestClient(app)
    anonymous_response = anonymous_client.get(
        f'/admin/customers/{customer["id"]}',
        follow_redirects=False,
    )

    db = TestingSessionLocal()
    try:
        customer_user = db.query(User).filter(User.id == customer["user_id"]).first()
        assert customer_user is not None
        customer_client = TestClient(app)
        customer_client.cookies.set(
            ADMIN_SESSION_COOKIE_NAME,
            create_admin_session_token(customer_user),
        )
    finally:
        db.close()

    customer_response = customer_client.get(
        f'/admin/customers/{customer["id"]}',
        follow_redirects=False,
    )

    assert anonymous_response.status_code == 303
    assert anonymous_response.headers["location"] == "/admin/login"
    assert customer_response.status_code == 303
    assert customer_response.headers["location"] == "/admin/login"


def test_unknown_customer_detail_returns_404():
    admin_client = get_admin_ui_client()

    response = admin_client.get('/admin/customers/999999')

    assert response.status_code == 404
    assert "Customer not found" in response.text


def test_customer_list_links_to_detail_page_from_id_and_name():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/customers")

    assert response.status_code == 200
    assert f'<a href="/admin/customers/{customer["id"]}">{customer["id"]}</a>' in response.text
    assert f'<a href="/admin/customers/{customer["id"]}">{customer["name"]}</a>' in response.text


def test_customer_detail_shows_related_orders_with_items_count():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    product = create_test_product()
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Orders" in response.text
    assert "Items Count" in response.text
    assert f'<td>{order["id"]}</td>' in response.text
    assert f'<td>{order["status"]}</td>' not in response.text
    assert f'>{order["status"]}</span>' in response.text
    assert '<td>1</td>' in response.text


def test_customer_detail_order_links_point_to_admin_order_detail():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    product = create_test_product()
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        headers=customer_headers,
    )
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert f'href="/admin/orders/{order["id"]}"' in response.text


def test_admin_customer_detail_page_shows_fields_and_orders():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    product = create_test_product()
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        headers=customer_headers,
    )
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Admin Customer Detail" in response.text
    assert str(customer["user_id"]) in response.text
    assert customer["name"] in response.text
    assert customer["email"] in response.text
    assert customer["phone"] in response.text
    assert f'/admin/orders/{order["id"]}' in response.text


def test_admin_customer_detail_contains_full_admin_navigation():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    expected_links = [
        ("Dashboard", "/admin"),
        ("Products", "/admin/products"),
        ("Categories", "/admin/categories"),
        ("Customers", "/admin/customers"),
        ("Orders", "/admin/orders"),
        ("Low Stock", "/admin/low-stock"),
        ("Swagger UI", "/docs"),
        ("Logout", "/admin/logout"),
    ]
    for label, href in expected_links:
        assert label in response.text
        assert f'href="{href}"' in response.text
    assert "Admin Customer Detail" in response.text
    assert f"Customer #{customer['id']}" in response.text


def test_admin_customer_detail_contains_back_to_customers_link():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Back to Customers" in response.text
    assert 'href="/admin/customers"' in response.text


def test_admin_can_edit_customer_from_ui_with_valid_csrf():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(
        admin_client,
        f'/admin/customers/{customer["id"]}',
    )

    response = admin_client.post(
        f'/admin/customers/{customer["id"]}/edit',
        data={
            "name": "Updated UI Customer",
            "email": f'updated_ui_{time.time()}@example.com',
            "phone": "+380501110000",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    detail_response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 303
    assert response.headers["location"] == f'/admin/customers/{customer["id"]}'
    assert detail_response.status_code == 200
    assert "Updated UI Customer" in detail_response.text
    assert "+380501110000" in detail_response.text


def test_admin_customer_edit_missing_csrf_returns_403():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.post(
        f'/admin/customers/{customer["id"]}/edit',
        data={
            "name": "Missing CSRF Customer",
            "email": f'missing_csrf_{time.time()}@example.com',
            "phone": "+380501110001",
        },
    )

    assert response.status_code == 403


def test_admin_customer_edit_empty_fields_returns_controlled_error():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(
        admin_client,
        f'/admin/customers/{customer["id"]}',
    )

    response = admin_client.post(
        f'/admin/customers/{customer["id"]}/edit',
        data={
            "name": " ",
            "email": customer["email"],
            "phone": customer["phone"],
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 400
    assert "Name, email and phone are required" in response.text


def test_admin_customer_edit_duplicate_email_returns_controlled_error():
    customer = create_test_customer()
    other_customer = create_test_customer()
    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(
        admin_client,
        f'/admin/customers/{customer["id"]}',
    )

    response = admin_client.post(
        f'/admin/customers/{customer["id"]}/edit',
        data={
            "name": customer["name"],
            "email": other_customer["email"],
            "phone": customer["phone"],
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 400
    assert "Customer with this email already exists" in response.text


def test_admin_customer_without_orders_delete_ui_has_warning_confirmation_and_csrf():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Deleting this customer is permanent and cannot be undone." in response.text
    assert (
        "return confirm('Delete this customer? This action cannot be undone.');"
        in response.text
    )
    assert f'/admin/customers/{customer["id"]}/delete' in response.text
    assert 'name="csrf_token"' in response.text


def test_admin_customer_with_orders_shows_blocked_delete_explanation():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    product = create_test_product()
    create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        headers=customer_headers,
    )
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert (
        "Delete unavailable: this customer has orders. "
        "Customer records with orders are retained for order history."
        in response.text
    )
    assert f'/admin/customers/{customer["id"]}/delete' not in response.text


def test_admin_can_delete_customer_with_no_orders_from_ui():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(
        admin_client,
        f'/admin/customers/{customer["id"]}',
    )

    response = admin_client.post(
        f'/admin/customers/{customer["id"]}/delete',
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    detail_response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/customers"
    assert detail_response.status_code == 404
    assert "Customer not found" in detail_response.text


def test_admin_customer_delete_missing_csrf_returns_403():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.post(f'/admin/customers/{customer["id"]}/delete')

    assert response.status_code == 403


def test_admin_customer_delete_with_orders_returns_controlled_error():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    product = create_test_product()
    create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        headers=customer_headers,
    )
    admin_client = get_admin_ui_client()
    csrf_token = get_admin_ui_csrf_token(
        admin_client,
        f'/admin/customers/{customer["id"]}',
    )

    response = admin_client.post(
        f'/admin/customers/{customer["id"]}/delete',
        data={"csrf_token": csrf_token},
    )

    assert response.status_code == 400
    assert "Customer cannot be deleted because they have orders" in response.text


def test_admin_orders_invalid_status_filter_returns_controlled_error():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/orders?status=invalid")

    assert response.status_code == 400
    assert "Invalid order status filter" in response.text
    assert "Filtered by status: <strong>invalid</strong>" not in response.text


def test_admin_order_detail_status_form_shows_valid_transitions_only():
    product, customer, order = _create_admin_ui_order()
    admin_client = get_admin_ui_client()

    new_response = admin_client.get(f"/admin/orders/{order['id']}")

    assert new_response.status_code == 200
    assert 'Mark as paid' in new_response.text
    assert 'Cancel order' in new_response.text
    assert 'value="paid"' in new_response.text
    assert 'value="cancelled"' in new_response.text
    assert 'Mark as shipped' not in new_response.text
    assert 'value="shipped"' not in new_response.text

    csrf_token = get_admin_ui_csrf_token(admin_client, path=f"/admin/orders/{order['id']}")
    paid_response = admin_client.post(
        f"/admin/orders/{order['id']}/status",
        data={"status": "paid", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    paid_detail_response = admin_client.get(f"/admin/orders/{order['id']}")

    assert paid_response.status_code == 303
    assert paid_detail_response.status_code == 200
    assert 'Mark as shipped' in paid_detail_response.text
    assert 'Cancel order' in paid_detail_response.text
    assert 'value="shipped"' in paid_detail_response.text
    assert 'value="cancelled"' in paid_detail_response.text
    assert 'value="new"' not in paid_detail_response.text
    assert 'value="paid"' not in paid_detail_response.text

def test_admin_dashboard_shows_overview_counts():
    response = build_isolated_admin_dashboard_response(
        {
            "new": ["1.00", "2.00"],
            "paid": ["3.00"],
        }
    )

    assert response.status_code == 200
    assert "<h2>Products</h2>\n                <p>2</p>" in response.text
    assert "<h2>Categories</h2>\n                <p>1</p>" in response.text
    assert "<h2>Customers</h2>\n                <p>1</p>" in response.text
    assert "<h2>Orders</h2>\n                <p>3</p>" in response.text
    assert "<h2>Low Stock Products</h2>\n                <p>1</p>" in response.text


def test_admin_dashboard_shows_orders_by_status():
    response = build_isolated_admin_dashboard_response(
        {
            "new": ["1.00", "2.00"],
            "paid": ["3.00"],
            "shipped": ["4.00", "5.00", "6.00"],
            "cancelled": ["7.00"],
        }
    )

    assert response.status_code == 200
    assert "<h2>New Orders</h2>\n                <p>2</p>" in response.text
    assert "<h2>Paid Orders</h2>\n                <p>1</p>" in response.text
    assert "<h2>Shipped Orders</h2>\n                <p>3</p>" in response.text
    assert "<h2>Cancelled Orders</h2>\n                <p>1</p>" in response.text


def test_admin_dashboard_recent_orders_link_to_order_detail():
    product = create_test_product(stock=10, price=100)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers,
    )

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Recent Orders" in response.text
    assert f'href="/admin/orders/{order["id"]}"' in response.text


def test_admin_dashboard_recent_customers_link_to_customer_detail():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Recent Customers" in response.text
    assert f'href="/admin/customers/{customer["id"]}"' in response.text
    assert customer["name"] in response.text


def test_anonymous_and_customer_cannot_access_admin_dashboard():
    anonymous_client = TestClient(app)
    anonymous_response = anonymous_client.get("/admin", follow_redirects=False)

    assert anonymous_response.status_code == 303
    assert anonymous_response.headers["location"] == "/admin/login"

    customer_user = create_registered_user(role="customer")
    customer_client = TestClient(app)
    customer_client.cookies.set(
        ADMIN_SESSION_COOKIE_NAME,
        create_admin_session_token(User(
            id=customer_user["id"],
            username=customer_user["username"],
            role="customer",
        )),
    )
    customer_response = customer_client.get("/admin", follow_redirects=False)

    assert customer_response.status_code == 303
    assert customer_response.headers["location"] == "/admin/login"
