from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Product, Customer, Order
from schemas import StatsSummaryResponse


router = APIRouter(
    prefix="/stats",
    tags=["stats"]
)


@router.get("/summary", response_model=StatsSummaryResponse)
def get_stats_summary(db: Session = Depends(get_db)):
    products_count = db.query(Product).count()
    customers_count = db.query(Customer).count()
    orders_count = db.query(Order).count()

    paid_orders = db.query(Order).filter(
        Order.status.in_(["paid", "shipped"])
    ).all()

    total_revenue = 0

    for order in paid_orders:
        total_revenue += order.total_price

    return {
        "products_count": products_count,
        "customers_count": customers_count,
        "orders_count": orders_count,
        "total_revenue": total_revenue
    }