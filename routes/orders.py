from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Order, OrderItem, Customer, Product
from schemas import OrderCreate, OrderResponse


router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@router.post("", response_model=OrderResponse)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == order_data.customer_id
    ).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

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

        item_total = product.price * item_data.quantity
        total_price += item_total

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
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return orders


@router.get("/by-status", response_model=list[OrderResponse])
def get_orders_by_status(
    status: str = Query(..., pattern="^(new|paid|shipped|cancelled)$"),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(Order.status == status).all()

    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order

@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status: str = Query(..., pattern="^(new|paid|shipped|cancelled)$"),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status

    db.commit()
    db.refresh(order)

    return order


@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()

    return {"message": "Order deleted successfully"}