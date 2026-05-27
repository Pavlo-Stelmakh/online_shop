from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    price: float
    description: str
    category_id: int


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    category_id: int
    category: CategoryResponse

    class Config:
        from_attributes = True


class ProductCatalogResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    limit: int
    pages: int


class CustomerCreate(BaseModel):
    name: str
    email: str
    phone: str


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str

    class Config:
        from_attributes = True

from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate]


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductResponse

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: str
    total_price: float
    created_at: datetime
    items: list[OrderItemResponse]

    class Config:
        from_attributes = True