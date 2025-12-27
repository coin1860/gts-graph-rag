"""CRUD operations for User entity."""


from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.jwt import get_password_hash, verify_password
from backend.models.db_models import Organization, User, UserRole


class UserCreate(BaseModel):
    """Schema for creating a user."""

    username: str
    password: str
    email: str | None = None
    role: UserRole = UserRole.USER
    organization_ids: list[int] = []


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    username: str | None = None
    email: str | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    organization_ids: list[int] | None = None


class UserResponse(BaseModel):
    """Response schema for user."""

    id: int
    username: str
    email: str | None
    role: UserRole
    is_active: bool
    organizations: list[dict]

    class Config:
        from_attributes = True


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user."""
    # Check if username already exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise ValueError(f"Username '{user_data.username}' already exists")

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
    )

    # Add organizations if specified
    if user_data.organization_ids:
        orgs = db.query(Organization).filter(
            Organization.id.in_(user_data.organization_ids)
        ).all()
        db_user.organizations = orgs

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> User | None:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """Get all users."""
    return db.query(User).offset(skip).limit(limit).all()


def update_user(
    db: Session,
    user_id: int,
    user_data: UserUpdate
) -> User | None:
    """Update a user."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_data.model_dump(exclude_unset=True)

    # Handle password separately
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))

    # Handle organizations separately
    if "organization_ids" in update_data:
        org_ids = update_data.pop("organization_ids")
        orgs = db.query(Organization).filter(
            Organization.id.in_(org_ids)
        ).all()
        db_user.organizations = orgs

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user."""
    db_user = get_user(db, user_id)
    if not db_user:
        return False

    db.delete(db_user)
    db.commit()
    return True


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Authenticate user by username and password."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user
