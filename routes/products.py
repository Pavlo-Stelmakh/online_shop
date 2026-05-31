from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from routes.auth import get_current_user
from models import Product, Category, User
from schemas import ProductCreate, ProductResponse, ProductCatalogResponse


router = APIRouter(
    prefix="/products",
    tags=["products"]
)


@router.post("", response_model=ProductResponse)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(Category.id == product_data.category_id).first()

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        name=product_data.name,
        price=product_data.price,
        description=product_data.description,
        stock=product_data.stock,
        category_id=product_data.category_id
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@router.get("", response_model=list[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return products


@router.get("/search", response_model=list[ProductResponse])
def search_products(
    query: str,
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(
        Product.name.ilike(f"%{query}%")
    ).all()

    return products


@router.get("/filter", response_model=list[ProductResponse])
def filter_products_by_price(
    min_price: float | None = None,
    max_price: float | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    products = query.all()

    return products


@router.get("/sort", response_model=list[ProductResponse])
def sort_products_by_price(
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if order == "desc":
        products = query.order_by(Product.price.desc()).all()
    else:
        products = query.order_by(Product.price.asc()).all()

    return products


@router.get("/limited", response_model=list[ProductResponse])
def get_limited_products(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    products = db.query(Product).limit(limit).all()

    return products


@router.get("/catalog", response_model=list[ProductResponse])
def get_catalog_products(
    search: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if search is not None:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if order == "desc":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.price.asc())

    products = query.limit(limit).all()

    return products


@router.get("/catalog/pages", response_model=ProductCatalogResponse)
def get_catalog_products_with_pages(
    search: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if search is not None:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    total = query.count()
    pages = (total + limit - 1) // limit

    if order == "desc":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.price.asc())

    offset = (page - 1) * limit

    products = query.offset(offset).limit(limit).all()

    return {
        "items": products,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    category = db.query(Category).filter(Category.id == product_data.category_id).first()

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    product.name = product_data.name
    product.price = product_data.price
    product.description = product_data.description
    product.stock = product_data.stock
    product.category_id = product_data.category_id

    db.commit()
    db.refresh(product)

    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {"message": "Product deleted successfully"}

