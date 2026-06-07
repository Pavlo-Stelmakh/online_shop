from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    description: str
    image_url: str | None = None
    stock: int = Field(..., ge=0)
    category_id: int


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    image_url: str | None = None
    stock: int
    category_id: int
    category: CategoryResponse

    model_config = ConfigDict(from_attributes=True)

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
    user_id: int
    name: str
    email: str
    phone: str

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: str
    total_price: float
    created_at: datetime
    items: list[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[OrderResponse]

    model_config = ConfigDict(from_attributes=True)


class StatsSummaryResponse(BaseModel):
    products_count: int
    customers_count: int
    orders_count: int
    total_revenue: float

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ProductCatalogResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[ProductResponse]

