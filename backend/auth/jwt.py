"""JWT token handling for authentication."""

from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token payload data."""

    user_id: int
    username: str
    role: str
    exp: datetime | None = None


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> TokenData | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id = payload.get("user_id")
        username = payload.get("username")
        role = payload.get("role")

        if user_id is None or username is None:
            return None

        return TokenData(
            user_id=user_id,
            username=username,
            role=role or "user",
            exp=payload.get("exp")
        )
    except JWTError:
        return None
