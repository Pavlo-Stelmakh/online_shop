import os

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal, get_db as database_get_db
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

ALLOWED_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

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


@app.get("/health/db")
def database_health_check(db: Session = Depends(database_get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": "unavailable"
            }
        )

    return {
        "status": "ok",
        "database": "ok"
    }


@app.get("/version")
def version():
    return {
        "app": "online_shop",
        "version": os.getenv("APP_VERSION", "unknown"),
        "commit": (
            os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("COMMIT_SHA")
            or "unknown"
        ),
        "environment": (
            os.getenv("APP_ENV")
            or os.getenv("ENVIRONMENT")
            or os.getenv("RENDER_ENVIRONMENT")
            or "unknown"
        )
    }

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

