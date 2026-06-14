import os
from datetime import datetime, timedelta, UTC

from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext

load_dotenv()


DEFAULT_SECRET_KEY = "fallback_secret_key"
PRODUCTION_SECRET_KEY_ERROR = (
    "SECRET_KEY must be set to a strong non-default value in production"
)


def is_production_environment(environ=None) -> bool:
    environ = environ or os.environ
    environment = environ.get("ENVIRONMENT", environ.get("ENV", "")).lower()

    return environment in {"production", "prod"} or environ.get("RENDER") == "true"


def get_secret_key(environ=None) -> str:
    environ = environ or os.environ
    secret_key = environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)

    if is_production_environment(environ) and secret_key == DEFAULT_SECRET_KEY:
        raise RuntimeError(PRODUCTION_SECRET_KEY_ERROR)

    return secret_key


SECRET_KEY = get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(UTC) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if username is None:
            return None

        return username

    except JWTError:
        return None
