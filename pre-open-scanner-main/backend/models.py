"""
Pydantic models for Pre-Open Scanner API.

Request/response schemas and shared data structures.
"""

from pydantic import BaseModel

class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = "healthy"
