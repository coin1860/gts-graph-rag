"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.jwt import decode_access_token
from backend.database import get_db
from backend.models.db_models import User, UserRole

# HTTP Bearer token scheme - set auto_error=False to allow fallback to query param
security = HTTPBearer(auto_error=False)


async def get_current_user(
    token: str = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token (checks header first, then query param)."""
    used_token = None
    if credentials and credentials.credentials:
        used_token = credentials.credentials
    elif token:
        used_token = token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not used_token:
        raise credentials_exception

    token_data = decode_access_token(used_token)

    if token_data is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Require admin role for access."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
