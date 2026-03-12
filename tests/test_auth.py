"""
tests/test_auth.py — JWT authentication & role-based access control unit tests
"""

import pytest
from datetime import timedelta


# ── Setup ─────────────────────────────────────────────────────────────────
import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-auth-testing!!")


# ── Imports after env setup ───────────────────────────────────────────────
from api.auth import (
    authenticate_user,
    create_access_token,
    _DEMO_USERS as USERS_DB,
    ROLE_HIERARCHY,
    SECRET_KEY,
    ALGORITHM,
)
from jose import jwt as jose_jwt, JWTError


def _decode_token(token: str):
    """Helper: decode a JWT and return the payload, or None if invalid."""
    try:
        return jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── User Authentication ───────────────────────────────────────────────────

def test_authenticate_manager_correct():
    user = authenticate_user("manager@medchain.in", "pharmaiq-demo")
    assert user is not None
    assert user["role"] == "MANAGER"


def test_authenticate_admin_correct():
    user = authenticate_user("admin@medchain.in", "pharmaiq-admin")
    assert user is not None
    assert user["role"] == "ADMIN"


def test_authenticate_viewer_correct():
    user = authenticate_user("viewer@medchain.in", "pharmaiq-view")
    assert user is not None
    assert user["role"] == "VIEWER"


def test_authenticate_wrong_password():
    user = authenticate_user("manager@medchain.in", "wrong-password")
    assert user is None


def test_authenticate_nonexistent_user():
    user = authenticate_user("ghost@example.com", "any-password")
    assert user is None


def test_authenticate_empty_password():
    user = authenticate_user("manager@medchain.in", "")
    assert user is None


# ── JWT Token Creation ────────────────────────────────────────────────────

def test_create_access_token_returns_string():
    token = create_access_token({"sub": "test@example.com", "role": "VIEWER"})
    assert isinstance(token, str)
    assert len(token) > 20


def test_create_access_token_custom_expiry():
    token = create_access_token(
        {"sub": "test@example.com", "role": "MANAGER"},
        expires_delta=timedelta(minutes=5),
    )
    assert isinstance(token, str)


def test_get_current_user_valid_token():
    user_data = {"sub": "test@example.com", "role": "ADMIN", "full_name": "Test User"}
    token = create_access_token(user_data, expires_delta=timedelta(minutes=30))
    payload = _decode_token(token)
    assert payload is not None
    assert payload["sub"] == "test@example.com"
    assert payload["role"] == "ADMIN"


def test_get_current_user_invalid_token():
    payload = _decode_token("not.a.valid.jwt.token")
    assert payload is None


def test_get_current_user_tampered_token():
    user_data = {"sub": "attacker@evil.com", "role": "ADMIN"}
    token = create_access_token(user_data)
    # Tamper with the payload section
    parts = token.split(".")
    tampered = parts[0] + ".AAAABBBBCCCC." + parts[2]
    payload = _decode_token(tampered)
    assert payload is None


# ── Role Hierarchy ────────────────────────────────────────────────────────

def test_role_hierarchy_admin_highest():
    assert ROLE_HIERARCHY["ADMIN"] > ROLE_HIERARCHY["MANAGER"]
    assert ROLE_HIERARCHY["MANAGER"] > ROLE_HIERARCHY["PHARMACIST"]
    assert ROLE_HIERARCHY["PHARMACIST"] > ROLE_HIERARCHY["VIEWER"]


def test_role_hierarchy_viewer_lowest():
    assert ROLE_HIERARCHY["VIEWER"] == 0


# ── USERS_DB structure ────────────────────────────────────────────────────

def test_users_db_has_required_keys():
    for email, user in USERS_DB.items():
        assert "username" in user, f"{email} missing 'username'"
        assert "hashed_password" in user, f"{email} missing 'hashed_password'"
        assert "role" in user, f"{email} missing 'role'"
        assert "full_name" in user, f"{email} missing 'full_name'"
        assert user["role"] in ROLE_HIERARCHY, f"{email} has unknown role: {user['role']}"


def test_users_db_passwords_are_hashed():
    """Ensure passwords are bcrypt hashed, not stored in plain text."""
    plain_passwords = ["pharmaiq-demo", "pharmaiq-admin", "pharmaiq-view"]
    for _, user in USERS_DB.items():
        for plain in plain_passwords:
            assert user["hashed_password"] != plain, (
                "Plain text password found in USERS_DB!"
            )
        assert user["hashed_password"].startswith("$2"), (
            f"Password for {user['username']} does not look like a bcrypt hash"
        )


def test_three_demo_users_exist():
    emails = list(USERS_DB.keys())
    assert "manager@medchain.in" in emails
    assert "admin@medchain.in" in emails
    assert "viewer@medchain.in" in emails
