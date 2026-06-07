from itertools import product

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Order, OrderItem, Customer, Product, User
from schemas import OrderCreate, OrderResponse
from routes.auth import get_current_user, get_admin_user
from datetime import date, time, datetime


router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@router.post("", response_model=OrderResponse)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.id == order_data.customer_id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    if current_user.role != "admin" and customer.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can create orders only for your own customer profile"
        )

    order = Order(
        customer_id=order_data.customer_id,
        status="new",
        total_price=0
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    total_price = 0

    for item_data in order_data.items:
        product = db.query(Product).filter(
            Product.id == item_data.product_id
        ).first()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product with id {item_data.product_id} not found"
            )

        if product.stock < item_data.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for product {product.name}"
            )

        item_total = product.price * item_data.quantity
        total_price += item_total

        product.stock -= item_data.quantity

        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )

        db.add(order_item)

    order.total_price = total_price

    db.commit()
    db.refresh(order)

    return order


@router.get("", response_model=list[OrderResponse])
def get_orders(
    status: str | None = None,
    customer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    allowed_statuses = ["new", "paid", "shipped", "cancelled"]

    query = db.query(Order)

    if status is not None:
        if status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid order status"
            )

        query = query.filter(Order.status == status)

    if customer_id is not None:
        query = query.filter(Order.customer_id == customer_id)

    if date_from is not None:
        start_datetime = datetime.combine(date_from, time.min)
        query = query.filter(Order.created_at >= start_datetime)

    if date_to is not None:
        end_datetime = datetime.combine(date_to, time.max)
        query = query.filter(Order.created_at <= end_datetime)

    orders = query.all()

    return orders


@router.get("/by-status", response_model=list[OrderResponse])
def get_orders_by_status(
    status: str = Query(..., pattern="^(new|paid|shipped|cancelled)$"),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(Order.status == status).all()

    return orders


@router.get("/my", response_model=list[OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.user_id == current_user.id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )

    orders = db.query(Order).filter(
        Order.customer_id == customer.id
    ).all()

    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if current_user.role == "admin":
        return order

    customer = db.query(Customer).filter(
        Customer.user_id == current_user.id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )

    if order.customer_id != customer.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return order



@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status: str = Query(..., pattern="^(new|paid|shipped|cancelled)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed_transitions = {
        "new": ["paid", "cancelled"],
        "paid": ["shipped", "cancelled"],
        "shipped": [],
        "cancelled": []
    }

    if status == order.status:
        raise HTTPException(
            status_code=400,
            detail=f"Order already has status '{status}'"
        )

    if status not in allowed_transitions[order.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change order status from '{order.status}' to '{status}'"
        )

    if status == "cancelled":
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()

            if product is not None:
                product.stock += item.quantity

    order.status = status

    db.commit()
    db.refresh(order)

    return order


@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()

    return {"message": "Order deleted successfully"}