"""
Script to create default admin user.
"""

from backend.database import SessionLocal, init_db
from backend.crud.user import create_user, get_user_by_username, UserCreate
from backend.models.db_models import UserRole


def main():
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        # Check if admin exists
        existing_admin = get_user_by_username(db, "admin")
        if existing_admin:
            print("✅ Admin user already exists")
            print(f"   Username: {existing_admin.username}")
            print(f"   Role: {existing_admin.role}")
            return
        
        # Create admin user
        print("Creating admin user...")
        admin = create_user(
            db,
            UserCreate(
                username="admin",
                password="admin123",
                role=UserRole.ADMIN,
            )
        )
        print(f"✅ Admin user created successfully!")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   Role: {admin.role}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
