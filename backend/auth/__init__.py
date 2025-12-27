"""Auth package - JWT authentication and role-based access control."""

from backend.auth.dependencies import (
    get_current_active_user,
    get_current_user,
    require_admin,
)
from backend.auth.jwt import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

__all__ = [
    "create_access_token",
    "verify_password",
    "get_password_hash",
    "decode_access_token",
    "get_current_user",
    "get_current_active_user",
    "require_admin",
]
