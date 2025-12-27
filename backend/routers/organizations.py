"""Organization admin routes - CRUD for organizations."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import AdminUser
from backend.crud.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    create_organization,
    delete_organization,
    get_organization,
    get_organizations,
    update_organization,
)
from backend.database import get_db

router = APIRouter(prefix="/api/admin/organizations", tags=["admin-organizations"])


class SchemaUpdate(BaseModel):
    """Schema update request."""

    node_types: list[str]
    relationship_types: list[str]
    patterns: list[list[str]]


@router.post("", response_model=OrganizationResponse)
async def create_org(
    org_data: OrganizationCreate,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Create a new organization."""
    try:
        org = create_organization(db, org_data)
        return org
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[OrganizationResponse])
async def list_orgs(
    skip: int = 0,
    limit: int = 100,
    admin: AdminUser = None,  # Optional, allows non-admin to see their orgs
    db: Session = Depends(get_db)
):
    """List all organizations (admin sees all)."""
    return get_organizations(db, skip=skip, limit=limit)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_org(
    org_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Get organization by ID."""
    org = get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_org(
    org_id: int,
    org_data: OrganizationUpdate,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Update organization."""
    try:
        org = update_organization(db, org_id, org_data)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{org_id}/schema", response_model=OrganizationResponse)
async def update_org_schema(
    org_id: int,
    schema_data: SchemaUpdate,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Update organization's graph schema."""
    org = get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Convert patterns from list to tuple format
    patterns = [tuple(p) for p in schema_data.patterns]

    graph_schema = {
        "node_types": schema_data.node_types,
        "relationship_types": schema_data.relationship_types,
        "patterns": patterns,
    }

    try:
        org = update_organization(
            db, org_id,
            OrganizationUpdate(graph_schema=graph_schema)
        )
        return org
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{org_id}")
async def delete_org(
    org_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Delete organization (cascades to documents)."""
    success = delete_organization(db, org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"message": "Organization deleted successfully"}
