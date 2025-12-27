"""CRUD package - Database operations for entities."""

from backend.crud.document import (
    create_document,
    delete_document,
    get_document,
    get_documents,
    update_document,
)
from backend.crud.organization import (
    create_organization,
    delete_organization,
    get_organization,
    get_organizations,
    update_organization,
)
from backend.crud.user import (
    authenticate_user,
    create_user,
    delete_user,
    get_user,
    get_user_by_username,
    get_users,
    update_user,
)

__all__ = [
    # Organization
    "create_organization",
    "get_organization",
    "get_organizations",
    "update_organization",
    "delete_organization",
    # User
    "create_user",
    "get_user",
    "get_user_by_username",
    "get_users",
    "update_user",
    "delete_user",
    "authenticate_user",
    # Document
    "create_document",
    "get_document",
    "get_documents",
    "update_document",
    "delete_document",
]
