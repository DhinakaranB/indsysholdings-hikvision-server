# backend/services/auth_service.py

from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# 1. UNCOMMENT THIS (Required for settings.JWT_SECRET_KEY)
from app.backend.config import settings 

# 2. REMOVED the self-import (It was causing a loop)

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    disabled: bool = False

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """Dependency that verifies the JWT token from the header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return verify_access_token(token, credentials_exception)