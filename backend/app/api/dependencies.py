from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth import verify_token
from app.services.user_service import UserService
from app.models.user import User


security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    token_data = verify_token(token)
    
    user = UserService.get_user_by_email(db, email=token_data["email"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user."""
    return current_user


def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Optional authentication (allows both authenticated and anonymous access)
def get_optional_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User | None:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        token_data = verify_token(credentials.credentials)
        user = UserService.get_user_by_email(db, email=token_data["email"])
        return user if user and user.is_active else None
    except HTTPException:
        return None