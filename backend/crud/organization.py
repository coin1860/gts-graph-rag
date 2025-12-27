"""CRUD operations for Organization entity."""


from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models.db_models import Organization
from backend.schema.boi_schema import validate_schema


class OrganizationCreate(BaseModel):
    """Schema for creating an organization."""

    name: str
    description: str | None = None
    graphrag_enabled: bool = False
    graph_schema: dict | None = None


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: str | None = None
    description: str | None = None
    graphrag_enabled: bool | None = None
    graph_schema: dict | None = None


class OrganizationResponse(BaseModel):
    """Response schema for organization."""

    id: int
    name: str
    description: str | None
    graphrag_enabled: bool
    graph_schema: dict | None

    class Config:
        from_attributes = True


def create_organization(db: Session, org_data: OrganizationCreate) -> Organization:
    """Create a new organization."""
    # Validate custom schema if provided
    if org_data.graph_schema and org_data.graphrag_enabled:
        is_valid, error = validate_schema(org_data.graph_schema)
        if not is_valid:
            raise ValueError(f"Invalid graph schema: {error}")

    db_org = Organization(
        name=org_data.name,
        description=org_data.description,
        graphrag_enabled=org_data.graphrag_enabled,
        graph_schema=org_data.graph_schema,
    )
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org


def get_organization(db: Session, org_id: int) -> Organization | None:
    """Get organization by ID."""
    return db.query(Organization).filter(Organization.id == org_id).first()


def get_organization_by_name(db: Session, name: str) -> Organization | None:
    """Get organization by name."""
    return db.query(Organization).filter(Organization.name == name).first()


def get_organizations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = None
) -> list[Organization]:
    """Get all organizations.
    If user_id is provided, only return organizations the user belongs to.
    """
    query = db.query(Organization)

    if user_id is not None:
        # Filter by user's organizations
        from backend.models.db_models import User
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.organizations:
            org_ids = [org.id for org in user.organizations]
            query = query.filter(Organization.id.in_(org_ids))

    return query.offset(skip).limit(limit).all()


def update_organization(
    db: Session,
    org_id: int,
    org_data: OrganizationUpdate
) -> Organization | None:
    """Update an organization."""
    db_org = get_organization(db, org_id)
    if not db_org:
        return None

    update_data = org_data.model_dump(exclude_unset=True)

    # Validate schema if updating
    if "graph_schema" in update_data and update_data["graph_schema"]:
        graphrag_enabled = update_data.get("graphrag_enabled", db_org.graphrag_enabled)
        if graphrag_enabled:
            is_valid, error = validate_schema(update_data["graph_schema"])
            if not is_valid:
                raise ValueError(f"Invalid graph schema: {error}")

    for field, value in update_data.items():
        setattr(db_org, field, value)

    db.commit()
    db.refresh(db_org)
    return db_org


def delete_organization(db: Session, org_id: int) -> bool:
    """Delete an organization (cascades to documents)."""
    db_org = get_organization(db, org_id)
    if not db_org:
        return False

    db.delete(db_org)
    db.commit()
    return True
