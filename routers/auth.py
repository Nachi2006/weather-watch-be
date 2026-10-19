from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from db.db import get_db
from db.models import UserModel
from models import UserRegister, UserLogin, Token, UserResponse
from services import auth as auth_service
from services.security import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    new_user = auth_service.create_user(db, user_in.model_dump())
    return new_user

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):

    user = auth_service.authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(data={
        "sub": user.username,
        "username": user.username,
        "role": user.role,
        "email": user.email
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 15 * 60,  
        "role": user.role,
        "username": user.username,
        "email": user.email
    }

@router.post("/token", response_model=Token, include_in_schema=False)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(data={
        "sub": user.username,
        "username": user.username,
        "role": user.role,
        "email": user.email
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 15 * 60,
        "role": user.role,
        "username": user.username,
        "email": user.email
    }

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: UserModel = Depends(get_current_user)):
    return current_user

@router.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: UserModel = Depends(require_admin)):
    return auth_service.get_all_users(db)
