from fastapi import Header, HTTPException, Depends
from enum import Enum
from typing import List, Optional

class Role(str, Enum):
    ADMIN = "ADMIN"
    DBA = "DBA"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"

# Define permission sets
PERMISSIONS = {
    Role.ADMIN: ["view_metrics", "view_alerts", "execute_sql", "execute_dml", "modify_settings"],
    Role.DBA: ["view_metrics", "view_alerts", "execute_sql", "execute_dml"],
    Role.OPERATOR: ["view_metrics", "view_alerts", "execute_sql"], # Only SELECT (checked in DB layer)
    Role.VIEWER: ["view_metrics", "view_alerts"]
}

async def get_current_role(x_role: Optional[str] = Header(None)) -> Role:
    """
    Extracts the role from X-Role header. 
    Defaults to VIEWER if not provided or invalid.
    """
    if not x_role:
        return Role.VIEWER
    
    try:
        return Role(x_role.upper())
    except ValueError:
        return Role.VIEWER

def check_permission(required_permission: str):
    """
    Dependency factor to check if the current role has the required permission.
    """
    async def permission_dependency(role: Role = Depends(get_current_role)):
        if required_permission not in PERMISSIONS.get(role, []):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission denied: {required_permission} required for role {role.value}"
            )
        return role
    return permission_dependency
