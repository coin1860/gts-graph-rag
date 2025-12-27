"""User admin routes - CRUD for users."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import AdminUser
from backend.crud.user import (
    UserCreate,
    UserUpdate,
    create_user,
    delete_user,
    get_user,
    get_users,
    update_user,
)
from backend.database import get_db

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


class UserResponse(BaseModel):
    """User response model."""

    id: int
    username: str
    email: str | None
    role: str
    is_active: bool
    organizations: list[dict]

    class Config:
        from_attributes = True


def user_to_response(user) -> UserResponse:
    """Convert User model to response."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        organizations=[
            {"id": org.id, "name": org.name}
            for org in user.organizations
        ]
    )


@router.post("", response_model=UserResponse)
async def create_new_user(
    user_data: UserCreate,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Create a new user."""
    try:
        user = create_user(db, user_data)
        return user_to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e



@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin: AdminUser = None,
    db: Session = Depends(get_db)
):
    """List all users."""
    users = get_users(db, skip=skip, limit=limit)
    return [user_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Get user by ID."""
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_id(
    user_id: int,
    user_data: UserUpdate,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Update user."""
    user = update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_response(user)


@router.delete("/{user_id}")
async def delete_user_by_id(
    user_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Delete user."""
    # Prevent self-deletion
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
