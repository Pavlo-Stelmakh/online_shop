import hashlib
import os
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY, is_production_environment
from models import User
from utils.money import format_money


templates = Jinja2Templates(directory="templates")
templates.env.filters["money"] = format_money


def format_admin_datetime(value: datetime | None) -> str:
    if value is None:
        return ""

    return value.strftime("%Y-%m-%d %H:%M")


templates.env.filters["datetime"] = format_admin_datetime

ADMIN_SESSION_COOKIE_NAME = "admin_session"
ADMIN_SESSION_EXPIRE_SECONDS = int(
    os.getenv("ADMIN_SESSION_EXPIRE_SECONDS", "1800")
)
ADMIN_SESSION_TOKEN_TYPE = "admin_ui_session"
ADMIN_CSRF_TOKEN_TYPE = "admin_ui_csrf"


def is_admin_cookie_secure() -> bool:
    return is_production_environment()


def create_admin_session_token(user: User) -> str:
    expire = datetime.now(UTC) + timedelta(
        seconds=ADMIN_SESSION_EXPIRE_SECONDS
    )

    payload = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "typ": ADMIN_SESSION_TOKEN_TYPE,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def create_admin_csrf_token(admin_session_token: str) -> str:
    session_digest = hashlib.sha256(
        admin_session_token.encode("utf-8")
    ).hexdigest()

    payload = {
        "typ": ADMIN_CSRF_TOKEN_TYPE,
        "session_sha256": session_digest
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def validate_admin_csrf_token(
    admin_session_token: str,
    csrf_token: str | None
) -> bool:
    if not csrf_token:
        return False

    try:
        payload = jwt.decode(
            csrf_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        return False

    if payload.get("typ") != ADMIN_CSRF_TOKEN_TYPE:
        return False

    expected_digest = hashlib.sha256(
        admin_session_token.encode("utf-8")
    ).hexdigest()

    return payload.get("session_sha256") == expected_digest


def require_admin_csrf(request: Request, csrf_token: str | None):
    admin_session_token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)

    if not admin_session_token:
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    if not validate_admin_csrf_token(admin_session_token, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def get_admin_csrf_token(request: Request) -> str:
    admin_session_token = request.cookies[ADMIN_SESSION_COOKIE_NAME]

    return create_admin_csrf_token(admin_session_token)


def decode_admin_session_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        return None

    if payload.get("typ") != ADMIN_SESSION_TOKEN_TYPE:
        return None

    if payload.get("role") != "admin":
        return None

    username = payload.get("sub")
    user_id = payload.get("user_id")

    if username is None or user_id is None:
        return None

    return payload


def get_admin_from_cookie(
    request: Request,
    db: Session
):
    token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)

    if token is None:
        return None

    payload = decode_admin_session_token(token)

    if payload is None:
        return None

    user = db.query(User).filter(
        User.id == payload["user_id"],
        User.username == payload["sub"]
    ).first()

    if user is None:
        return None

    if user.role != "admin":
        return None

    return user


def require_admin_ui(
    request: Request,
    db: Session
):
    user = get_admin_from_cookie(request, db)

    if user is None:
        return RedirectResponse(
            url="/admin/login",
            status_code=303
        )

    return user
