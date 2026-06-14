from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Product, Customer, Order, User
from schemas import StatsSummaryResponse
from routes.auth import get_admin_user


router = APIRouter(
    prefix="/stats",
    tags=["stats"]
)


@router.get("/summary", response_model=StatsSummaryResponse)
def get_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    products_count = db.query(Product).count()
    customers_count = db.query(Customer).count()
    orders_count = db.query(Order).count()

    total_revenue = db.query(
        func.coalesce(func.sum(Order.total_price), Decimal("0.00"))
    ).filter(
        Order.status.in_(["paid", "shipped"])
    ).scalar()

    total_revenue = Decimal(total_revenue).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    return {
        "products_count": products_count,
        "customers_count": customers_count,
        "orders_count": orders_count,
        "total_revenue": total_revenue
    }