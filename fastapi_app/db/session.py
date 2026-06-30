from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from fastapi_app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def _ensure_sqlite_forecast_columns():
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(forecasts);"))
        columns = {row[1] for row in result.fetchall()}

        if "model_id" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE forecasts ADD COLUMN model_id VARCHAR(255)"
                )
            )

        if "created_at" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE forecasts ADD COLUMN created_at DATETIME NOT NULL DEFAULT (datetime('now'))"
                )
            )

        if "updated_at" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE forecasts ADD COLUMN updated_at DATETIME NOT NULL DEFAULT (datetime('now'))"
                )
            )

        # Ensure recommendation table has required timestamp and status columns
        result = conn.execute(text("PRAGMA table_info(recommendations);"))
        rec_columns = {row[1] for row in result.fetchall()}

        if "created_at" not in rec_columns:
            conn.execute(
                text(
                    "ALTER TABLE recommendations ADD COLUMN created_at DATETIME NOT NULL DEFAULT (datetime('now'))"
                )
            )

        if "updated_at" not in rec_columns:
            conn.execute(
                text(
                    "ALTER TABLE recommendations ADD COLUMN updated_at DATETIME NOT NULL DEFAULT (datetime('now'))"
                )
            )

        if "status" not in rec_columns:
            conn.execute(
                text(
                    "ALTER TABLE recommendations ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'pending'"
                )
            )


def _seed_rbac_defaults():
    """Idempotently seed the default roles and permission catalog.

    Runs on every init_db() call. Safe to run repeatedly — uses get-or-create
    by unique `name`, so it never duplicates rows or overwrites edits an
    admin made later via the Roles API.
    """
    from fastapi_app.models.permission_model import Permission
    from fastapi_app.models.role_model import Role

    # Fixed catalog of fine-grained permissions covering the app's resource
    # areas. Permissions themselves are not admin-editable (no POST/PUT/DELETE
    # in the API) — only which permissions are attached to a Role is editable.
    PERMISSION_CATALOG = [
        ("users:read", "View user accounts"),
        ("users:write", "Create or update user accounts"),
        ("users:delete", "Delete user accounts"),
        ("roles:read", "View roles and their permissions"),
        ("roles:write", "Create or update roles"),
        ("roles:delete", "Delete roles"),
        ("data:read", "View data sources and uploaded datasets"),
        ("data:write", "Upload or modify data sources and datasets"),
        ("forecast:read", "View forecasts and trained models"),
        ("forecast:run", "Train models and generate forecasts"),
        ("recommendations:read", "View generated recommendations"),
        ("validation:read", "View data validation results"),
        ("inventory:read", "View inventory, stock, and reorder data"),
        ("inventory:write", "Modify inventory, transfers, and reorder points"),
    ]

    db = SessionLocal()
    try:
        existing_permissions = {p.name: p for p in db.query(Permission).all()}
        for name, description in PERMISSION_CATALOG:
            if name not in existing_permissions:
                perm = Permission(name=name, description=description)
                db.add(perm)
                existing_permissions[name] = perm
        db.commit()

        existing_roles = {r.name: r for r in db.query(Role).all()}

        if "super_admin" not in existing_roles:
            super_admin = Role(
                name="super_admin",
                description="Full access to every resource in the system.",
            )
            super_admin.permissions = list(existing_permissions.values())
            db.add(super_admin)

        if "user" not in existing_roles:
            user_role = Role(
                name="user",
                description="Default role for newly created accounts. No elevated permissions.",
            )
            db.add(user_role)

        db.commit()
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_forecast_columns()
    _seed_rbac_defaults()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()