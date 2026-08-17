# fastapi_app/db/session.py

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from fastapi_app.core.config import (
    DATABASE_URL,
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_VIEWER,
    ROLE_AI_ANALYST,
    ROLE_DATA_ENGINEER,
    PROTECTED_ROLES,
)


def _ensure_mysql_database_exists(database_url: str) -> None:
    """Create the MySQL database if it does not already exist."""
    parsed_url = make_url(database_url)
    if not parsed_url.drivername.startswith("mysql"):
        return

    if not parsed_url.database:
        return

    database_name = parsed_url.database
    admin_url = parsed_url.set(database="")

    admin_engine = create_engine(
        admin_url,
        pool_pre_ping=True,
        echo=False,
    )

    try:
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                    "DEFAULT CHARACTER SET utf8mb4 "
                    "COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        admin_engine.dispose()


Base = declarative_base()

# Import models AFTER Base is defined to avoid circular imports
from fastapi_app import models

# Ensure the target database exists before creating the engine
_ensure_mysql_database_exists(DATABASE_URL)

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


def _seed_roles(db):
    """Seed the six fixed system roles with UI-compatible display names."""
    from fastapi_app.models.role_model import Role
    
    roles_data = [
        (ROLE_SUPER_ADMIN, "Super Admin", "Full access to every resource in the system. Can manage all users, roles, and system configuration.", True),
        (ROLE_ADMIN, "Admin", "Can manage normal users, assign roles, and configure permissions for non-system roles.", True),
        (ROLE_MANAGER, "Manager", "Manager-level access with read and write capabilities for business operations.", True),
        (ROLE_VIEWER, "Viewer", "Read-only access to all application data and reports.", True),
        # Fixed display names to match UI
        (ROLE_AI_ANALYST, "AI Engineer", "Specialized access for AI and forecasting operations. Can run forecasts and generate recommendations.", True),
        (ROLE_DATA_ENGINEER, "Data Analyst", "Specialized access for data operations. Can manage data sources, uploads, and processing.", True),
    ]
    
    existing_roles = {r.name: r for r in db.query(Role).all()}
    
    for name, display_name, description, is_system in roles_data:
        if name not in existing_roles:
            role = Role(
                name=name,
                display_name=display_name,
                description=description,
                is_system_role=is_system,
                # Default access control settings
                login_enabled=True,
                require_mfa=False,
                ip_restriction_enabled=False,
                allowed_ip_ranges=None,
                session_timeout_hours=8,
                max_concurrent_sessions=3,
            )
            db.add(role)
        else:
            # Update existing roles
            role = existing_roles[name]
            if not role.display_name or role.display_name != display_name:
                role.display_name = display_name
            if role.login_enabled is None:  # For backward compatibility
                role.login_enabled = True
    
    db.commit()
    return {r.name: r for r in db.query(Role).all()}


