from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Category, Product
from routes.admin.common import (
    get_admin_csrf_token,
    require_admin_csrf,
    require_admin_ui,
    templates,
)


router = APIRouter()

CATEGORY_DELETE_IN_USE_ERROR = (
    "Неможливо видалити категорію, оскільки вона використовується наявними товарами."
)


def build_admin_categories_context(
    request: Request,
    db: Session,
    search: str | None = None,
    error: str | None = None
):
    query = db.query(Category)

    if search is not None:
        search_value = search.strip()

        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(Category.name.ilike(search_pattern))

    categories = query.order_by(Category.id.desc()).all()

    categories_with_counts = []

    for category in categories:
        products_count = db.query(Product).filter(
            Product.category_id == category.id
        ).count()

        categories_with_counts.append(
            {
                "category": category,
                "products_count": products_count
            }
        )

    return {
        "categories": categories_with_counts,
        "search": search or "",
        "error": error,
        "csrf_token": get_admin_csrf_token(request)
    }


def render_admin_categories(
    request: Request,
    db: Session,
    search: str | None = None,
    error: str | None = None,
    status_code: int = 200
):
    return templates.TemplateResponse(
        request=request,
        name="admin_categories.html",
        context=build_admin_categories_context(request, db, search, error),
        status_code=status_code
    )



def category_has_description() -> bool:
    return hasattr(Category, "description")


def build_category_form_context(
    request: Request,
    action_url: str,
    title: str,
    subtitle: str,
    submit_label: str,
    form_values: dict[str, str] | None = None,
    error: str | None = None
):
    return {
        "action_url": action_url,
        "title": title,
        "subtitle": subtitle,
        "submit_label": submit_label,
        "form_values": form_values or {},
        "has_description": category_has_description(),
        "error": error,
        "csrf_token": get_admin_csrf_token(request)
    }


def render_category_form(
    request: Request,
    action_url: str,
    title: str,
    subtitle: str,
    submit_label: str,
    form_values: dict[str, str] | None = None,
    error: str | None = None,
    status_code: int = 200
):
    return templates.TemplateResponse(
        request=request,
        name="admin_category_form.html",
        context=build_category_form_context(
            request,
            action_url,
            title,
            subtitle,
            submit_label,
            form_values,
            error
        ),
        status_code=status_code
    )


def category_form_values(
    category: Category | None = None,
    name: str | None = None
) -> dict[str, str]:
    values = {
        "name": name if name is not None else (category.name if category else "")
    }

    if category_has_description():
        values["description"] = getattr(category, "description", "") or ""

    return values


def validate_category_name(
    db: Session,
    name: str,
    category_id: int | None = None
) -> str | None:
    category_name = name.strip()

    if not category_name:
        return "Назва категорії не може бути порожньою"

    query = db.query(Category).filter(Category.name == category_name)

    if category_id is not None:
        query = query.filter(Category.id != category_id)

    if query.first() is not None:
        return "Категорія вже існує"

    return None


@router.get("/categories")
def admin_categories(
    request: Request,
    search: str | None = None,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    return render_admin_categories(request, db, search)


@router.get("/categories/new")
def admin_category_new_page(
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    return render_category_form(
        request,
        action_url="/admin/categories/new",
        title="Додати категорію",
        subtitle="Створіть нову категорію товарів з адмін-панелі.",
        submit_label="Додати категорію",
        form_values=category_form_values()
    )


@router.post("/categories/new")
def admin_category_new(
    request: Request,
    name: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    category_name = name.strip()
    validation_error = validate_category_name(db, name)

    if validation_error:
        return render_category_form(
            request,
            action_url="/admin/categories/new",
            title="Додати категорію",
            subtitle="Створіть нову категорію товарів з адмін-панелі.",
            submit_label="Додати категорію",
            form_values=category_form_values(name=name),
            error=validation_error,
            status_code=400
        )

    category = Category(name=category_name)
    db.add(category)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_category_form(
            request,
            action_url="/admin/categories/new",
            title="Додати категорію",
            subtitle="Створіть нову категорію товарів з адмін-панелі.",
            submit_label="Додати категорію",
            form_values=category_form_values(name=name),
            error="Категорія вже існує",
            status_code=400
        )

    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/categories/create")
def admin_category_create(
    request: Request,
    name: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    category_name = name.strip()

    if not category_name:
        return render_admin_categories(
            request,
            db,
            error="Назва категорії не може бути порожньою",
            status_code=400
        )

    existing_category = db.query(Category).filter(
        Category.name == category_name
    ).first()

    if existing_category is not None:
        return render_admin_categories(
            request,
            db,
            error="Категорія вже існує",
            status_code=400
        )

    category = Category(name=category_name)
    db.add(category)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_admin_categories(
            request,
            db,
            error="Категорія вже існує",
            status_code=400
        )

    return RedirectResponse(url="/admin/categories", status_code=303)


@router.get("/categories/{category_id}/edit")
def admin_category_edit_page(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return render_admin_categories(
            request,
            db,
            error="Категорію не знайдено",
            status_code=404
        )

    return render_category_form(
        request,
        action_url=f"/admin/categories/{category_id}/edit",
        title="Редагувати категорію",
        subtitle="Оновіть цю категорію товарів з адмін-панелі.",
        submit_label="Зберегти категорію",
        form_values=category_form_values(category=category)
    )


@router.post("/categories/{category_id}/edit")
def admin_category_edit(
    category_id: int,
    request: Request,
    name: str = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return render_admin_categories(
            request,
            db,
            error="Категорію не знайдено",
            status_code=404
        )

    category_name = name.strip()

    validation_error = validate_category_name(db, name, category_id=category_id)

    if validation_error:
        return render_category_form(
            request,
            action_url=f"/admin/categories/{category_id}/edit",
            title="Редагувати категорію",
            subtitle="Оновіть цю категорію товарів з адмін-панелі.",
            submit_label="Зберегти категорію",
            form_values=category_form_values(category=category, name=name),
            error=validation_error,
            status_code=400
        )

    category.name = category_name

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_category_form(
            request,
            action_url=f"/admin/categories/{category_id}/edit",
            title="Редагувати категорію",
            subtitle="Оновіть цю категорію товарів з адмін-панелі.",
            submit_label="Зберегти категорію",
            form_values=category_form_values(category=category, name=name),
            error="Категорія вже існує",
            status_code=400
        )

    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
def admin_category_delete(
    category_id: int,
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return render_admin_categories(
            request,
            db,
            error="Категорію не знайдено",
            status_code=404
        )

    products_count = db.query(Product).filter(
        Product.category_id == category_id
    ).count()

    if products_count > 0:
        return render_admin_categories(
            request,
            db,
            error=CATEGORY_DELETE_IN_USE_ERROR,
            status_code=400
        )

    db.delete(category)
    db.commit()

    return RedirectResponse(url="/admin/categories", status_code=303)
