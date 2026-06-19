from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Order
from routes.admin.common import (
    get_admin_csrf_token,
    require_admin_csrf,
    require_admin_ui,
    templates,
)


router = APIRouter()


def build_customer_form_values(
    name: str,
    email: str,
    phone: str
) -> dict[str, str]:
    return {
        "name": name,
        "email": email,
        "phone": phone
    }


@router.get("/customers")
def admin_customers(
    request: Request,
    search: str | None = None,
    db: Session = Depends(get_db)
):

    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    query = db.query(Customer)

    if search is not None:
        search_value = search.strip()

        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(
                (Customer.name.ilike(search_pattern)) |
                (Customer.email.ilike(search_pattern)) |
                (Customer.phone.ilike(search_pattern))
            )

    customers = query.order_by(Customer.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_customers.html",
        context={
            "customers": customers,
            "search": search or ""
        }
    )


def render_admin_customer_detail(
    request: Request,
    customer: Customer | None,
    error: str | None = None,
    status_code: int = 200,
    form_values: dict[str, str] | None = None
):
    return templates.TemplateResponse(
        request=request,
        name="admin_customer_detail.html",
        context={
            "customer": customer,
            "error": error,
            "form_values": form_values or {},
            "csrf_token": get_admin_csrf_token(request)
        },
        status_code=status_code
    )


@router.get("/customers/{customer_id}")
def admin_customer_detail(
    customer_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_customer_detail.html",
            context={
                "customer": None,
                "error": "Клієнта не знайдено",
                "form_values": {},
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    return render_admin_customer_detail(request, customer)


@router.post("/customers/{customer_id}/edit")
def admin_customer_edit(
    customer_id: int,
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_customer_detail.html",
            context={
                "customer": None,
                "error": "Клієнта не знайдено",
                "form_values": {},
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    form_values = build_customer_form_values(name, email, phone)

    name_value = name.strip()
    email_value = email.strip()
    phone_value = phone.strip()

    if not name_value or not email_value or not phone_value:
        return render_admin_customer_detail(
            request,
            customer,
            error="Ім’я, email і телефон є обов’язковими",
            status_code=400,
            form_values=form_values
        )

    existing_customer = db.query(Customer).filter(
        Customer.email == email_value,
        Customer.id != customer_id
    ).first()

    if existing_customer is not None:
        return render_admin_customer_detail(
            request,
            customer,
            error="Клієнт із цим email уже існує",
            status_code=400,
            form_values=form_values
        )

    customer.name = name_value
    customer.email = email_value
    customer.phone = phone_value

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_admin_customer_detail(
            request,
            customer,
            error="Не вдалося оновити клієнта",
            status_code=400,
            form_values=form_values
        )

    return RedirectResponse(
        url=f"/admin/customers/{customer.id}",
        status_code=303
    )


@router.post("/customers/{customer_id}/delete")
def admin_customer_delete(
    customer_id: int,
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_customer_detail.html",
            context={
                "customer": None,
                "error": "Клієнта не знайдено",
                "form_values": {},
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    existing_order = db.query(Order).filter(
        Order.customer_id == customer_id
    ).first()

    if existing_order is not None:
        return render_admin_customer_detail(
            request,
            customer,
            error="Неможливо видалити клієнта, оскільки він має замовлення",
            status_code=400
        )

    db.delete(customer)
    db.commit()

    return RedirectResponse(url="/admin/customers", status_code=303)
