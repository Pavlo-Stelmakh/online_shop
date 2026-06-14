from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Product, Category
from schemas import ProductCreate, ProductResponse, CategoryCreate, CategoryResponse
from routes.categories import router as categories_router
from routes.products import router as products_router
from routes.customers import router as customers_router
from routes.orders import router as orders_router
from routes.stats import router as stats_router
from routes.auth import router as auth_router
from routes import admin


app = FastAPI()

@app.get("/")
def root():
    return {
        "message": "Online Shop API is running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(categories_router)
app.include_router(products_router)
app.include_router(customers_router)
app.include_router(orders_router)
app.include_router(stats_router)
app.include_router(auth_router)
app.include_router(admin.router)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "Online shop API with SQLite is working"}



