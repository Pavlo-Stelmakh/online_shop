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
from models import Order, Product, User


def format_order_status_uk_for_test(status):
    return {
        "new": "Нове",
        "paid": "Оплачено",
        "shipped": "Відправлено",
        "cancelled": "Скасовано",
    }[status]



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
    assert "Адмін-панель Online Shop" in response.text

def test_admin_dashboard_contains_dashboard_cards():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Товари" in response.text
    assert "Категорії" in response.text
    assert "Клієнти" in response.text
    assert "Замовлення" in response.text

def test_admin_dashboard_displays_total_revenue():
    response = build_isolated_admin_dashboard_response({"paid": ["200.00"]})

    assert response.status_code == 200
    assert "Загальний дохід" in response.text
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
    assert "Товари" in response.text
    assert "Категорії" in response.text
    assert "Клієнти" in response.text
    assert "Замовлення" in response.text
    assert "Товари з низьким залишком" in response.text
    assert "Нові замовлення" in response.text
    assert "Оплачені замовлення" in response.text
    assert "Відправлені замовлення" in response.text
    assert "Скасовані замовлення" in response.text

def test_admin_dashboard_contains_quick_links():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Панель" in response.text
    assert "Товари" in response.text
    assert "Замовлення" in response.text
    assert "Категорії" in response.text
    assert "Клієнти" in response.text
    assert "Низькі залишки" in response.text
    assert "Swagger UI" in response.text
    assert "Перевірка стану" in response.text

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
    assert "Адмін: товари" in response.text

