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
            error="Category name is required",
            status_code=400
        )

    existing_category = db.query(Category).filter(
        Category.name == category_name
    ).first()

    if existing_category is not None:
        return render_admin_categories(
            request,
            db,
            error="Category already exists",
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
            error="Category already exists",
            status_code=400
        )

    return RedirectResponse(url="/admin/categories", status_code=303)


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
            error="Category not found",
            status_code=404
        )

    category_name = name.strip()

    if not category_name:
        return render_admin_categories(
            request,
            db,
            error="Category name is required",
            status_code=400
        )

    existing_category = db.query(Category).filter(
        Category.name == category_name,
        Category.id != category_id
    ).first()

    if existing_category is not None:
        return render_admin_categories(
            request,
            db,
            error="Category already exists",
            status_code=400
        )

    category.name = category_name

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_admin_categories(
            request,
            db,
            error="Category already exists",
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
            error="Category not found",
            status_code=404
        )

    products_count = db.query(Product).filter(
        Product.category_id == category_id
    ).count()

    if products_count > 0:
        return render_admin_categories(
            request,
            db,
            error="Cannot delete category with products",
            status_code=400
        )

    db.delete(category)
    db.commit()

    return RedirectResponse(url="/admin/categories", status_code=303)
