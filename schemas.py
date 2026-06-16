from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from utils.money import MoneyValidationError, format_money, parse_positive_money


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def trim_non_blank_string(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Value must be a string")

    trimmed_value = value.strip()

    if not trimmed_value:
        raise ValueError("Value cannot be blank")

    return trimmed_value


def validate_email_string(value: str) -> str:
    trimmed_value = trim_non_blank_string(value)

    if not _EMAIL_RE.fullmatch(trimmed_value):
        raise ValueError("Value must be a valid email address")

    return trimmed_value


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return trim_non_blank_string(value)


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
    price_amount: str = Field(
        default="",
        description="Exact price amount as a decimal string with two places.",
    )
    description: str
    image_url: str | None = None
    stock: int
    low_stock_threshold: int
    category_id: int
    category: CategoryResponse

    @model_validator(mode="after")
    def set_price_amount(self):
        self.price_amount = format_money(self.price)
        return self

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
    email: str = Field(..., json_schema_extra={"format": "email"})
    phone: str

    @field_validator("name", "phone")
    @classmethod
    def validate_required_strings(cls, value):
        return trim_non_blank_string(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return validate_email_string(value)

class CustomerResponse(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    phone: str

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime

class OrderItemCreate(BaseModel):
    product_id: int = Field(ge=1)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int = Field(ge=1)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    unit_price_amount: str = Field(
        default="",
        description="Exact unit price amount as a decimal string with two places.",
    )
    product: ProductResponse

    @model_validator(mode="after")
    def set_unit_price_amount(self):
        self.unit_price_amount = format_money(self.unit_price)
        return self

    model_config = ConfigDict(from_attributes=True)

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: str
    total_price: float
    total_price_amount: str = Field(
        default="",
        description="Exact total price amount as a decimal string with two places.",
    )
    created_at: datetime
    items: list[OrderItemResponse]

    @model_validator(mode="after")
    def set_total_price_amount(self):
        self.total_price_amount = format_money(self.total_price)
        return self

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
    total_revenue_amount: str = Field(
        default="",
        description="Exact total revenue amount as a decimal string with two places.",
    )

    @model_validator(mode="after")
    def set_total_revenue_amount(self):
        self.total_revenue_amount = format_money(self.total_revenue)
        return self

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1)
    email: str = Field(..., json_schema_extra={"format": "email"})
    password: str = Field(..., min_length=6)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        return trim_non_blank_string(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return validate_email_string(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return trim_non_blank_string(value)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
