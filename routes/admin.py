import hashlib
import os
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, Request, Form, Response, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from jose import jwt, JWTError

from auth import verify_password, SECRET_KEY, ALGORITHM, is_production_environment
from database import get_db
from models import Product, Category, Customer, Order, User, OrderItem
from routes.orders import update_order_status
from schemas import ORDER_STATUS_TRANSITIONS, ORDER_STATUS_VALUES
from routes.stats import calculate_total_revenue
from utils.money import MoneyValidationError, format_money, parse_positive_money

ORDER_STATUSES = ORDER_STATUS_VALUES

router = APIRouter(
    prefix="/admin",
    tags=["admin dashboard"]
)

templates = Jinja2Templates(directory="templates")
templates.env.filters["money"] = format_money


def format_admin_datetime(value: datetime | None) -> str:
    if value is None:
        return ""

    return value.strftime("%Y-%m-%d %H:%M")


templates.env.filters["datetime"] = format_admin_datetime

ADMIN_SESSION_COOKIE_NAME = "admin_session"
ADMIN_SESSION_EXPIRE_SECONDS = int(
    os.getenv("ADMIN_SESSION_EXPIRE_SECONDS", "1800")
)
ADMIN_SESSION_TOKEN_TYPE = "admin_ui_session"
ADMIN_CSRF_TOKEN_TYPE = "admin_ui_csrf"



def is_admin_cookie_secure() -> bool:
    return is_production_environment()


def create_admin_session_token(user: User) -> str:
    expire = datetime.now(UTC) + timedelta(
        seconds=ADMIN_SESSION_EXPIRE_SECONDS
    )

    payload = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "typ": ADMIN_SESSION_TOKEN_TYPE,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def create_admin_csrf_token(admin_session_token: str) -> str:
    session_digest = hashlib.sha256(
        admin_session_token.encode("utf-8")
    ).hexdigest()

    payload = {
        "typ": ADMIN_CSRF_TOKEN_TYPE,
        "session_sha256": session_digest
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def validate_admin_csrf_token(
    admin_session_token: str,
    csrf_token: str | None
) -> bool:
    if not csrf_token:
        return False

    try:
        payload = jwt.decode(
            csrf_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        return False

    if payload.get("typ") != ADMIN_CSRF_TOKEN_TYPE:
        return False

    expected_digest = hashlib.sha256(
        admin_session_token.encode("utf-8")
    ).hexdigest()

    return payload.get("session_sha256") == expected_digest



def build_admin_categories_context(
    request: Request,
    db: Session,
    search: str | None = None,
    error: str | None = None
):
    query = db.query(Category)

    if search is not None:
        search_value = search.strip()

        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(Category.name.ilike(search_pattern))

    categories = query.order_by(Category.id.desc()).all()

    categories_with_counts = []

    for category in categories:
        products_count = db.query(Product).filter(
            Product.category_id == category.id
        ).count()

        categories_with_counts.append(
            {
                "category": category,
                "products_count": products_count
            }
        )

    return {
        "categories": categories_with_counts,
        "search": search or "",
        "error": error,
        "csrf_token": get_admin_csrf_token(request)
    }


def render_admin_categories(
    request: Request,
    db: Session,
    search: str | None = None,
    error: str | None = None,
    status_code: int = 200
):
    return templates.TemplateResponse(
        request=request,
        name="admin_categories.html",
        context=build_admin_categories_context(request, db, search, error),
        status_code=status_code
    )



def build_product_form_values(
    name: str,
    price: str,
    description: str,
    image_url: str | None,
    stock: int,
    low_stock_threshold: int,
    category_id: int
) -> dict[str, str | int]:
    return {
        "name": name,
        "price": price,
        "description": description,
        "image_url": image_url or "",
        "stock": stock,
        "low_stock_threshold": low_stock_threshold,
        "category_id": category_id
    }


def build_customer_form_values(
    name: str,
    email: str,
    phone: str
) -> dict[str, str]:
    return {
        "name": name,
        "email": email,
        "phone": phone
    }

def require_admin_csrf(request: Request, csrf_token: str | None):
    admin_session_token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)

    if not admin_session_token:
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    if not validate_admin_csrf_token(admin_session_token, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def get_admin_csrf_token(request: Request) -> str:
    admin_session_token = request.cookies[ADMIN_SESSION_COOKIE_NAME]

    return create_admin_csrf_token(admin_session_token)


def decode_admin_session_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        return None

    if payload.get("typ") != ADMIN_SESSION_TOKEN_TYPE:
        return None

    if payload.get("role") != "admin":
        return None

    username = payload.get("sub")
    user_id = payload.get("user_id")

    if username is None or user_id is None:
        return None

    return payload

def get_admin_from_cookie(
    request: Request,
    db: Session
):
    token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)

    if token is None:
        return None

    payload = decode_admin_session_token(token)

    if payload is None:
        return None

    user = db.query(User).filter(
        User.id == payload["user_id"],
        User.username == payload["sub"]
    ).first()

    if user is None:
        return None

    if user.role != "admin":
        return None

    return user


def require_admin_ui(
    request: Request,
    db: Session
):
    user = get_admin_from_cookie(request, db)

    if user is None:
        return RedirectResponse(
            url="/admin/login",
            status_code=303
        )

    return user

@router.get("/login")
def admin_login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={
            "error": None,
            "form_values": {}
        }
    )


