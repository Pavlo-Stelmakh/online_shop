from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Order, OrderItem, Customer, Product, User
from schemas import OrderCreate, OrderResponse, OrderListResponse
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

    if not order_data.items:
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one item"
        )

    product_ids = [item.product_id for item in order_data.items]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate product in order items"
        )

    for item_data in order_data.items:
        if item_data.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid quantity"
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
    status: str = Query(..., pattern="^(new|paid|shipped|cancelled)$"),
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
