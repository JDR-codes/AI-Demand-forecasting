# app/scripts/create_superadmin.py

from getpass import getpass

from fastapi_app.db.session import SessionLocal
from fastapi_app.schemas.auth_schema import SuperAdminCreate
from fastapi_app.modules.auth.auth_service import create_super_admin


def main():
    name = input("Name: ")
    email = input("Email: ")
    password = getpass("Password: ")

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