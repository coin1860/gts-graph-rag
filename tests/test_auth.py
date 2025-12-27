"""Unit tests for authentication module."""

import pytest
from datetime import datetime, timedelta

from backend.auth.jwt import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password_123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """Test JWT token creation."""
    data = {"user_id": 1, "username": "testuser", "role": "admin"}
    token = create_access_token(data, expires_delta=timedelta(hours=1))

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token():
    """Test JWT token decoding."""
    data = {"user_id": 1, "username": "testuser", "role": "admin"}
    token = create_access_token(data, expires_delta=timedelta(hours=1))

    payload = decode_access_token(token)

    assert payload is not None
    assert payload.username == "testuser"
    assert payload.role == "admin"


def test_decode_expired_token():
    """Test that expired tokens are rejected."""
    data = {"user_id": 1, "username": "testuser", "role": "user"}
    # Create token that expires immediately
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))

    payload = decode_access_token(token)
    assert payload is None


def test_decode_invalid_token():
    """Test that invalid tokens are rejected."""
    invalid_token = "invalid.token.here"
    payload = decode_access_token(invalid_token)
    assert payload is None

