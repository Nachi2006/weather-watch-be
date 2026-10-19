import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import bcrypt
import jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from db.models import UserModel

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "weather-watch-disaster-response-jwt-secret-key-2026-secure-32bytes")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
VALID_ROLES = ["Admin", "Rescue Team", "User"]

def normalize_role(role_input: Optional[str]) -> str:
    if not role_input:
        return "User"
    cleaned = role_input.strip().lower()
    if cleaned in ["admin", "admins"]:
        return "Admin"
    elif cleaned in ["rescue team", "rescueteam", "rescue_team", "rescue"]:
        return "Rescue Team"
    elif cleaned in ["user", "users"]:
        return "User"
    else:
        for role in VALID_ROLES:
            if role.lower() == cleaned:
                return role
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{role_input}'. Allowed roles: {', '.join(VALID_ROLES)}"
        )

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.id == user_id).first()

def get_all_users(db: Session) -> List[UserModel]:
    return db.query(UserModel).all()

def create_user(db: Session, user_data: dict) -> UserModel:
    username = user_data["username"].strip()
    email = user_data["email"].strip().lower()

    if get_user_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{username}' already exists."
        )

    if get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{email}' is already registered."
        )

    role = normalize_role(user_data.get("role", "User"))
    hashed_pwd = hash_password(user_data["password"])

    new_user = UserModel(
        username=username,
        email=email,
        hashed_password=hashed_pwd,
        role=role,
        full_name=user_data.get("full_name")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[UserModel]:
    user = get_user_by_username(db, username_or_email)
    if not user:
        user = get_user_by_email(db, username_or_email.lower())
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def seed_default_users(db: Session):
    defaults = [
        {
            "username": "admin",
            "email": "admin@weatherwatch.org",
            "password": "AdminPassword123!",
            "role": "Admin",
            "full_name": "System Administrator"
        },
        {
            "username": "rescueteam",
            "email": "rescue@weatherwatch.org",
            "password": "RescuePassword123!",
            "role": "Rescue Team",
            "full_name": "Disaster Response Unit"
        },
        {
            "username": "citizen",
            "email": "user@weatherwatch.org",
            "password": "UserPassword123!",
            "role": "User",
            "full_name": "Local Citizen"
        }
    ]

    for user_info in defaults:
        existing = db.query(UserModel).filter(
            (UserModel.username == user_info["username"]) | (UserModel.email == user_info["email"])
        ).first()
        if not existing:
            new_user = UserModel(
                username=user_info["username"],
                email=user_info["email"],
                hashed_password=hash_password(user_info["password"]),
                role=user_info["role"],
                full_name=user_info["full_name"]
            )
            db.add(new_user)
    db.commit()
