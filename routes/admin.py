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

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "products_count": products_count,
            "categories_count": categories_count,
            "customers_count": customers_count,
            "orders_count": orders_count
        }
    )


@router.get("/products")
def admin_products(
    request: Request,
    db: Session = Depends(get_db)
):
    products = db.query(Product).order_by(Product.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_products.html",
        context={
            "products": products
        }
    )


@router.get("/orders")
def admin_orders(
    request: Request,
    db: Session = Depends(get_db)
):
    orders = db.query(Order).order_by(Order.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_orders.html",
        context={
            "orders": orders
        }
    )


@router.get("/categories")
def admin_categories(
    request: Request,
    db: Session = Depends(get_db)
):
    categories = db.query(Category).order_by(Category.id.desc()).all()

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
            "categories": categories_with_counts
        }
    )
