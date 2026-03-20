"""
Authentication module for Pre-Open Scanner.

Handles JWT tokens, password hashing, and protected route dependencies.
Uses python-jose for JWT and passlib[bcrypt] for passwords.
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext

# Load secret from environment (set in .env or system)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=True)


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token with expiration.

    Args:
        data: Payload to encode (e.g. {"sub": username, "scope": "user"}).
              Do not put sensitive data in the payload.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(tz=timezone.utc)
    encoded = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT string (usually from Authorization: Bearer <token>).

    Returns:
        Decoded payload dict (e.g. sub, exp, iat).

    Raises:
        HTTPException: 401 if token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        return payload
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain-text password.

    Returns:
        Bcrypt hash string (safe to store in DB).
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.

    Args:
        plain_password: User-supplied password.
        hashed_password: Stored hash from get_password_hash().

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency for protected routes.

    Extracts the Bearer token from the Authorization header, verifies it,
    and returns the decoded payload (user data). Use in route dependencies:

        @app.get("/me")
        async def me(user: dict = Depends(get_current_user)):
            return user

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.
    """
    payload = verify_token(token)
    # Optional: require "sub" (subject) for user identity
    if "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
