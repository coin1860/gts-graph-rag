"""FastAPI main application server."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.crud.user import UserCreate, create_user, get_user_by_username
from backend.database import SessionLocal, init_db
from backend.models.db_models import UserRole
from backend.routers import (
    auth,
    chat,
    documents,
    organizations,
    temp_routes,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting GTS Graph RAG Backend...")

    # Initialize database
    init_db()
    print("✅ Database initialized")

    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    print("✅ Storage directories ready")

    # Create default admin user if none exists
    db = SessionLocal()
    try:
        if not get_user_by_username(db, "admin"):
            create_user(db, UserCreate(
                username="admin",
                password="admin123",  # Change in production!
                role=UserRole.ADMIN,
            ))
            print("✅ Default admin user created (admin/admin123)")
    except Exception as e:
        print(f"⚠️ Could not create default admin: {e}")
    finally:
        db.close()

    yield

    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="GTS Graph RAG API",
    description="Agentic GraphRAG system for HSBC BOI knowledge transfer",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(temp_routes.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(documents.public_router)  # Public document search endpoint


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "GTS Graph RAG API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
