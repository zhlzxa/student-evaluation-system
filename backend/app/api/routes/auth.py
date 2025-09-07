from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import (
    Token, UserCreate, User as UserSchema, 
    LoginRequest, RegisterRequest
)
from app.services.user_service import UserService
from app.services.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.api.dependencies import get_current_active_user


router = APIRouter()


@router.post("/register", response_model=Token)
def register_user(
    user_data: RegisterRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Register a new user."""
    user_create = UserCreate(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    user = UserService.create_user(db, user_create)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserSchema.model_validate(user)
    }


@router.post("/login", response_model=Token)
def login_user(
    login_data: LoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Login user."""
    user = UserService.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserSchema.model_validate(user)
    }


# OAuth2 compatible endpoint for form-based login
@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    """OAuth2 compatible token endpoint."""
    user = UserService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserSchema.model_validate(user)
    }


@router.get("/me", response_model=UserSchema)
def read_users_me(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)]
):
    """Get current user."""
    return current_user


@router.post("/guest", response_model=Token)
def create_guest_user(
    db: Annotated[Session, Depends(get_db)]
):
    """Create a guest user for demo purposes."""
    from datetime import datetime
    import uuid
    
    # Create a temporary guest user
    guest_email = f"guest-{uuid.uuid4().hex[:8]}@example.com"
    guest_password = "guest-password"
    
    user_create = UserCreate(
        email=guest_email,
        password=guest_password,
        full_name="Guest User",
        is_active=True
    )
    
    user = UserService.create_user(db, user_create)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserSchema.model_validate(user)
    }