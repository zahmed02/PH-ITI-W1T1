"""
Authentication for the patient portal.

Design notes:
- Passwords are hashed with bcrypt directly (not passlib, to avoid the
  passlib/bcrypt version-compatibility issues that trip up a lot of
  setups).
- Tokens are JWTs (PyJWT) carrying the user id and a "tv" (token_version)
  claim. Logout increments the user's token_version in the DB, which
  immediately invalidates every token issued before that point - so
  logout is a real server-side revocation, not just "the client deletes
  its copy and hopes for the best."
- The frontend is responsible for the *instant* cross-tab UI sync (via a
  localStorage 'storage' event) - this file is what makes that
  server-side, too, so a leaked/old token can't keep working after logout.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import TokenResponse, UserLogin, UserOut, UserRegister

load_dotenv()
logger = logging.getLogger(__name__)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    # Fine for local dev so the app doesn't just crash, but every restart
    # invalidates all existing tokens and it's not safe for production.
    JWT_SECRET_KEY = "insecure-dev-secret-change-me"
    logger.warning(
        "JWT_SECRET_KEY is not set in the environment - using an insecure "
        "default. Add JWT_SECRET_KEY=<a long random string> to your .env "
        "file before deploying this anywhere real."
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# -------------------- password hashing --------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB - treat as a failed login, not a 500.
        return False


# -------------------- JWT --------------------

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "tv": user.token_version,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    if payload.get("tv") != user.token_version:
        # The user (or another tab/device) logged out since this token was
        # issued - reject it even though it hasn't expired yet.
        raise HTTPException(status_code=401, detail="Session has been logged out. Please log in again.")

    return user


# -------------------- routes --------------------

@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(func.lower(User.username) == payload.username.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="That username is already taken.")

    user = User(username=payload.username, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.username) == payload.username.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Deliberately identical message for "no such user" and "wrong
        # password" so login can't be used to enumerate valid usernames.
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(user)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.commit()
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