def _seed_permissions(db):
    """Seed the complete permission catalog."""
    from fastapi_app.models.permission_model import Permission
    
    PERMISSION_CATALOG = [
        # User Management
        ("users:read", "View user accounts and their details"),
        ("users:write", "Create or update user accounts"),
        ("users:delete", "Delete user accounts"),
        ("users:manage", "Manage user status, roles, and permissions"),
        
        # Role Management
        ("roles:read", "View roles and their permissions"),
        ("roles:write", "Create or update roles"),
        ("roles:delete", "Delete roles"),
        
        # Dashboard
        ("dashboard:read", "View dashboard and analytics"),
        
        # Simulation Engine
        ("simulation:read", "View simulation results and models"),
        ("simulation:run", "Run simulations"),
        ("simulation:delete", "Delete simulation results"),
        
        # Data Sources (includes uploads)
        ("data_sources:read", "View data sources, uploaded datasets, and files"),
        ("data_sources:write", "Upload, modify, or update data sources and files"),
        ("data_sources:delete", "Delete data sources and uploaded files"),
        
        # Data Processing (includes validation)
        ("processing:read", "View data processing jobs, validation results, and status"),
        ("processing:run", "Run data processing and validation jobs"),
        ("processing:delete", "Delete processing jobs and validation results"),
        
        # Forecast
        ("forecast:read", "View forecasts and trained models"),
        ("forecast:run", "Train models and generate forecasts"),
        ("forecast:delete", "Delete forecasts and models"),
        
        # Recommendations
        ("recommendations:read", "View generated recommendations"),
        ("recommendations:run", "Generate recommendations"),
        ("recommendations:delete", "Delete recommendations"),
        
        # Inventory
        ("inventory:read", "View inventory, stock, and reorder data"),
        ("inventory:write", "Modify inventory, transfers, and reorder points"),
        ("inventory:delete", "Delete inventory records"),
        
        # Reports
        ("reports:read", "View reports and dashboards"),
        ("reports:generate", "Generate and download reports"),
        ("reports:delete", "Delete reports"),
        
        # Alerts
        ("alerts:read", "View system alerts and notifications"),
        ("alerts:write", "Create and update alerts"),
        ("alerts:delete", "Delete alerts"),
        
        # Audit
        ("audit:read", "View audit logs"),
        ("audit:manage", "Manage audit log retention and settings"),
    ]
    
    existing_permissions = {p.name: p for p in db.query(Permission).all()}
    
    for name, description in PERMISSION_CATALOG:
        if name not in existing_permissions:
            perm = Permission(name=name, description=description)
            db.add(perm)
            existing_permissions[name] = perm
    
    db.commit()
    return existing_permissions


