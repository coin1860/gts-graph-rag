"""Database setup and session management using SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from backend.models.db_models import Organization, User, Document  # noqa
    Base.metadata.create_all(bind=engine)
