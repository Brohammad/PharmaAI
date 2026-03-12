"""
PharmaIQ – JWT Authentication

Roles:
  VIEWER    — read-only access (default for demo)
  PHARMACIST — can view all + acknowledge minor alerts
  MANAGER   — can approve / reject escalations (TIER_2 authority)
  ADMIN     — full access

Demo users (seeded):
  manager@medchain.in  / pharmaiq-demo  (MANAGER)
  admin@medchain.in    / pharmaiq-admin (ADMIN)
  viewer@medchain.in   / pharmaiq-view  (VIEWER)

In production, replace _DEMO_USERS with a proper database lookup.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────────
SECRET_KEY     = os.getenv("JWT_SECRET_KEY", "pharmaiq-dev-secret-change-in-production-32chars!")
ALGORITHM      = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8h

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


# ── Demo user store ────────────────────────────────────────────────────────────
_DEMO_USERS: dict[str, dict[str, Any]] = {
    "manager@medchain.in": {
        "username":      "manager@medchain.in",
        "full_name":     "Ravi Krishnamurthy",
        "role":          "MANAGER",
        "hashed_password": pwd_context.hash("pharmaiq-demo"),
        "disabled":      False,
    },
    "admin@medchain.in": {
        "username":      "admin@medchain.in",
        "full_name":     "Ananya Singh",
        "role":          "ADMIN",
        "hashed_password": pwd_context.hash("pharmaiq-admin"),
        "disabled":      False,
    },
    "viewer@medchain.in": {
        "username":      "viewer@medchain.in",
        "full_name":     "Demo Viewer",
        "role":          "VIEWER",
        "hashed_password": pwd_context.hash("pharmaiq-view"),
        "disabled":      False,
    },
}

ROLE_HIERARCHY = {"VIEWER": 0, "PHARMACIST": 1, "MANAGER": 2, "ADMIN": 3}


# ── Pydantic models ────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserPublic"


class UserPublic(BaseModel):
    username: str
    full_name: str
    role: str


Token.model_rebuild()


# ── Core helpers ───────────────────────────────────────────────────────────────
def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _get_user(username: str) -> dict | None:
    return _DEMO_USERS.get(username)


def authenticate_user(username: str, password: str) -> dict | None:
    user = _get_user(username)
    if not user:
        return None
    if not _verify_password(password, user["hashed_password"]):
        return None
    if user.get("disabled"):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── FastAPI dependencies ───────────────────────────────────────────────────────
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict | None:
    """
    Returns the current user dict, or None if no token is provided.
    Call require_role() for protected endpoints.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            return None
        return _get_user(username)
    except JWTError:
        return None


def require_role(minimum_role: str):
    """
    Dependency factory — raises 401 if no token, 403 if insufficient role.
    Usage:  Depends(require_role("MANAGER"))
    """
    async def _checker(token: str = Depends(oauth2_scheme)) -> dict:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        forbidden_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {minimum_role}+.",
        )
        if not token:
            raise credentials_exception
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub", "")
            if not username:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = _get_user(username)
        if not user:
            raise credentials_exception

        user_level = ROLE_HIERARCHY.get(user["role"], 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)
        if user_level < required_level:
            raise forbidden_exception
        return user

    return _checker