def _assign_role_permissions(db, roles, permissions):
    """
    Assign permissions to roles based on the permission matrix.
    Maps UI module access to actual permission names.
    """
    from fastapi_app.models.role_model import Role
    
    # ──────────────────────────────────────────────────────────────────────────
    # MODULE TO PERMISSION MAPPING
    # This maps UI module names to their permission names
    # ──────────────────────────────────────────────────────────────────────────
    
    # Dashboard - read only
    DASHBOARD_PERMS = [
        permissions.get("dashboard:read"),
    ]
    
    # User Management
    USER_MANAGEMENT_PERMS = [
        permissions.get("users:read"),
        permissions.get("users:write"),
        permissions.get("users:delete"),
        permissions.get("users:manage"),
    ]
    
    # Role Management
    ROLE_MANAGEMENT_PERMS = [
        permissions.get("roles:read"),
        permissions.get("roles:write"),
        permissions.get("roles:delete"),
    ]
    
    # Data Integration (Data Sources)
    DATA_INTEGRATION_PERMS = [
        permissions.get("data_sources:read"),
        permissions.get("data_sources:write"),
        permissions.get("data_sources:delete"),
    ]
    
    # Data Processing
    DATA_PROCESSING_PERMS = [
        permissions.get("processing:read"),
        permissions.get("processing:run"),
        permissions.get("processing:delete"),
    ]
    
    # Forecasting Engine
    FORECASTING_PERMS = [
        permissions.get("forecast:read"),
        permissions.get("forecast:run"),
        permissions.get("forecast:delete"),
    ]
    
    # Recommendations
    RECOMMENDATIONS_PERMS = [
        permissions.get("recommendations:read"),
        permissions.get("recommendations:run"),
        permissions.get("recommendations:delete"),
    ]
    
    # Simulation Engine
    SIMULATION_PERMS = [
        permissions.get("simulation:read"),
        permissions.get("simulation:run"),
        permissions.get("simulation:delete"),
    ]
    
    # Inventory Optimization
    INVENTORY_PERMS = [
        permissions.get("inventory:read"),
        permissions.get("inventory:write"),
        permissions.get("inventory:delete"),
    ]
    
    # Reports
    REPORTS_PERMS = [
        permissions.get("reports:read"),
        permissions.get("reports:generate"),
        permissions.get("reports:delete"),
    ]
    
    # Alerts
    ALERTS_PERMS = [
        permissions.get("alerts:read"),
        permissions.get("alerts:write"),
        permissions.get("alerts:delete"),
    ]
    
    # Audit
    AUDIT_PERMS = [
        permissions.get("audit:read"),
        permissions.get("audit:manage"),
    ]
    
    # ──────────────────────────────────────────────────────────────────────────
    # ROLE PERMISSION DEFINITIONS
    # ──────────────────────────────────────────────────────────────────────────
    
    # Super Admin: ALL permissions
    super_admin_perms = list(permissions.values())
    
    # Admin: Everything except audit:manage and roles:delete (for now)
    admin_perms = (
        DASHBOARD_PERMS +
        USER_MANAGEMENT_PERMS +
        [permissions.get("roles:read")] +  # Admin can read roles but not delete
        DATA_INTEGRATION_PERMS +
        DATA_PROCESSING_PERMS +
        FORECASTING_PERMS +
        RECOMMENDATIONS_PERMS +
        SIMULATION_PERMS +
        INVENTORY_PERMS +
        REPORTS_PERMS +
        ALERTS_PERMS +
        [permissions.get("audit:read")]  # Admin can read audit logs
    )
    admin_perms = [p for p in admin_perms if p is not None]
    
    # Manager: Dashboard + read/write for business operations
    manager_perms = (
        DASHBOARD_PERMS +
        DATA_INTEGRATION_PERMS +
        DATA_PROCESSING_PERMS +
        FORECASTING_PERMS +
        RECOMMENDATIONS_PERMS +
        SIMULATION_PERMS +
        INVENTORY_PERMS +
        REPORTS_PERMS +
        ALERTS_PERMS
    )
    manager_perms = [p for p in manager_perms if p is not None]
    
    # Data Analyst (Data Engineer): Data operations focus
    data_analyst_perms = (
        DASHBOARD_PERMS +
        DATA_INTEGRATION_PERMS +
        DATA_PROCESSING_PERMS +
        INVENTORY_PERMS +
        REPORTS_PERMS
    )
    data_analyst_perms = [p for p in data_analyst_perms if p is not None]
    
    # AI Engineer (AI Analyst): AI and forecasting focus
    ai_engineer_perms = (
        DASHBOARD_PERMS +
        DATA_INTEGRATION_PERMS +  # Read data sources
        DATA_PROCESSING_PERMS +    # Read processing
        FORECASTING_PERMS +
        RECOMMENDATIONS_PERMS +
        INVENTORY_PERMS +          # Read inventory
        REPORTS_PERMS +
        ALERTS_PERMS               # Read alerts
    )
    ai_engineer_perms = [p for p in ai_engineer_perms if p is not None]
    
    # Viewer: Read-only access to everything
    viewer_perms = (
        DASHBOARD_PERMS +
        [permissions.get("data_sources:read")] +
        [permissions.get("processing:read")] +
        [permissions.get("forecast:read")] +
        [permissions.get("recommendations:read")] +
        [permissions.get("inventory:read")] +
        [permissions.get("reports:read")] +
        [permissions.get("alerts:read")]
    )
    viewer_perms = [p for p in viewer_perms if p is not None]
    
    role_permissions_map = {
        ROLE_SUPER_ADMIN: super_admin_perms,
        ROLE_ADMIN: admin_perms,
        ROLE_MANAGER: manager_perms,
        ROLE_DATA_ENGINEER: data_analyst_perms,      # Data Analyst
        ROLE_AI_ANALYST: ai_engineer_perms,          # AI Engineer
        ROLE_VIEWER: viewer_perms,
    }
    
    for role_name, perms in role_permissions_map.items():
        role = roles.get(role_name)
        if role:
            role.permissions = perms
    
    db.commit()


def _seed_rbac_defaults():
    """Idempotently seed the default roles and permission catalog."""
    db = SessionLocal()
    try:
        # Seed permissions first (they're referenced by roles)
        permissions = _seed_permissions(db)
        
        # Seed roles
        roles = _seed_roles(db)
        
        # Assign permissions to roles
        _assign_role_permissions(db, roles, permissions)
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database - create tables and seed default data."""
    Base.metadata.create_all(bind=engine)
    _seed_rbac_defaults()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()