"""Pydantic schemas for authentication API.

This module defines the request and response models used in authentication
endpoints. Validates data for the simplified, single-user-table architecture.
"""

from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import Optional
from src.auth.models import Role

# --- BASE MODELS (Used by multiple responses) ---

class User(BaseModel):
    """Base user model for responses (excludes sensitive data)."""
    user_id: uuid.UUID 
    username: str
    full_name: str
    role: Role
    created_at: datetime 

class UserCreateResponse(BaseModel):
    """Response structure for successful signup."""
    success: bool
    message: str
    data: User



# --- LOGIN ---

class LoginInput(BaseModel):
    """Payload for user login."""
    username: str
    password: str

class LoginData(BaseModel):
    """Data returned upon successful login."""
    user_id: uuid.UUID
    username: str
    full_name: str
    created_at: datetime
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

class LoginResponse(BaseModel):
    """Response structure for successful login."""
    success: bool
    message: str
    data: LoginData




# --- TOKEN RENEWAL ---

class RenewAccessTokenResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}

# --- LOGOUT ---

class LogoutInput(BaseModel):
    refresh_token: Optional[str] = None

class LogoutResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}