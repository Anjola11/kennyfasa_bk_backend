"""Authentication service layer.

This module implements the business logic for user authentication operations
including signup, login, and OTP verification. It handles user model selection
based on role (planner/vendor) and manages token generation for authenticated
sessions.
"""

from sqlmodel import select
from src.auth.models import User
from src.auth.schemas import LoginInput, LogoutInput

from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import DatabaseError
from src.utils.auth import verify_password_hash, create_token, decode_token
from datetime import datetime, timezone, timedelta
import uuid
from src.db.redis import redis_client


access_token_expiry = timedelta(hours=2)
refresh_token_expiry = timedelta(days=3)

class AuthServices:
    """Service class for authentication operations.
    
    Provides methods for user registration, login, and OTP verification.
    Handles role-based model selection and token generation.
    """

    async def get_user_by_username(self, username: str, session: AsyncSession):
        """Retrieves User by username.
        
        Args:
            username: User username address.
            session: Database session.
            
        Returns:
            User instance if found, None otherwise.
        """
        try:
            statement = select(User).where(User.username == username)
            result = await session.exec(statement)
            return result.first()
        except DatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error during user lookup: {str(e)}"
            )
        
    async def check_user_exists(self, user_id: str, session: AsyncSession):
        """Checks if admin already exists.
        
        Args:
            email: Admin email to check.
            session: Database session.
            
        Raises:
            HTTPException: If email already exists.
        """
        statement = select(User).where(User.user_id == user_id)
        result = await session.exec(statement)
        user = result.first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to proceed"
            )
        
    async def login(self, loginInput: LoginInput, session: AsyncSession):
        """Authenticate user and generate tokens for dual-auth delivery.
        
        Returns both access and refresh tokens in response dict for dual delivery:
        - Route layer sets tokens as httponly cookies (web clients)
        - Response body contains tokens (mobile clients extract and store)
        
        Args:
            loginInput: User username and password credentials.
            session: Database session.
        
        Returns:
            dict: User data with access_token and refresh_token included.
        
        Raises:
            HTTPException: If credentials invalid or username not verified.
        """
        
        # Query user by username using Helper (case-insensitive: convert to lowercase)
        username_lower = loginInput.username.lower()
        user = await self.get_user_by_username(username_lower, session)
        
        # Reusable exception for invalid credentials
        INVALID_CREDENTIALS = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Credentials"
        )

        # Validate user exists
        if not user:
            raise INVALID_CREDENTIALS
        
        
        # Verify password hash matches
        verified_password = verify_password_hash(loginInput.password, user.password_hash)

        if not verified_password:
            raise INVALID_CREDENTIALS

        # Generate authentication tokens for dual-auth delivery
        user_dict = user.model_dump()
        access_token = create_token(user_dict, access_token_expiry, type="access")
        refresh_token = create_token(user_dict, refresh_token_expiry, type="refresh")
        
        # Return tokens in dict for dual delivery (cookies + response body)
        user_details = {
            **user_dict, 
            'access_token': access_token,  # Will be set in cookies and returned in body
            'refresh_token': refresh_token,  # Will be set in cookies and returned in body
            
        }
        
        return user_details
    


        
    async def renewAccessToken(self, old_refresh_token_str: str,  session: AsyncSession):
        """Renew access token using refresh token with rotation (dual-auth agnostic).
        
        Implements refresh token rotation for security: old refresh token is blocklisted
        and a new refresh token is issued. Works for both mobile and web clients.
        Route layer determines response format based on request source.
        
        Args:
            old_refresh_token_str: Refresh token from cookies or bearer header.
            session: Database session.
        
        Returns:
            dict: New access_token and refresh_token.
        
        Raises:
            HTTPException: If token invalid, expired, or already used (rotation detection).
        """
        # Decode and validate refresh token
        old_refresh_token_decode = decode_token(old_refresh_token_str)

        # Ensure this is a refresh token, not access/reset
        if old_refresh_token_decode.get('type') != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token type"
            )
        
        # Detect refresh token reuse (security: rotation attack)
        jti = old_refresh_token_decode.get('jti')
        if await self.is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Refresh token reused. Login required."
            )

        # Retrieve user from token subject
        user_id = old_refresh_token_decode.get("sub") 
        statement = select(User).where(User.user_id == uuid.UUID(user_id))
        result = await session.exec(statement)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = {
            "user_id": user.user_id,
            "username": user.username
        }

        # Generate new access token
        new_token = create_token(user_data, expiry_delta=access_token_expiry, type="access")

        # Blocklist old refresh token (rotation: prevents reuse)
        await self.add_token_to_blocklist(old_refresh_token_str)

        # Generate new refresh token (rotation)
        new_refresh_token = create_token(user_data, expiry_delta=refresh_token_expiry, type="refresh")
        
        # Return both tokens for dual-auth delivery by route layer
        return {
            "access_token" : new_token,
            "refresh_token": new_refresh_token
        }
    
    async def add_token_to_blocklist(self, token):
        """Revokes token by adding to Redis blocklist.
        
        Args:
            token: JWT token string to revoke.
        """
        token_decoded = decode_token(token)
        token_id = token_decoded.get('jti')  # Unique token identifier
        exp_timestamp = token_decoded.get('exp')

        # Calculate TTL: Only blocklist until natural expiry
        current_time = datetime.now(timezone.utc).timestamp()
        time_to_live = int(exp_timestamp - current_time)

        # Only blocklist if token hasn't expired yet
        if time_to_live > 0:
            await redis_client.setex(name=token_id, time=time_to_live, value="true")
        
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Checks if token is revoked.
        
        Args:
            jti: JWT ID (unique token identifier).
            
        Returns:
            True if token is blocklisted, False otherwise.
        """
        result = await redis_client.get(jti)
        return result is not None
    

    async def logout(
            self,
    request: Request,
    response: Response,
    logout_input: LogoutInput,
    bearer_token: HTTPAuthorizationCredentials,
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
        
        # Dual-auth: Extract tokens from bearer/body (mobile) or cookies (web)
        if bearer_token:
            # Mobile client: Access token in header, refresh token in body
            access_token = bearer_token.credentials
            refresh_token = logout_input.refresh_token
        
        else:
            # Web client: Both tokens in cookies
            access_token = request.cookies.get("access_token")
            refresh_token = request.cookies.get("refresh_token")

        if access_token == None and refresh_token == None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token missing"
            )

        # Revoke tokens by adding to Redis blocklist (prevents reuse)
        if access_token:
            await self.add_token_to_blocklist(access_token)
        if refresh_token:
            await self.add_token_to_blocklist(refresh_token)

        # Delete cookies (harmless for mobile, necessary for web)
        response.delete_cookie(key="access_token")
        response.delete_cookie(key="refresh_token")
        
        return {
            "success": True,
            "message": "Logged out successfully",
            "data": {}
        }