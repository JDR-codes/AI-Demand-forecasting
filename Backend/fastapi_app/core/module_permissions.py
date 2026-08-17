# fastapi_app/core/module_permissions.py
"""
Module-to-Permission mapping for the Access Controls tab.
"""

MODULE_CATALOG = {
    "dashboard": {
        "name": "Dashboard",
        "description": "Main dashboard & KPI overview",
        "actions": ["read"],
        "permissions": {
            "read": "dashboard:read",
        }
    },
    "data_integration": {
        "name": "Data Integration",
        "description": "Connect & sync data sources",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "data_sources:read",
            "write": "data_sources:write",
            "delete": "data_sources:delete",
        }
    },
    "data_processing": {
        "name": "Data Processing",
        "description": "Data pipelines & transformation",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "processing:read",
            "write": "processing:run",
            "delete": "processing:delete",
        }
    },
    "forecasting": {
        "name": "Forecasting Engine",
        "description": "AI model management & forecasts",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "forecast:read",
            "write": "forecast:run",
            "delete": "forecast:delete",
        }
    },
    "recommendations": {
        "name": "Recommendations",
        "description": "AI-driven business recommendations",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "recommendations:read",
            "write": "recommendations:run",
            "delete": "recommendations:delete",
        }
    },
    "simulation": {
        "name": "Simulation Engine",
        "description": "What-if analysis & scenario planning",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "simulation:read",
            "write": "simulation:run",
            "delete": "simulation:delete",
        }
    },
    "inventory": {
        "name": "Inventory Optimization",
        "description": "Stock levels & reorder management",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "inventory:read",
            "write": "inventory:write",
            "delete": "inventory:delete",
        }
    },
    "reports": {
        "name": "Reports",
        "description": "Analytics & business reports",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "reports:read",
            "write": "reports:generate",
            "delete": "reports:delete",
        }
    },
    "alerts": {
        "name": "Alerts",
        "description": "System notifications & alerts",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "alerts:read",
            "write": "alerts:write",
            "delete": "alerts:delete",
        }
    },
    "user_management": {
        "name": "User Management",
        "description": "User roles & access control",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "users:read",
            "write": "users:write",
            "delete": "users:delete",
        }
    },
    "audit": {
        "name": "Audit Logs",
        "description": "System audit & activity logs",
        "actions": ["read", "write", "delete"],
        "permissions": {
            "read": "audit:read",
            "write": "audit:manage",
            "delete": "audit:manage",
        }
    },
}


def get_module_permission(module_key: str, action: str) -> str:
    """Get the permission name for a specific module and action."""
    module = MODULE_CATALOG.get(module_key)
    if not module:
        raise ValueError(f"Unknown module: {module_key}")
    
    permission = module["permissions"].get(action)
    if not permission:
        raise ValueError(f"Action '{action}' not available for module '{module_key}'")
    
    return permission


def get_permission_module(permission_name: str) -> tuple[str, str]:
    """Reverse lookup: get module and action from a permission name."""
    for module_key, module in MODULE_CATALOG.items():
        for action, perm_name in module["permissions"].items():
            if perm_name == permission_name:
                return module_key, action
    raise ValueError(f"Unknown permission: {permission_name}")