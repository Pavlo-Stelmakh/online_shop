from sqlalchemy import CheckConstraint, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from database import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("trim(name) <> ''", name="ck_categories_name_not_empty"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_products_low_stock_threshold_non_negative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    stock = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, default=5, nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category = relationship("Category", back_populates="products")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("trim(name) <> ''", name="ck_customers_name_not_empty"),
        CheckConstraint("trim(email) <> ''", name="ck_customers_email_not_empty"),
        CheckConstraint("trim(phone) <> ''", name="ck_customers_phone_not_empty"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            name="fk_customers_user_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)

    user = relationship("User")
    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "total_price >= 0",
            name="ck_orders_total_price_non_negative",
        ),
        CheckConstraint(
            "status IN ('new', 'paid', 'shipped', 'cancelled')",
            name="ck_orders_status_allowed",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(String, default="new", nullable=False)
    total_price = Column(Float, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_order_items_quantity_positive",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'customer')",
            name="ck_users_role_admin_customer",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="customer", nullable=False)
