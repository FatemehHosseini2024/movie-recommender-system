from fastapi import APIRouter, Depends, HTTPException, status

from auth import AuthManager
from api.schemas import UserRegister, UserLogin, TokenResponse
from api.dependencies import get_auth_manager
from api.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, auth_manager: AuthManager = Depends(get_auth_manager)):
    user_id = auth_manager.register_user(payload.username, payload.password)
    if user_id is None:
        raise HTTPException(status_code=400, detail="this username has already registered")
    token = create_access_token(user_id, payload.username)
    return TokenResponse(access_token=token, user_id=user_id, username=payload.username)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, auth_manager: AuthManager = Depends(get_auth_manager)):
    user_id = auth_manager.login_user(payload.username, payload.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="username or password is wrong")
    token = create_access_token(user_id, payload.username)
    return TokenResponse(access_token=token, user_id=user_id, username=payload.username)
