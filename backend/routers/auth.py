"""Authentication routes - Login and token management."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_active_user
from backend.auth.jwt import Token, create_access_token
from backend.crud.user import authenticate_user
from backend.database import get_db
from backend.models.db_models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class UserInfo(BaseModel):
    """User info response."""

    id: int
    username: str
    email: str | None
    role: str
    organizations: list[dict]

    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    user = authenticate_user(db, request.username, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
        }
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user info."""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value,
        organizations=[
            {"id": org.id, "name": org.name}
            for org in current_user.organizations
        ]
    )


@router.post("/logout")
async def logout():
    """Logout (client-side token removal)."""
    # JWT tokens are stateless, so logout is handled client-side
    return {"message": "Logged out successfully"}