def test_admin_products_page_contains_product_table():
    create_test_product(stock=10, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Назва" in response.text
    assert "Ціна" in response.text
    assert "Залишок" in response.text
    assert "ID категорії" in response.text

def test_admin_dashboard_contains_admin_products_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Товари" in response.text
    assert "/admin/products" in response.text
    

def test_admin_orders_page_returns_200():


    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "Адмін: замовлення" in response.text

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
    assert "ID клієнта" in response.text
    assert "Статус" in response.text
    assert "Загальна сума" in response.text
    assert "Створено" in response.text
    assert "Кількість позицій" in response.text

def test_admin_dashboard_contains_admin_orders_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Замовлення" in response.text
    assert "/admin/orders" in response.text

def test_admin_categories_page_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert "Адмін: категорії" in response.text

def test_admin_categories_page_contains_categories_table_headers():
    create_test_category()

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Назва" in response.text
    assert "Кількість товарів" in response.text

def test_admin_dashboard_contains_admin_categories_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Категорії" in response.text
    assert "/admin/categories" in response.text

def test_admin_customers_page_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/customers")

    assert response.status_code == 200
    assert "Адмін: клієнти" in response.text

def test_admin_customers_page_contains_customers_table_headers():
    customer_headers = get_auth_headers(role="customer")
    create_test_customer(headers=customer_headers)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/customers")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "ID користувача" in response.text
    assert "Назва" in response.text
    assert "Email" in response.text
    assert "Телефон" in response.text

def test_admin_dashboard_contains_admin_customers_link():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Клієнти" in response.text
    assert "/admin/customers" in response.text

def test_admin_low_stock_page_returns_200():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert "Адмін: низькі залишки" in response.text

def test_admin_low_stock_page_contains_table_headers():
    create_test_product(stock=2, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/low-stock")

    assert response.status_code == 200
    assert "ID" in response.text
    assert "Назва" in response.text
    assert "Ціна" in response.text
    assert "Залишок" in response.text
    assert "ID категорії" in response.text

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
    assert "Низькі залишки" in response.text
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
    assert "Товари з низьким залишком" in response.text
    assert "Нові замовлення" in response.text
    assert "Оплачені замовлення" in response.text
    assert "Скасовані замовлення" in response.text

def test_admin_dashboard_low_stock_count_is_displayed():
    create_test_product(stock=2, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Товари з низьким залишком" in response.text


def test_admin_dashboard_low_stock_count_uses_product_specific_threshold():
    response = build_isolated_admin_dashboard_response(
        {},
        products=[
            {
                "name": f"Панель Custom Низькі залишки {time.time_ns()}",
                "price": Decimal("1.00"),
                "description": "Uses product-specific threshold",
                "stock": 8,
                "low_stock_threshold": 10,
            },
            {
                "name": f"Панель Hardcoded Five Regression {time.time_ns()}",
                "price": Decimal("2.00"),
                "description": "Would be low only with the old hardcoded rule",
                "stock": 6,
                "low_stock_threshold": 5,
            },
        ],
    )

    assert response.status_code == 200
    assert "Товари з низьким залишком" in response.text
    assert "<h2>Товари з низьким залишком</h2>\n                <p>1</p>" in response.text

def test_admin_dashboard_final_polish_content():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Версія: <strong>v4.0.0</strong>" in response.text
    assert "Ця панель надає візуальний огляд" in response.text
    assert "Сторінки адміністратора:" in response.text

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
        assert "Адмін-панель Online Shop — v4.0.0" in response.text

def test_admin_dashboard_order_status_cards_have_filtered_links():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200

    assert "Нові замовлення" in response.text
    assert "Оплачені замовлення" in response.text
    assert "Відправлені замовлення" in response.text
    assert "Скасовані замовлення" in response.text

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
    assert "Відфільтровано за статусом" in response.text
    assert "new" in response.text

def test_admin_orders_page_contains_status_filter_links():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert "Фільтр за статусом" in response.text

    assert "/admin/orders" in response.text
    assert "/admin/orders?status=new" in response.text
    assert "/admin/orders?status=paid" in response.text
    assert "/admin/orders?status=shipped" in response.text
    assert "/admin/orders?status=cancelled" in response.text

    assert "Усі" in response.text
    assert "Нове" in response.text
    assert "Оплачено" in response.text
    assert "Відправлено" in response.text
    assert "Скасовано" in response.text

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
    assert "Відфільтровано за статусом" in response.text
    assert "paid" in response.text

def test_admin_products_page_contains_filter_ui():
    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Фільтри товарів" in response.text
    assert "Пошук за назвою або описом" in response.text
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
    assert "Пошук категорій" in response.text
    assert "Пошук за назвою категорії" in response.text
    assert "Скинути" in response.text

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
    assert "Пошук клієнтів" in response.text
    assert "Пошук за іменем, email або телефоном" in response.text
    assert "Скинути" in response.text

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
    assert "Поріг низького залишку" in response.text

    # Both products currently use the default threshold.
    assert low_stock_product["name"] not in response.text
    assert normal_stock_product["name"] not in response.text

def test_admin_products_page_displays_low_stock_threshold():
    product = create_test_product(stock=3, price=100)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Поріг низького залишку" in response.text
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
    assert "Поріг низького залишку" in response.text

def test_admin_login_page_returns_200():
    anonymous_client = TestClient(app)

    response = anonymous_client.get("/admin/login")

    assert response.status_code == 200
    assert "Вхід адміністратора" in response.text
    assert "Ім’я користувача" in response.text
    assert "Пароль" in response.text

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
    assert "Недійсне ім’я користувача або пароль" in response.text

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
    assert "Потрібен доступ адміністратора" in response.text

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
    assert "Адмін-панель Online Shop" in response.text

def test_admin_can_open_new_product_form():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/products/new")

    assert response.status_code == 200
    assert "Додати товар" in response.text
    assert "Поріг низького залишку" in response.text
    assert "ID категорії" in response.text

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
    assert "Немає зображення" in response.text


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
    assert "URL зображення має починатися з http:// або https://" in response.text
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
    assert "URL зображення має починатися з http:// або https://" in response.text
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
    assert "Категорію не знайдено" in response.text



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
            "name": "Attempted Редагувати товар",
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
    assert 'value="Attempted Редагувати товар"' in response.text
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
            "name": "Negative Залишок Attempt",
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
    assert 'value="Negative Залишок Attempt"' in stock_response.text
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
    assert "Додати товар" in response.text
    assert "/admin/products/new" in response.text

def test_admin_product_edit_page_returns_200_for_admin():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get(f"/admin/products/{product['id']}/edit")

    assert response.status_code == 200
    assert "Редагувати товар" in response.text
    assert product["name"] in response.text
    assert "Поріг низького залишку" in response.text
    assert "Оновити товар" in response.text

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
    assert "Категорію не знайдено" in response.text

def test_admin_products_page_contains_edit_product_link():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Редагувати" in response.text
    assert f"/admin/products/{product['id']}/edit" in response.text

def test_admin_products_page_contains_delete_button_and_modal():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get("/admin/products")

    assert response.status_code == 200
    assert "Видалити" in response.text
    assert f"/admin/products/{product['id']}/delete" in response.text
    assert "Ви впевнені, що хочете видалити цей товар?" in response.text
    assert "Товари, використані в наявних замовленнях, не можна видалити." in response.text
    assert "Скасувати" in response.text

def test_admin_product_edit_page_contains_update_confirmation_modal():
    admin_client = get_admin_ui_client()
    product = create_test_product(stock=5, price=100)

    response = admin_client.get(f"/admin/products/{product['id']}/edit")

    assert response.status_code == 200
    assert "Оновити товар?" in response.text
    assert "Ви впевнені, що хочете зберегти ці зміни товару?" in response.text
    assert "Скасувати" in response.text
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
    assert "Неможливо видалити товар, оскільки він використовується в наявних замовленнях." in response.text

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
    assert "Назва товару не може бути порожньою" in response.text

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
    assert "більше ніж 2 десяткові знаки" in response.text

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
    assert "більше ніж 2 десяткові знаки" in response.text

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
    assert "Адмін: деталі замовлення" in response.text
    assert f"Замовлення №{order['id']}" in response.text


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
    assert "Замовлення не знайдено" in response.text


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
        ("Панель", "/admin"),
        ("Товари", "/admin/products"),
        ("Категорії", "/admin/categories"),
        ("Клієнти", "/admin/customers"),
        ("Замовлення", "/admin/orders"),
        ("Низькі залишки", "/admin/low-stock"),
        ("Swagger UI", "/docs"),
        ("Вийти", "/admin/logout"),
    ]
    for label, href in expected_links:
        assert label in response.text
        assert f'href="{href}"' in response.text
    assert "Адмін: деталі замовлення" in response.text
    assert f"Замовлення №{order['id']}" in response.text


def test_admin_order_detail_contains_back_to_orders_link():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    response = admin_client.get(f"/admin/orders/{order['id']}")

    assert response.status_code == 200
    assert "Повернутися до замовлень" in response.text
    assert 'href="/admin/orders"' in response.text


def test_admin_orders_list_contains_order_detail_link():
    product, customer, order = _create_admin_ui_order()

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin/orders")

    assert response.status_code == 200
    assert f'<a href="/admin/orders/{order["id"]}">{order["id"]}</a>' in response.text
    assert "Переглянути деталі" in response.text



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
    assert "Створено" in response.text
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
        assert f">{format_order_status_uk_for_test(status)}</span>" in response.text
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
    assert "Неможливо змінити статус замовлення з «Нове» на «Відправлено»" in response.text
    assert detail_response.status_code == 200
    assert "status-new" in detail_response.text


def test_admin_can_open_categories_page():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert "Адмін: категорії" in response.text
    assert "Створити категорію" in response.text


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
    assert "Назва категорії не може бути порожньою" in response.text


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
    assert "Категорія вже існує" in response.text


def test_admin_can_edit_category_from_ui_with_valid_csrf():
    admin_client = get_admin_ui_client()
    category = create_test_category()
    updated_name = f"Редагуватиed Admin UI Category {time.time()}"

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
        data={"name": f"Missing Редагувати CSRF {time.time()}"},
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
    assert "Видалення цієї порожньої категорії є остаточним і не може бути скасоване." in response.text
    assert (
        "return confirm('Видалити цю категорію? Цю дію не можна скасувати.');"
        in response.text
    )
    assert 'name="csrf_token"' in response.text


def test_admin_categories_category_with_products_shows_blocked_delete_explanation():
    admin_client = get_admin_ui_client()
    product = create_test_product()

    response = admin_client.get("/admin/categories")

    assert response.status_code == 200
    assert (
        "Видалення недоступне: ця категорія має товари. Спочатку перемістіть або видаліть ці товари."
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
    edited_name = f"Visible Редагуватиed Admin UI Category {time.time()}"
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
    assert "Переглянути деталі" in response.text


def test_admin_can_view_customer_detail():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Адмін: деталі клієнта" in response.text
    assert f"Клієнт №{customer['id']}" in response.text
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
    assert "Клієнта не знайдено" in response.text


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
    assert "Замовлення" in response.text
    assert "Кількість позицій" in response.text
    assert f'<td>{order["id"]}</td>' in response.text
    assert f'<td>{order["status"]}</td>' not in response.text
    assert f'>{format_order_status_uk_for_test(order["status"])}</span>' in response.text
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
    assert "Адмін: деталі клієнта" in response.text
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
        ("Панель", "/admin"),
        ("Товари", "/admin/products"),
        ("Категорії", "/admin/categories"),
        ("Клієнти", "/admin/customers"),
        ("Замовлення", "/admin/orders"),
        ("Низькі залишки", "/admin/low-stock"),
        ("Swagger UI", "/docs"),
        ("Вийти", "/admin/logout"),
    ]
    for label, href in expected_links:
        assert label in response.text
        assert f'href="{href}"' in response.text
    assert "Адмін: деталі клієнта" in response.text
    assert f"Клієнт №{customer['id']}" in response.text


def test_admin_customer_detail_contains_back_to_customers_link():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Повернутися до клієнтів" in response.text
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
    assert "Ім’я, email і телефон є обов’язковими" in response.text


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
    assert "Клієнт із цим email уже існує" in response.text


def test_admin_customer_without_orders_delete_ui_has_warning_confirmation_and_csrf():
    customer = create_test_customer()
    admin_client = get_admin_ui_client()

    response = admin_client.get(f'/admin/customers/{customer["id"]}')

    assert response.status_code == 200
    assert "Видалення цього клієнта є остаточним і не може бути скасоване." in response.text
    assert (
        "return confirm('Видалити цього клієнта? Цю дію не можна скасувати.');"
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
        "Видалення недоступне: цей клієнт має замовлення. "
        "Записи клієнтів із замовленнями зберігаються для історії замовлень."
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
    assert "Клієнта не знайдено" in detail_response.text


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
    assert "Неможливо видалити клієнта, оскільки він має замовлення" in response.text


def test_admin_orders_invalid_status_filter_returns_controlled_error():
    admin_client = get_admin_ui_client()

    response = admin_client.get("/admin/orders?status=invalid")

    assert response.status_code == 400
    assert "Недійсний фільтр статусу замовлення" in response.text
    assert "Відфільтровано за статусом: <strong>invalid</strong>" not in response.text


def test_admin_order_detail_status_form_shows_valid_transitions_only():
    product, customer, order = _create_admin_ui_order()
    admin_client = get_admin_ui_client()

    new_response = admin_client.get(f"/admin/orders/{order['id']}")

    assert new_response.status_code == 200
    assert 'Позначити як оплачене' in new_response.text
    assert 'Скасувати замовлення' in new_response.text
    assert 'value="paid"' in new_response.text
    assert 'value="cancelled"' in new_response.text
    assert 'Позначити як відправлене' not in new_response.text
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
    assert 'Позначити як відправлене' in paid_detail_response.text
    assert 'Скасувати замовлення' in paid_detail_response.text
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
    assert "<h2>Товари</h2>\n                <p>2</p>" in response.text
    assert "<h2>Категорії</h2>\n                <p>1</p>" in response.text
    assert "<h2>Клієнти</h2>\n                <p>1</p>" in response.text
    assert "<h2>Замовлення</h2>\n                <p>3</p>" in response.text
    assert "<h2>Товари з низьким залишком</h2>\n                <p>1</p>" in response.text


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
    assert "<h2>Нові замовлення</h2>\n                <p>2</p>" in response.text
    assert "<h2>Оплачені замовлення</h2>\n                <p>1</p>" in response.text
    assert "<h2>Відправлені замовлення</h2>\n                <p>3</p>" in response.text
    assert "<h2>Скасовані замовлення</h2>\n                <p>1</p>" in response.text


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
    assert "Останні замовлення" in response.text
    assert f'href="/admin/orders/{order["id"]}"' in response.text


def test_admin_dashboard_recent_customers_link_to_customer_detail():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_client = get_admin_ui_client()
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "Останні клієнти" in response.text
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


def test_admin_create_product_uploads_image_file(monkeypatch):
    from routes.admin import products as admin_products_routes

    admin_client = get_admin_ui_client()
    category = create_test_category()
    product_name = f"Admin Upload Product {time.time()}"
    uploaded_url = f"https://cdn.example.com/admin-upload-{time.time()}.webp"
    calls = []

    def fake_upload_product_image(file, product_id):
        calls.append((file.filename, file.content_type, product_id))
        return uploaded_url

    monkeypatch.setattr(
        admin_products_routes,
        "upload_product_image",
        fake_upload_product_image,
    )

    response = admin_client.post(
        "/admin/products/new",
        data={
            "name": product_name,
            "price": 150,
            "description": "Created from admin UI with an uploaded image",
            "stock": 7,
            "low_stock_threshold": 10,
            "category_id": category["id"],
            "csrf_token": get_admin_ui_csrf_token(admin_client),
        },
        files={"image_file": ("product.webp", b"fake image", "image/webp")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"
    assert len(calls) == 1
    assert calls[0][0] == "product.webp"
    assert calls[0][1] == "image/webp"
    assert isinstance(calls[0][2], int)

    products_response = admin_client.get("/admin/products")

    assert products_response.status_code == 200
    assert product_name in products_response.text
    assert f'src="{uploaded_url}"' in products_response.text


def test_admin_edit_product_shows_current_image_and_uploads_replacement(monkeypatch):
    from routes.admin import products as admin_products_routes

    admin_client = get_admin_ui_client()
    original_url = f"https://example.com/original-{time.time()}.jpg"
    replacement_url = f"https://cdn.example.com/replacement-{time.time()}.png"
    product = create_test_product(stock=5, price=100)
    db = TestingSessionLocal()

    try:
        db_product = db.query(Product).filter(Product.id == product["id"]).first()
        assert db_product is not None
        db_product.image_url = original_url
        db.commit()
    finally:
        db.close()

    calls = []

    edit_page_response = admin_client.get(f"/admin/products/{product['id']}/edit")

    assert edit_page_response.status_code == 200
    assert 'class="current-product-image"' in edit_page_response.text
    assert f'src="{original_url}"' in edit_page_response.text
    assert 'name="image_file"' in edit_page_response.text

    def fake_upload_product_image(file, product_id):
        calls.append((file.filename, file.content_type, product_id))
        return replacement_url

    monkeypatch.setattr(
        admin_products_routes,
        "upload_product_image",
        fake_upload_product_image,
    )

    response = admin_client.post(
        f"/admin/products/{product['id']}/edit",
        data={
            "name": product["name"],
            "price": 250,
            "description": "Updated with replacement image",
            "image_url": original_url,
            "stock": 12,
            "low_stock_threshold": 20,
            "category_id": product["category_id"],
            "csrf_token": get_admin_ui_csrf_token(
                admin_client,
                f"/admin/products/{product['id']}/edit",
            ),
        },
        files={"image_file": ("replacement.png", b"fake image", "image/png")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"
    assert calls == [("replacement.png", "image/png", product["id"])]

    products_response = admin_client.get("/admin/products")

    assert products_response.status_code == 200
    assert f'src="{replacement_url}"' in products_response.text
