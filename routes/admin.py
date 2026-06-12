import os
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, Request, Form, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from jose import jwt, JWTError

from auth import verify_password, SECRET_KEY, ALGORITHM
from database import get_db
from models import Product, Category, Customer, Order, User, OrderItem

router = APIRouter(
    prefix="/admin",
    tags=["admin dashboard"]
)

templates = Jinja2Templates(directory="templates")

ADMIN_SESSION_COOKIE_NAME = "admin_session"
ADMIN_SESSION_EXPIRE_SECONDS = int(
    os.getenv("ADMIN_SESSION_EXPIRE_SECONDS", "1800")
)
ADMIN_SESSION_TOKEN_TYPE = "admin_ui_session"


def is_admin_cookie_secure() -> bool:
    environment = os.getenv("ENVIRONMENT", os.getenv("ENV", "")).lower()

    return environment in {"production", "prod"} or os.getenv("RENDER") == "true"


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
            "error": None
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
                "error": "Invalid username or password"
            },
            status_code=401
        )

    if user.role != "admin":
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={
                "error": "Admin access required"
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

    low_stock_count = db.query(Product).filter(Product.stock <= 5).count()
    new_orders_count = db.query(Order).filter(Order.status == "new").count()
    paid_orders_count = db.query(Order).filter(Order.status == "paid").count()
    shipped_orders_count = db.query(Order).filter(Order.status == "shipped").count()
    cancelled_orders_count = db.query(Order).filter(Order.status == "cancelled").count()


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
            "cancelled_orders_count": cancelled_orders_count
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
            "error": None
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
            "error": None
        }
    )


@router.post("/products/create")
def admin_product_create(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    description: str = Form(...),
    image_url: str | None = Form(None),
    stock: int = Form(...),
    low_stock_threshold: int = Form(...),
    category_id: int = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    if price <= 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "price must be greater than 0"
            },
            status_code=400
        )

    if stock < 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "stock must be greater than or equal to 0"
            },
            status_code=400
        )

    if low_stock_threshold < 1 or low_stock_threshold > 100:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "low_stock_threshold must be between 1 and 100"
            },
            status_code=400
        )

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "Category not found"
            },
            status_code=404
        )

    product = Product(
        name=name,
        price=price,
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
            "error": None
        }
    )


@router.post("/products/{product_id}/edit")
def admin_product_edit(
    product_id: int,
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    description: str = Form(...),
    image_url: str | None = Form(None),
    stock: int = Form(...),
    low_stock_threshold: int = Form(...),
    category_id: int = Form(...),
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

    if price <= 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "price must be greater than 0"
            },
            status_code=400
        )

    if stock < 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "stock must be greater than or equal to 0"
            },
            status_code=400
        )

    if low_stock_threshold < 1 or low_stock_threshold > 100:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "low_stock_threshold must be between 1 and 100"
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
                "error": "Category not found"
            },
            status_code=404
        )

    product.name = name
    product.price = price
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
                "error": "Product cannot be deleted because it is used in orders."
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

    if status is not None:
        query = query.filter(Order.status == status)

    orders = query.order_by(Order.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_orders.html",
        context={
            "orders": orders,
            "status": status
        }
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

    return templates.TemplateResponse(
        request=request,
        name="admin_categories.html",
        context={
            "categories": categories_with_counts,
            "search": search or ""
        }
    )


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

