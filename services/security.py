from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db.db import get_db
from db.models import UserModel
from services.auth import decode_access_token, get_user_by_username

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> UserModel:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_access_token(token)
    username: str = payload.get("username") or payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_username(db, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        username: str = payload.get("username") or payload.get("sub")
        if not username:
            return None
        return get_user_by_username(db, username=username)
    except Exception:
        return None

def require_roles(allowed_roles: List[str]):
    def role_dependency(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        # Admins have full access across the system
        if current_user.role == "Admin" or current_user.role in allowed_roles:
            return current_user
        roles_str = ", ".join(allowed_roles)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient permissions. Required role: {roles_str} (Your role: {current_user.role})."
        )
    return role_dependency

require_admin = require_roles(["Admin"])
require_rescue_team_or_admin = require_roles(["Rescue Team", "Admin"])
require_authenticated_user = require_roles(["User", "Rescue Team", "Admin"])
