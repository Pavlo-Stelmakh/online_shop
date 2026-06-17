from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Category, Customer, Order, OrderItem, Product, User
from scripts import seed_demo_data


def make_session(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'seed_demo_data.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine), database_url


def test_seed_script_does_not_run_without_demo_mode_or_force(monkeypatch, capsys):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///unused.db")

    exit_code = seed_demo_data.main([])

    assert exit_code == 1
    assert "Refusing to run demo seed" in capsys.readouterr().err


def test_seed_preserves_admin_removes_test_data_and_creates_demo_products(tmp_path):
    SessionLocal, _ = make_session(tmp_path)
    session = SessionLocal()
    try:
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password="hash",
            role="admin",
        )
        test_user = User(
            username="customer",
            email="customer@example.com",
            hashed_password="hash",
            role="customer",
        )
        test_category = Category(name="Swagger Test Category")
        keep_category = Category(name="Real Category")
        session.add_all([admin, test_user, test_category, keep_category])
        session.flush()
        test_product = Product(
            name="Swagger Test Product",
            price=10,
            description="Render validation test product",
            stock=3,
            category_id=test_category.id,
        )
        keep_product = Product(
            name="Real Product",
            price=42,
            description="A real catalog product",
            stock=8,
            category_id=keep_category.id,
        )
        test_customer = Customer(
            user_id=test_user.id,
            name="Customer Validation Test",
            email="customer.validation.test@example.com",
            phone="+15555550123",
        )
        session.add_all([test_product, keep_product, test_customer])
        session.flush()
        order = Order(customer_id=test_customer.id, status="new", total_price=10)
        session.add(order)
        session.flush()
        session.add(OrderItem(order_id=order.id, product_id=test_product.id, quantity=1, unit_price=10))
        session.commit()

        stats = seed_demo_data.reset_demo_data(session)

        assert stats["products_created"] == 10
        assert session.query(User).filter(User.username == "admin", User.role == "admin").count() == 1
        assert session.query(Product).filter(Product.name == "Swagger Test Product").count() == 0
        assert session.query(Customer).filter(Customer.name == "Customer Validation Test").count() == 0
        assert session.query(Order).count() == 0
        assert session.query(OrderItem).count() == 0
        assert session.query(Product).filter(Product.name == "Real Product").count() == 1
        assert session.query(Product).filter(Product.name.in_([p["name"] for p in seed_demo_data.DEMO_PRODUCTS])).count() == 10
        assert session.query(Category).filter(Category.name.in_(seed_demo_data.DEMO_CATEGORY_NAMES)).count() == 4
    finally:
        session.close()
