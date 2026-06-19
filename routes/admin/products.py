from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Category, OrderItem, Product
from routes.admin.common import (
    get_admin_csrf_token,
    require_admin_csrf,
    require_admin_ui,
    templates,
)
from utils.money import MoneyValidationError, parse_positive_money


router = APIRouter()


def translate_admin_money_error(message: str) -> str:
    translations = {
        "price is required": "Ціна є обов’язковою",
        "price must be a valid decimal amount": "Ціна має бути коректним десятковим числом",
        "price must be a finite decimal amount": "Ціна має бути скінченним десятковим числом",
        "price must be greater than or equal to 0": "Ціна має бути більшою або дорівнювати 0",
        "price must not have more than 2 decimal places": "Ціна не може мати більше ніж 2 десяткові знаки",
        "price must be greater than 0": "Ціна має бути більшою за 0",
    }

    return translations.get(message, message)


def build_product_form_values(
    name: str,
    price: str,
    description: str,
    image_url: str | None,
    stock: int,
    low_stock_threshold: int,
    category_id: int
) -> dict[str, str | int]:
    return {
        "name": name,
        "price": price,
        "description": description,
        "image_url": image_url or "",
        "stock": stock,
        "low_stock_threshold": low_stock_threshold,
        "category_id": category_id
    }



def validate_admin_product_image_url(image_url: str | None) -> str | None:
    if image_url is None:
        return None

    cleaned_image_url = image_url.strip()

    if not cleaned_image_url:
        return None

    if not (
        cleaned_image_url.startswith("http://")
        or cleaned_image_url.startswith("https://")
    ):
        return "URL зображення має починатися з http:// або https://"

    return None


@router.get("/products")
def admin_products(
    request: Request,
    search: str | None = None,
    in_stock: bool | None = None,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    query = db.query(Product)

    if search is not None:
        search_value = search.strip()

        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(
                (Product.name.ilike(search_pattern)) |
                (Product.description.ilike(search_pattern))
            )

    if in_stock is not None:
        if in_stock:
            query = query.filter(Product.stock > 0)
        else:
            query = query.filter(Product.stock == 0)

    products = query.order_by(Product.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_products.html",
        context={
            "products": products,
            "search": search or "",
            "in_stock": in_stock,
            "error": None,
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.get("/products/create")
def admin_product_create_legacy_page(
    request: Request,
    db: Session = Depends(get_db)
):
    return admin_product_new_page(request=request, db=db)


@router.get("/products/new")
def admin_product_new_page(
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    return templates.TemplateResponse(
        request=request,
        name="admin_product_create.html",
        context={
            "error": None,
            "form_values": {},
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.post("/products/create")
def admin_product_create_legacy(
    request: Request,
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form(...),
    image_url: str | None = Form(None),
    stock: int = Form(...),
    low_stock_threshold: int = Form(...),
    category_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    return admin_product_create(
        request=request,
        name=name,
        price=price,
        description=description,
        image_url=(image_url.strip() or None) if image_url else None,
        stock=stock,
        low_stock_threshold=low_stock_threshold,
        category_id=category_id,
        csrf_token=csrf_token,
        db=db
    )


@router.post("/products/new")
def admin_product_create(
    request: Request,
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form(...),
    image_url: str | None = Form(None),
    stock: int = Form(...),
    low_stock_threshold: int = Form(...),
    category_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    form_values = build_product_form_values(
        name,
        price,
        description,
        image_url,
        stock,
        low_stock_threshold,
        category_id
    )

    image_url_error = validate_admin_product_image_url(image_url)

    if image_url_error:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": image_url_error,
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if not name.strip():
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "Назва товару не може бути порожньою",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if not description.strip():
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "Опис товару не може бути порожнім",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    try:
        price_amount = parse_positive_money(price)
    except MoneyValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": translate_admin_money_error(str(exc)),
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if stock < 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "Залишок має бути більшим або дорівнювати 0",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if low_stock_threshold < 1 or low_stock_threshold > 100:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "Поріг низького залишку має бути від 1 до 100",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_create.html",
            context={
                "error": "Категорію не знайдено",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    product = Product(
        name=name,
        price=price_amount,
        description=description,
        image_url=(image_url.strip() or None) if image_url else None,
        stock=stock,
        low_stock_threshold=low_stock_threshold,
        category_id=category_id
    )

    db.add(product)
    db.commit()

    return RedirectResponse(
        url="/admin/products",
        status_code=303
    )


@router.get("/products/{product_id}/edit")
def admin_product_edit_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        return RedirectResponse(
            url="/admin/products",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_product_edit.html",
        context={
            "product": product,
            "error": None,
            "form_values": {},
            "csrf_token": get_admin_csrf_token(request)
        }
    )


@router.post("/products/{product_id}/edit")
def admin_product_edit(
    product_id: int,
    request: Request,
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form(...),
    image_url: str | None = Form(None),
    stock: int = Form(...),
    low_stock_threshold: int = Form(...),
    category_id: int = Form(...),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        return RedirectResponse(
            url="/admin/products",
            status_code=303
        )

    form_values = build_product_form_values(
        name,
        price,
        description,
        image_url,
        stock,
        low_stock_threshold,
        category_id
    )

    image_url_error = validate_admin_product_image_url(image_url)

    if image_url_error:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": image_url_error,
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if not name.strip():
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "Назва товару не може бути порожньою",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if not description.strip():
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "Опис товару не може бути порожнім",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    try:
        price_amount = parse_positive_money(price)
    except MoneyValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": translate_admin_money_error(str(exc)),
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if stock < 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "Залишок має бути більшим або дорівнювати 0",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    if low_stock_threshold < 1 or low_stock_threshold > 100:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "Поріг низького залишку має бути від 1 до 100",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_product_edit.html",
            context={
                "product": product,
                "error": "Категорію не знайдено",
                "form_values": form_values,
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=404
        )

    product.name = name
    product.price = price_amount
    product.description = description
    product.image_url = (image_url.strip() or None) if image_url else None
    product.stock = stock
    product.low_stock_threshold = low_stock_threshold
    product.category_id = category_id

    db.commit()

    return RedirectResponse(
        url="/admin/products",
        status_code=303
    )


@router.post("/products/{product_id}/delete")
def admin_product_delete(
    product_id: int,
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    require_admin_csrf(request, csrf_token)

    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        return RedirectResponse(
            url="/admin/products",
            status_code=303
        )

    related_order_items_count = db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).count()

    if related_order_items_count > 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_products.html",
            context={
                "products": db.query(Product).order_by(Product.id.desc()).all(),
                "search": "",
                "in_stock": None,
                "error": "Неможливо видалити товар, оскільки він використовується в наявних замовленнях.",
                "csrf_token": get_admin_csrf_token(request)
            },
            status_code=400
        )

    db.delete(product)
    db.commit()

    return RedirectResponse(
        url="/admin/products",
        status_code=303
    )




@router.get("/low-stock")
def admin_low_stock(
    request: Request,
    db: Session = Depends(get_db)
):
    admin_user = require_admin_ui(request, db)

    if isinstance(admin_user, RedirectResponse):
        return admin_user

    products = db.query(Product).filter(
        Product.stock <= Product.low_stock_threshold
    ).order_by(Product.stock.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_low_stock.html",
        context={
            "products": products
        }
    )
