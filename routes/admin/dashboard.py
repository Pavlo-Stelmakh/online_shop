from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database import get_db
from models import Category, Customer, Order, Product
from routes.admin.common import require_admin_ui, templates
from routes.stats import calculate_total_revenue


def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

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
    recent_orders = db.query(Order).order_by(Order.created_at.desc(), Order.id.desc()).limit(5).all()

    customer_columns = {column.key for column in inspect(Customer).columns}
    if "created_at" in customer_columns:
        recent_customers = (
            db.query(Customer)
            .order_by(Customer.created_at.desc(), Customer.id.desc())
            .limit(5)
            .all()
        )
    else:
        recent_customers = db.query(Customer).order_by(Customer.id.desc()).limit(5).all()

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
            "total_revenue": total_revenue,
            "recent_orders": recent_orders,
            "recent_customers": recent_customers
        }
    )
