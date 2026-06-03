from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import Product, Category
from schemas import ProductCreate, ProductResponse, CategoryCreate, CategoryResponse, ProductCatalogResponse
from routes.categories import router as categories_router
from routes.products import router as products_router
from routes.customers import router as customers_router
from routes.orders import router as orders_router
from routes.stats import router as stats_router
from routes.auth import router as auth_router


Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(categories_router)
app.include_router(products_router)
app.include_router(customers_router)
app.include_router(orders_router)
app.include_router(stats_router)
app.include_router(auth_router)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "Online shop API with SQLite is working"}



