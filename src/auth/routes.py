"""Authentication API routes.

This module defines the REST API endpoints for user authentication workflows.
"""

from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from src.auth.services import AuthServices
from src.auth.schemas import (
    LoginInput, 
    LoginResponse, 
    RenewAccessTokenResponse,
    LogoutInput,
    LogoutResponse
)
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session


from datetime import timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.utils.limiter import limiter
from src.utils.auth import get_current_user
import uuid


# reset_password_expiry = timedelta(minutes=5)  # Removed as requested

# Initialize router for auth endpoints
authRouter = APIRouter()

# Initialize service instances
authServices = AuthServices()
security = HTTPBearer(auto_error=False)

IS_PRODUCTION = True # Set this via environment variable in real usage

cookie_settings = {
    "httponly": True,
    "secure": IS_PRODUCTION,  # False for local HTTP, True for production HTTPS
    "samesite": "Lax" if not IS_PRODUCTION else "none"
}


@authRouter.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
@limiter.limit("5/minute")
async def loginUser(
    loginInput: LoginInput, 
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_Session)
):
    """Authenticate user with dual-auth token delivery.
    
    Supports both web (cookies) and mobile (JSON response) clients:
    - Web: Receives tokens in httponly cookies (XSS-safe)
    - Mobile: Extracts tokens from response body for manual storage
    
    Args:
        loginInput: Email and password credentials.
        request: Request object for future client detection.
        response: Response object to set cookies.
        session: Database session.
    
    Returns:
        LoginResponse with user data and tokens in body.
    """
    user = await authServices.login(loginInput, session)

    # Set httponly cookies for web clients (browser handles automatically)
    response.set_cookie(
        key="access_token",
        value=user.get('access_token'),
        **cookie_settings,
        max_age = 60 * 60 * 2
    )
    response.set_cookie(
        key="refresh_token",
        value=user.get('refresh_token'),
        **cookie_settings,
        max_age = 60 * 60 * 24 * 3
    )
   
    # Return tokens in body for mobile clients (cookies ignored by mobile HTTP clients)
    return {
        "success": True,
        "message": "login successful",
        "data": user  # Contains access_token & refresh_token for mobile
    }


@authRouter.get("/me", status_code=status.HTTP_200_OK)
async def get_me(
    user_info: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_Session)
):
    """Get current authenticated user details."""
    user_id = user_info.get("user_id")
    # Need to fetch full user details from DB
    from src.auth.models import User
    from sqlmodel import select
    
    statement = select(User).where(User.user_id == uuid.UUID(user_id))
    result = await session.exec(statement)
    user = result.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "success": True,
        "message": "User details fetched successfully",
        "data": {
            "id": str(user.user_id),
            "username": user.username,
            "role": user.role
        }
    }



@authRouter.post("/renew_access_token", status_code=status.HTTP_201_CREATED, response_model=RenewAccessTokenResponse)
@limiter.limit("5/minute")
async def renewAccessToken(
    request: Request,
    response: Response,
    bearer_token: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_Session) 
):
    """Renew access token using refresh token with dual-auth support.
    
    Detects client type from refresh token source and responds accordingly:
    - Web (cookies): Returns new tokens in cookies and empty response body
    - Mobile (bearer): Returns new tokens in response body
    
    Args:
        request: Request object to access cookie-based refresh tokens.
        response: Response object to set new cookies for web clients.
        bearer_token: Optional bearer token for mobile clients.
        session: Database session.
    
    Returns:
        RenewAccessTokenResponse with new tokens (format depends on client type).
    
    Raises:
        HTTPException: If refresh token missing or invalid.
    """
    token = None

    # Dual-auth: Extract refresh token from bearer header or cookies
    bearer_raw = bearer_token.credentials if bearer_token else None
    cookie_raw = request.cookies.get('refresh_token')

    # Priority: Bearer token first, fallback to cookies
    token = bearer_raw  or cookie_raw
    if token == None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    # Basic structural check (JWT should have 2 dots)
    if token.count('.') != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )

    # Generate new access and refresh tokens (rotates refresh token for security)
    new_token = await authServices.renewAccessToken(token, session)

    # Web client (cookie-based): Set new tokens in cookies
    if cookie_raw and not bearer_raw:

        response.set_cookie(
            key="access_token",
            value=new_token.get('access_token'),
            **cookie_settings,
            max_age=60 * 60 * 2
        )
        response.set_cookie(
            key="refresh_token",
            value=new_token.get('refresh_token'),
            **cookie_settings,
            max_age=60 * 60 * 24 * 3
        )
        # Return empty data; tokens delivered via cookies
        return {
            "success": True,
            "message": "access token renewed successfully",
            "data": {}  # Empty body for web clients
        }
    
    # Mobile client (bearer-based): Return tokens in response body
    if bearer_raw and not cookie_raw:
        return {
            "success": True,
            "message": "access token renewed successfully",
            "data": new_token  # Contains access_token & refresh_token
        }


@authRouter.post("/logout", status_code=status.HTTP_200_OK, response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    logout_input: LogoutInput,
    bearer_token: HTTPAuthorizationCredentials = Depends(security),
):
    """Logout user by revoking tokens with dual-auth support.
    
    Handles token revocation for both web and mobile clients:
    - Mobile: Reads tokens from Authorization header and request body
    - Web: Reads tokens from cookies
    Both tokens are added to Redis blocklist for immediate revocation.
    
    Args:
        request: Request object to access cookies.
        response: Response object to delete cookies.
        logout_input: Optional refresh token from request body (for mobile).
        bearer_token: Optional access token from Authorization header (for mobile).
    
    Returns:
        LogoutResponse confirming successful logout.
    
    Raises:
        HTTPException: If no tokens found in either source.
    """
    
    await authServices.logout(request, response, logout_input, bearer_token)
    
    return {
        "success": True,
        "message": "Logged out successfully",
        "data": {}
    }
