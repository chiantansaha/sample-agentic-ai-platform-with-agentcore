"""Simple authentication middleware for development"""
from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify token from Authorization header

    In development mode, authentication is skipped and returns a dev user.

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        User payload dict

    Raises:
        HTTPException: If token is missing (in production mode)
    """
    # Development mode - bypass authentication
    if settings.SKIP_AUTH:
        return {"sub": "dev-user", "email": "dev@example.com", "name": "Dev User"}

    # Production mode - validate token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Simple token validation for development
    if token == "dev-token":
        return {"sub": "dev-user", "email": "dev@example.com", "name": "Dev User"}

    # For production, implement proper JWT validation here
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(token_payload: dict) -> dict:
    """
    Extract user information from validated token

    Args:
        token_payload: Decoded token payload

    Returns:
        User information dict
    """
    return {
        "user_id": token_payload.get("sub"),
        "email": token_payload.get("email"),
        "name": token_payload.get("name"),
    }


# Alias for backward compatibility
verify_okta_token = verify_token
