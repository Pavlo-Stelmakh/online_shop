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