@router.post("/login")
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if user is None or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={
                "error": "Invalid username or password",
                "form_values": {"username": username}
            },
            status_code=401
        )

    if user.role != "admin":
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={
                "error": "Admin access required",
                "form_values": {"username": username}
            },
            status_code=403
        )

    response = RedirectResponse(
        url="/admin",
        status_code=303
    )

    response.set_cookie(
        key=ADMIN_SESSION_COOKIE_NAME,
        value=create_admin_session_token(user),
        httponly=True,
        samesite="lax",
        secure=is_admin_cookie_secure(),
        max_age=ADMIN_SESSION_EXPIRE_SECONDS
    )

    return response


@router.get("/logout")
def admin_logout():
    response = RedirectResponse(
        url="/admin/login",
        status_code=303
    )

    response.delete_cookie(ADMIN_SESSION_COOKIE_NAME)
    response.delete_cookie("admin_username")

    return response


@router.get("")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    products_count = db.query(Product).count()
    categories_count = db.query(Category).count()
    customers_count = db.query(Customer).count()
    orders_count = db.query(Order).count()

    low_stock_count = db.query(Product).filter(
        Product.stock <= Product.low_stock_threshold
    ).count()
    new_orders_count = db.query(Order).filter(Order.status == "new").count()
    paid_orders_count = db.query(Order).filter(Order.status == "paid").count()
    shipped_orders_count = db.query(Order).filter(Order.status == "shipped").count()
    cancelled_orders_count = db.query(Order).filter(Order.status == "cancelled").count()
    total_revenue = calculate_total_revenue(db)

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "products_count": products_count,
            "categories_count": categories_count,
            "customers_count": customers_count,
            "orders_count": orders_count,
            "low_stock_count": low_stock_count,
            "new_orders_count": new_orders_count,
            "paid_orders_count": paid_orders_count,
            "shipped_orders_count": shipped_orders_count,
            "cancelled_orders_count": cancelled_orders_count,
            "total_revenue": total_revenue
        }
    )


