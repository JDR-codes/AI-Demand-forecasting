# scripts/create_super_admin.py
"""
Script to create the initial super admin user.
This should be run during application setup.
"""

import os
import sys
from getpass import getpass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from fastapi_app.db.session import SessionLocal, init_db
from fastapi_app.schemas.user_schema import UserCreate
from fastapi_app.services.users.user_service import create_user
from fastapi_app.core.config import ROLE_SUPER_ADMIN
from fastapi_app.models.role_model import Role


def main():
    print("=" * 60)
    print("Create Super Admin User")
    print("=" * 60)
    
    name = input("Name: ")
    email = input("Email: ")

    while True:
        password = getpass("Password: ")
        confirm_password = getpass("Confirm Password: ")
        if password == confirm_password:
            if len(password) < 8:
                print("Password must be at least 8 characters long.")
                continue
            break
        print("Passwords do not match. Please try again.\n")

    # Initialize database
    init_db()

    db = SessionLocal()

    try:
        super_admin_role = db.query(Role).filter(Role.name == ROLE_SUPER_ADMIN).first()
        if not super_admin_role:
            print("Error: super_admin role not found. Database seeding failed.")
            return

        user_data = UserCreate(
            name=name,
            email=email,
            password=password,
            role_id=super_admin_role.id,
            is_active=True,
            permission_ids=[],
        )

        user = create_user(db, user_data)

        print("\n" + "=" * 60)
        print("Super Admin Created Successfully")
        print("=" * 60)
        print(f"ID: {user.id}")
        print(f"Name: {user.name}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role.name if user.role else 'None'}")
        print("=" * 60)

    except Exception as e:
        print("Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    main()