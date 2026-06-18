from fastapi import APIRouter

from routes.admin.auth import router as auth_router
from routes.admin.categories import router as categories_router
from routes.admin.common import (
    ADMIN_SESSION_COOKIE_NAME,
    ADMIN_SESSION_EXPIRE_SECONDS,
    ADMIN_SESSION_TOKEN_TYPE,
    create_admin_session_token,
    format_admin_datetime,
)
from routes.admin.customers import router as customers_router
from routes.admin.dashboard import admin_dashboard
from routes.admin.orders import router as orders_router
from routes.admin.products import router as products_router


router = APIRouter(
    prefix="/admin",
    tags=["admin dashboard"]
)

router.include_router(auth_router)
router.get("")(admin_dashboard)
router.include_router(products_router)
router.include_router(orders_router)
router.include_router(categories_router)
router.include_router(customers_router)
