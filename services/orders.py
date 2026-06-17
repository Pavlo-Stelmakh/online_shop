from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Order, OrderItem, Product
from schemas import ORDER_STATUS_TRANSITIONS, OrderStatus


_NON_CANCEL_EXPECTED_CURRENT_STATUS: dict[str, str] = {
    "paid": "new",
    "shipped": "paid",
}


def validate_order_transition(order: Order, status: OrderStatus) -> None:
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


def get_available_order_status_actions(order: Order) -> tuple[dict[str, str], ...]:
    action_labels = {
        "paid": "Mark as paid",
        "shipped": "Mark as shipped",
        "cancelled": "Cancel order",
    }

    return tuple(
        {"status": status, "label": action_labels[status]}
        for status in ORDER_STATUS_TRANSITIONS[order.status]
    )


def _raise_failed_transition_error(db: Session, order_id: int, status: OrderStatus) -> None:
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


def _read_order_or_404(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


def cancel_order_with_stock_restore(db: Session, order_id: int) -> Order:
    rows_updated = db.query(Order).filter(
        Order.id == order_id,
        Order.status.in_(("new", "paid")),
    ).update(
        {Order.status: "cancelled"},
        synchronize_session=False,
    )

    if rows_updated != 1:
        _raise_failed_transition_error(db, order_id, "cancelled")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    for item in items:
        db.query(Product).filter(Product.id == item.product_id).update(
            {Product.stock: Product.stock + item.quantity},
            synchronize_session=False,
        )

    db.commit()

    return _read_order_or_404(db, order_id)


def _apply_non_cancel_status_transition(
    db: Session,
    order_id: int,
    status: OrderStatus,
) -> Order:
    expected_current_status = _NON_CANCEL_EXPECTED_CURRENT_STATUS[status]

    rows_updated = db.query(Order).filter(
        Order.id == order_id,
        Order.status == expected_current_status,
    ).update(
        {Order.status: status},
        synchronize_session=False,
    )

    if rows_updated != 1:
        _raise_failed_transition_error(db, order_id, status)

    db.commit()

    return _read_order_or_404(db, order_id)


def transition_order_status(
    db: Session,
    order_id: int,
    status: OrderStatus,
) -> Order:
    order = _read_order_or_404(db, order_id)

    validate_order_transition(order, status)

    if status == "cancelled":
        return cancel_order_with_stock_restore(db, order_id)

    return _apply_non_cancel_status_transition(db, order_id, status)
