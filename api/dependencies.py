from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from database import Database
from auth import AuthManager
from recommender import RecommenderSystem
from api.security import decode_access_token


_db = Database()
_auth_manager = AuthManager(_db)
_recommender = RecommenderSystem(_db)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db() -> Database:
    return _db


def get_auth_manager() -> AuthManager:
    return _auth_manager


def get_recommender() -> RecommenderSystem:
    return _recommender


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """برای اندپوینت‌هایی که لاگین اجباریه."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    return {"user_id": int(payload["sub"]), "username": payload["username"]}


def get_optional_user(token: str = Depends(oauth2_scheme)) -> dict | None:
    
    if token is None:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    return {"user_id": int(payload["sub"]), "username": payload["username"]}
