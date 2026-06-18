from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth import verify_password
from database import get_db
from models import User
from routes.admin.common import (
    ADMIN_SESSION_COOKIE_NAME,
    ADMIN_SESSION_EXPIRE_SECONDS,
    create_admin_session_token,
    is_admin_cookie_secure,
    templates,
)


router = APIRouter()


@router.get("/login")
def admin_login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={
            "error": None,
            "form_values": {}
        }
    )


@router.post("/login")
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if user is None or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={
                "error": "Invalid username or password",
                "form_values": {"username": username}
            },
            status_code=401
        )

    if user.role != "admin":
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={
                "error": "Admin access required",
                "form_values": {"username": username}
            },
            status_code=403
        )

    response = RedirectResponse(
        url="/admin",
        status_code=303
    )

    response.set_cookie(
        key=ADMIN_SESSION_COOKIE_NAME,
        value=create_admin_session_token(user),
        httponly=True,
        samesite="lax",
        secure=is_admin_cookie_secure(),
        max_age=ADMIN_SESSION_EXPIRE_SECONDS
    )

    return response


@router.get("/logout")
def admin_logout():
    response = RedirectResponse(
        url="/admin/login",
        status_code=303
    )

    response.delete_cookie(ADMIN_SESSION_COOKIE_NAME)
    response.delete_cookie("admin_username")

    return response
