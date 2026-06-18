from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Order
from routes.admin.common import (
    get_admin_csrf_token,
    require_admin_csrf,
    require_admin_ui,
    templates,
)
from schemas import ORDER_STATUS_VALUES
from services.orders import get_available_order_status_actions, transition_order_status


ORDER_STATUSES = ORDER_STATUS_VALUES
router = APIRouter()


@router.get("/orders")
def admin_orders(
    request: Request,
    status: str | None = None,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    query = db.query(Order)

    error = None

    if status is not None:
        if status not in ORDER_STATUSES:
            error = "Invalid order status filter"
        else:
            query = query.filter(Order.status == status)

    orders = [] if error else query.order_by(Order.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_orders.html",
        context={
            "orders": orders,
            "status": status if error is None else None,
            "error": error
        },
        status_code=400 if error else 200
    )


@router.get("/orders/{order_id}")
def admin_order_detail(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return templates.TemplateResponse(
        request=request,
        name="admin_order_detail.html",
        context={
            "order": order,
            "status_actions": get_available_order_status_actions(order),
            "error": None,
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.post("/orders/{order_id}/status")
def admin_order_status_update(
    order_id: int,
    request: Request,
    status: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    if status not in ORDER_STATUSES:
        order = db.query(Order).filter(Order.id == order_id).first()

        if order is None:
            return RedirectResponse(
                url="/admin/orders",
                status_code=303
            )

        return templates.TemplateResponse(
            request=request,
            name="admin_order_detail.html",
            context={
                "order": order,
                "status_actions": get_available_order_status_actions(order),
                "error": "Invalid order status",
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    try:
        transition_order_status(
            db=db,
            order_id=order_id,
            status=status
        )
    except HTTPException as exc:
        order = db.query(Order).filter(Order.id == order_id).first()

        if order is None:
            return RedirectResponse(
                url="/admin/orders",
                status_code=303
            )

        return templates.TemplateResponse(
            request=request,
            name="admin_order_detail.html",
            context={
                "order": order,
                "status_actions": get_available_order_status_actions(order),
                "error": exc.detail,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=exc.status_code
        )

    return RedirectResponse(
        url=f"/admin/orders/{order_id}",
        status_code=303
    )
