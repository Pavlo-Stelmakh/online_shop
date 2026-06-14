from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from utils.money import MoneyValidationError, parse_positive_money


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)


class CategoryResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: Decimal

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, value):
        try:
            return parse_positive_money(value)
        except MoneyValidationError as exc:
            raise ValueError(str(exc)) from exc
    description: str
    image_url: str | None = None
    stock: int = Field(..., ge=0)
    low_stock_threshold: int = Field(5, ge=1, le=100)
    category_id: int


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    image_url: str | None = None
    stock: int
    low_stock_threshold: int
    category_id: int
    category: CategoryResponse

    model_config = ConfigDict(from_attributes=True)

class ProductCatalogPageResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    limit: int
    pages: int


class ProductCatalogOffsetResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[ProductResponse]


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
    unit_price: float
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
