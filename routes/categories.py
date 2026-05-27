from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Category, Product
from schemas import CategoryCreate, CategoryResponse, ProductResponse


router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)

@router.post("", response_model=CategoryResponse)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db)
):
    existing_category = db.query(Category).filter(
        Category.name == category_data.name
    ).first()

    if existing_category is not None:
        raise HTTPException(
            status_code=400,
            detail="Category already exists"
        )

    category = Category(name=category_data.name)

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


@router.get("", response_model=list[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return categories

@router.get("/{category_id}/products", response_model=list[ProductResponse])
def get_products_by_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    products = db.query(Product).filter(Product.category_id == category_id).all()

    return products
