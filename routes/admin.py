from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Product, Category, Customer, Order


router = APIRouter(
    prefix="/admin",
    tags=["admin dashboard"]
)

templates = Jinja2Templates(directory="templates")


@router.get("")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
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
            "in_stock": in_stock
        }
    )


@router.get("/orders")
def admin_orders(
    request: Request,
    status: str | None = None,
    db: Session = Depends(get_db)
):
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
    threshold = 5

    products = db.query(Product).filter(
        Product.stock <= threshold
    ).order_by(Product.stock.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_low_stock.html",
        context={
            "products": products,
            "threshold": threshold
        }
    )

