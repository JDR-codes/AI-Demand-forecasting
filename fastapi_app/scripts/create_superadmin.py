# app/scripts/create_superadmin.py

import os
import sys
from getpass import getpass

# Ensure the repo root is on sys.path when running this script directly from fastapi_app/
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from fastapi_app.db.session import SessionLocal, init_db
from fastapi_app.schemas.auth_schema import SuperAdminCreate
from fastapi_app.services.auth.auth_service import create_super_admin


def main():
    name = input("Name: ")
    email = input("Email: ")
    password = getpass("Password: ")

    # ensure DB tables exist (creates missing tables from SQLAlchemy models)
    init_db()

    db = SessionLocal()

    try:
        user_data = SuperAdminCreate(
            name=name,
            email=email,
            password=password
        )

        user = create_super_admin(db, user_data)

        print("\nSuper Admin Created Successfully")
        print(f"ID: {user.id}")
        print(f"Name: {user.name}")
        print(f"Email: {user.email}")

    except Exception as e:
        print("Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    main()