@router.get("/products")
def admin_products(
    request: Request,
    search: str | None = None,
    in_stock: bool | None = None,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    query = db.query(Product)

    if search is not None:
        search_value = search.strip()

        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(
                (Product.name.ilike(search_pattern)) |
                (Product.description.ilike(search_pattern))
            )

    if in_stock is not None:
        if in_stock:
            query = query.filter(Product.stock > 0)
        else:
            query = query.filter(Product.stock == 0)

    products = query.order_by(Product.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_products.html",
        context={
            "products": products,
            "search": search or "",
            "in_stock": in_stock,
            "error": None,
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.get("/products/create")
def admin_product_create_page(
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    return templates.TemplateResponse(
        request=request,
        name="admin_product_create.html",
        context={
            "error": None,
            "form_values": {},
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.post("/products/create")
def admin_product_create(
    request: Request,
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form(...),
    image_url: str | None = Form(None),
    stock: int = Form(...),
    low_stock_threshold: int = Form(...),
    category_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    form_values = build_product_form_values(
        name,
        price,
        description,
        image_url,
        stock,
        low_stock_threshold,
        category_id
    )

    try:
        price_amount = parse_positive_money(price)
    except MoneyValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": str(exc),
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if stock < 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "stock must be greater than or equal to 0",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if low_stock_threshold < 1 or low_stock_threshold > 100:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "low_stock_threshold must be between 1 and 100",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "Category not found",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    product = Product(
        name=name,
        price=price_amount,
        description=description,
        image_url=image_url,
        stock=stock,
        low_stock_threshold=low_stock_threshold,
        category_id=category_id
    )

    db.add(product)
    db.commit()

    return RedirectResponse(
        url="/admin/products",
        status_code=303
    )


@router.get("/products/{product_id}/edit")
def admin_product_edit_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        return RedirectResponse(
            url="/admin/products",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_product_edit.html",
        context={
            "product": product,
            "error": None,
            "form_values": {},
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.post("/products/{product_id}/edit")
def admin_product_edit(
    product_id: int,
    request: Request,
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form(...),
    image_url: str | None = Form(None),
    stock: int = Form(...),
    low_stock_threshold: int = Form(...),
    category_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        return RedirectResponse(
            url="/admin/products",
            status_code=303
        )

    form_values = build_product_form_values(
        name,
        price,
        description,
        image_url,
        stock,
        low_stock_threshold,
        category_id
    )

    try:
        price_amount = parse_positive_money(price)
    except MoneyValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": str(exc),
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if stock < 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "stock must be greater than or equal to 0",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if low_stock_threshold < 1 or low_stock_threshold > 100:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "low_stock_threshold must be between 1 and 100",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "Category not found",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    product.name = name
    product.price = price_amount
    product.description = description
    product.image_url = image_url
    product.stock = stock
    product.low_stock_threshold = low_stock_threshold
    product.category_id = category_id

    db.commit()

    return RedirectResponse(
        url="/admin/products",
        status_code=303
    )

@router.post("/products/{product_id}/delete")
def admin_product_delete(
    product_id: int,
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        return RedirectResponse(
            url="/admin/products",
            status_code=303
        )

    related_order_items_count = db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).count()

    if related_order_items_count > 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_products.html",
            context={
                "products": db.query(Product).order_by(Product.id.desc()).all(),
                "search": "",
                "in_stock": None,
                "error": "Product cannot be deleted because it is used in orders.",
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    db.delete(product)
    db.commit()

    return RedirectResponse(
        url="/admin/products",
        status_code=303
    )


@router.get("/orders")
def admin_orders(
    request: Request,
    status: str | None = None,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    query = db.query(Order)

    error = None

    if status is not None:
        if status not in ORDER_STATUSES:
            error = "Invalid order status filter"
        else:
            query = query.filter(Order.status == status)

    orders = [] if error else query.order_by(Order.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_orders.html",
        context={
            "orders": orders,
            "status": status if error is None else None,
            "error": error
        },
        status_code=400 if error else 200
    )


@router.get("/orders/{order_id}")
def admin_order_detail(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        return RedirectResponse(
            url="/admin/orders",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_order_detail.html",
        context={
            "order": order,
            "statuses": ORDER_STATUS_TRANSITIONS[order.status],
            "error": None,
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.post("/orders/{order_id}/status")
def admin_order_status_update(
    order_id: int,
    request: Request,
    status: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    if status not in ORDER_STATUSES:
        order = db.query(Order).filter(Order.id == order_id).first()

        if order is None:
            return RedirectResponse(
                url="/admin/orders",
                status_code=303
            )

        return templates.TemplateResponse(
            request=request,
            name="admin_order_detail.html",
            context={
                "order": order,
                "statuses": ORDER_STATUS_TRANSITIONS[order.status],
                "error": "Invalid order status",
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    try:
        update_order_status(
            order_id=order_id,
            status=status,
            db=db,
            current_user=admin_user
        )
    except HTTPException as exc:
        order = db.query(Order).filter(Order.id == order_id).first()

        if order is None:
            return RedirectResponse(
                url="/admin/orders",
                status_code=303
            )

        return templates.TemplateResponse(
            request=request,
            name="admin_order_detail.html",
            context={
                "order": order,
                "statuses": ORDER_STATUS_TRANSITIONS[order.status],
                "error": exc.detail,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=exc.status_code
        )

    return RedirectResponse(
        url=f"/admin/orders/{order_id}",
        status_code=303
    )


@router.get("/categories")
def admin_categories(
    request: Request,
    search: str | None = None,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    return render_admin_categories(request, db, search)


@router.post("/categories/create")
def admin_category_create(
    request: Request,
    name: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    category_name = name.strip()

    if not category_name:
        return render_admin_categories(
            request,
            db,
            error="Category name is required",
            status_code=400
        )

    existing_category = db.query(Category).filter(
        Category.name == category_name
    ).first()

    if existing_category is not None:
        return render_admin_categories(
            request,
            db,
            error="Category already exists",
            status_code=400
        )

    category = Category(name=category_name)
    db.add(category)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_admin_categories(
            request,
            db,
            error="Category already exists",
            status_code=400
        )

    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/categories/{category_id}/edit")
def admin_category_edit(
    category_id: int,
    request: Request,
    name: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return render_admin_categories(
            request,
            db,
            error="Category not found",
            status_code=404
        )

    category_name = name.strip()

    if not category_name:
        return render_admin_categories(
            request,
            db,
            error="Category name is required",
            status_code=400
        )

    existing_category = db.query(Category).filter(
        Category.name == category_name,
        Category.id != category_id
    ).first()

    if existing_category is not None:
        return render_admin_categories(
            request,
            db,
            error="Category already exists",
            status_code=400
        )

    category.name = category_name

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_admin_categories(
            request,
            db,
            error="Category already exists",
            status_code=400
        )

    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
def admin_category_delete(
    category_id: int,
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return render_admin_categories(
            request,
            db,
            error="Category not found",
            status_code=404
        )

    products_count = db.query(Product).filter(
        Product.category_id == category_id
    ).count()

    if products_count > 0:
        return render_admin_categories(
            request,
            db,
            error="Cannot delete category with products",
            status_code=400
        )

    db.delete(category)
    db.commit()

    return RedirectResponse(url="/admin/categories", status_code=303)


@router.get("/customers")
def admin_customers(
    request: Request,
    search: str | None = None,
    db: Session = Depends(get_db)
):

    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    query = db.query(Customer)

    if search is not None:
        search_value = search.strip()

        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(
                (Customer.name.ilike(search_pattern)) |
                (Customer.email.ilike(search_pattern)) |
                (Customer.phone.ilike(search_pattern))
            )

    customers = query.order_by(Customer.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_customers.html",
        context={
            "customers": customers,
            "search": search or ""
        }
    )


def render_admin_customer_detail(
    request: Request,
    customer: Customer | None,
    error: str | None = None,
    status_code: int = 200,
    form_values: dict[str, str] | None = None
):
    return templates.TemplateResponse(
        request=request,
        name="admin_customer_detail.html",
        context={
            "customer": customer,
            "error": error,
            "form_values": form_values or {},
            "csrf_token": get_admin_csrf_token(request)
        },
        status_code=status_code
    )


@router.get("/customers/{customer_id}")
def admin_customer_detail(
    customer_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_customer_detail.html",
            context={
                "customer": None,
                "error": "Customer not found",
                "form_values": {},
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    return render_admin_customer_detail(request, customer)


@router.post("/customers/{customer_id}/edit")
def admin_customer_edit(
    customer_id: int,
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_customer_detail.html",
            context={
                "customer": None,
                "error": "Customer not found",
                "form_values": {},
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    form_values = build_customer_form_values(name, email, phone)

    name_value = name.strip()
    email_value = email.strip()
    phone_value = phone.strip()

    if not name_value or not email_value or not phone_value:
        return render_admin_customer_detail(
            request,
            customer,
            error="Name, email and phone are required",
            status_code=400,
            form_values=form_values
        )

    existing_customer = db.query(Customer).filter(
        Customer.email == email_value,
        Customer.id != customer_id
    ).first()

    if existing_customer is not None:
        return render_admin_customer_detail(
            request,
            customer,
            error="Customer with this email already exists",
            status_code=400,
            form_values=form_values
        )

    customer.name = name_value
    customer.email = email_value
    customer.phone = phone_value

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_admin_customer_detail(
            request,
            customer,
            error="Customer could not be updated",
            status_code=400,
            form_values=form_values
        )

    return RedirectResponse(
        url=f"/admin/customers/{customer.id}",
        status_code=303
    )


@router.post("/customers/{customer_id}/delete")
def admin_customer_delete(
    customer_id: int,
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_customer_detail.html",
            context={
                "customer": None,
                "error": "Customer not found",
                "form_values": {},
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    existing_order = db.query(Order).filter(
        Order.customer_id == customer_id
    ).first()

    if existing_order is not None:
        return render_admin_customer_detail(
            request,
            customer,
            error="Customer cannot be deleted because they have orders",
            status_code=400
        )

    db.delete(customer)
    db.commit()

    return RedirectResponse(url="/admin/customers", status_code=303)

@router.get("/low-stock")
def admin_low_stock(
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    products = db.query(Product).filter(
        Product.stock <= Product.low_stock_threshold
    ).order_by(Product.stock.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_low_stock.html",
        context={
            "products": products
        }
    )
