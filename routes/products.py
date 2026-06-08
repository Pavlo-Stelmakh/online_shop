from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from routes.auth import get_admin_user
from models import Product, Category, User
from schemas import ProductCreate, ProductResponse, ProductCatalogResponse


router = APIRouter(
    prefix="/products",
    tags=["products"]
)


def apply_product_filters(
    query,
    category_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock: bool | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc"
):
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=400,
            detail="min_price cannot be greater than max_price"
        )

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if in_stock is True:
        query = query.filter(Product.stock > 0)

    allowed_sort_fields = {
        "id": Product.id,
        "name": Product.name,
        "price": Product.price,
        "stock": Product.stock
    }

    if sort_by is not None:
        if sort_by not in allowed_sort_fields:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_by value"
            )

        sort_column = allowed_sort_fields[sort_by]

        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        elif sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_order value"
            )

    return query


@router.post("", response_model=ProductResponse)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    category = db.query(Category).filter(Category.id == product_data.category_id).first()

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        name=product_data.name,
        price=product_data.price,
        description=product_data.description,
        image_url=product_data.image_url,
        stock=product_data.stock,
        category_id=product_data.category_id
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product

@router.get("", response_model=list[ProductResponse])
def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: int | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    in_stock: bool | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    query = apply_product_filters(
        query=query,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort_by=sort_by,
        sort_order=sort_order
    )

    products = query.offset(skip).limit(limit).all()

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


@router.get("/catalog", response_model=ProductCatalogResponse)
def get_products_catalog(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: int | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    in_stock: bool | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    query = apply_product_filters(
        query=query,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort_by=sort_by,
        sort_order=sort_order
    )


    if search is not None:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_pattern)) |
            (Product.description.ilike(search_pattern))
        )

    total = query.count()

    products = query.offset(skip).limit(limit).all()


    total = query.count()

    products = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": products
    }


@router.get("/low-stock", response_model=list[ProductResponse])
def get_low_stock_products(
    threshold: int = Query(5, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    products = db.query(Product).filter(
        Product.stock <= threshold
    ).all()

    return products


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
    current_user: User = Depends(get_admin_user)
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
    product.image_url = product_data.image_url
    product.stock = product_data.stock
    product.category_id = product_data.category_id

    db.commit()
    db.refresh(product)

    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {"message": "Product deleted successfully"}

