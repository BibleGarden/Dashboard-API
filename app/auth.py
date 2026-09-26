"""
Authorization module for Bible API

Supports two levels of protection:
1. Static API key (X-API-Key) - for client applications
2. JWT tokens (Authorization: Bearer) - for administrative operations
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

# Import configuration (config.py is located in app/ and is imported as "config"
# because the app directory is on sys.path when running via FastAPI/Uvicorn).
try:
    from config import (
        API_KEY,
        JWT_SECRET_KEY,
        JWT_ALGORITHM,
        JWT_EXPIRE_HOURS,
        ADMIN_USERNAME,
        ADMIN_PASSWORD_HASH,
    )
except Exception as e:
    raise RuntimeError(
        'Failed to import configuration. Ensure app/config.py is importable and required env vars are set.'
    ) from e

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class Token(BaseModel):
    """Access token model"""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Data from token"""
    username: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Get password hash"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT token
    
    Args:
        data: Data to include in the token
        expires_delta: Token lifetime (default from config)
    
    Returns:
        JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """
    Verify static API key from X-API-Key header
    
    Used for public endpoints (GET requests)
    """
    if api_key is None or api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return True


def verify_api_key_query(api_key: Optional[str] = None) -> bool:
    """
    Verify static API key from query parameter
    
    Used for audio endpoint (browser cannot send custom headers)
    """
    if api_key is None or api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return True


def verify_jwt_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)) -> str:
    """
    Verify JWT token
    
    Used for administrative endpoints (POST/PUT/PATCH/DELETE)
    
    Returns:
        username from token
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user by username and password
    
    Args:
        username: Username
        password: Password
    
    Returns:
        True if authentication is successful
    """
    if username != ADMIN_USERNAME:
        return False
    if not verify_password(password, ADMIN_PASSWORD_HASH):
        return False
    return True


# Dependencies for use in endpoints
RequireAPIKey = Depends(verify_api_key)
RequireJWT = Depends(verify_jwt_token)
