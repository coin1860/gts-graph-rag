"""
Script to reset admin password.
"""

from backend.database import SessionLocal, init_db
from backend.crud.user import get_user_by_username
from backend.auth.jwt import get_password_hash


def main():
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        # Find admin user
        admin = get_user_by_username(db, "admin")
        if not admin:
            print("⚠️ Admin user not found. Creating new admin user...")
            from backend.models.db_models import User, UserRole
            from backend.crud.user import create_user, UserCreate
            
            create_user(db, UserCreate(
                username="admin",
                password="admin123",
                role=UserRole.ADMIN
            ))
            print("✅ Admin user created successfully!")
            print(f"   Username: admin")
            print(f"   Password: admin123")
            return
        
        # Reset password
        new_hash = get_password_hash("admin123")
        admin.password_hash = new_hash
        db.commit()
        
        print(f"✅ Admin password reset successfully!")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
