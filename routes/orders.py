from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Order, OrderItem, Customer, Product, User
from schemas import (
    ORDER_STATUS_TRANSITIONS,
    ORDER_STATUS_VALUES,
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderStatus,
)
from routes.auth import get_current_user, get_admin_user
from datetime import date, time, datetime
from decimal import Decimal

from utils.money import quantize_money


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

    product_ids = [item.product_id for item in order_data.items]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate product in order items"
        )

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
        total_price=Decimal("0.00")
    )

    db.add(order)
    db.flush()

    total_price = Decimal("0.00")

    products = db.query(Product).filter(
        Product.id.in_(product_ids)
    ).all()
    products_by_id = {product.id: product for product in products}

    for product_id in product_ids:
        if product_id not in products_by_id:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Product with id {product_id} not found"
            )

    items_by_product_id = {
        item_data.product_id: item_data
        for item_data in order_data.items
    }

    for product_id in sorted(product_ids):
        item_data = items_by_product_id[product_id]
        rows_updated = db.query(Product).filter(
            Product.id == product_id,
            Product.stock >= item_data.quantity,
        ).update(
            {Product.stock: Product.stock - item_data.quantity},
            synchronize_session=False,
        )

        if rows_updated == 0:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for product {products_by_id[product_id].name}"
            )

    for item_data in order_data.items:
        product = products_by_id[item_data.product_id]

        unit_price = quantize_money(product.price)
        item_total = quantize_money(unit_price * item_data.quantity)
        total_price = quantize_money(total_price + item_total)

        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
        )

        db.add(order_item)

    order.total_price = quantize_money(total_price)

    db.commit()
    db.refresh(order)

    return order


@router.get("", response_model=OrderListResponse)
def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: str | None = None,
    customer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    query = db.query(Order)

    if status is not None:
        if status not in ORDER_STATUS_VALUES:
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

    total = query.count()

    orders = query.order_by(Order.id.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": orders
    }



@router.get("/by-status", response_model=list[OrderResponse])
def get_orders_by_status(
    status: OrderStatus = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
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
    status: OrderStatus = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if status == order.status:
        raise HTTPException(
            status_code=400,
            detail=f"Order already has status '{status}'"
        )

    if status not in ORDER_STATUS_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change order status from '{order.status}' to '{status}'"
        )

    if status == "cancelled":
        rows_updated = db.query(Order).filter(
            Order.id == order_id,
            Order.status.in_(("new", "paid")),
        ).update(
            {Order.status: "cancelled"},
            synchronize_session=False,
        )

        if rows_updated == 1:
            items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

            for item in items:
                db.query(Product).filter(Product.id == item.product_id).update(
                    {Product.stock: Product.stock + item.quantity},
                    synchronize_session=False,
                )

            db.commit()

            cancelled_order = db.query(Order).filter(Order.id == order_id).first()

            if cancelled_order is None:
                raise HTTPException(status_code=404, detail="Order not found")

            return cancelled_order
    else:
        expected_current_status_by_target = {
            "paid": "new",
            "shipped": "paid",
        }
        expected_current_status = expected_current_status_by_target[status]

        rows_updated = db.query(Order).filter(
            Order.id == order_id,
            Order.status == expected_current_status,
        ).update(
            {Order.status: status},
            synchronize_session=False,
        )

        if rows_updated == 1:
            db.commit()

            updated_order = db.query(Order).filter(Order.id == order_id).first()

            if updated_order is None:
                raise HTTPException(status_code=404, detail="Order not found")

            return updated_order

    db.rollback()

    current_order = db.query(Order).filter(Order.id == order_id).first()

    if current_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_order.status == status:
        raise HTTPException(
            status_code=400,
            detail=f"Order already has status '{status}'"
        )

    raise HTTPException(
        status_code=400,
        detail=(
            f"Cannot change order status from '{current_order.status}' "
            f"to '{status}'"
        )
    )


@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    existing_item = db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).first()

    if existing_item is not None:
        raise HTTPException(
            status_code=409,
            detail="Order cannot be deleted because it has order items"
        )

    db.delete(order)
    db.commit()

    return {"message": "Order deleted successfully"}
