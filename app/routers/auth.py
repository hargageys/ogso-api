from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.email import send_registration_email
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, ChangePasswordRequest
from app.schemas.user import UserOut
from app.dependencies import get_current_user
from jose import JWTError
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if body.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Cannot self-register as admin")

    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        status=UserStatus.pending,
        full_name=body.full_name,
    )
    db.add(user)
    await db.commit()
    send_registration_email(user.email, user.full_name or "")
    return {"message": "Registration received. Awaiting admin approval."}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status == UserStatus.pending:
        raise HTTPException(status_code=403, detail="Your account is awaiting admin approval")
    if user.status == UserStatus.suspended:
        raise HTTPException(status_code=403, detail="Your account has been suspended")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access = create_access_token(str(user.id), user.role.value)
    refresh = create_refresh_token(str(user.id))

    response.set_cookie(
        "refresh_token", refresh,
        httponly=True, samesite="lax",
        max_age=7 * 86400,
    )
    return TokenResponse(access_token=access, role=user.role.value)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
        user_id = payload["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access = create_access_token(str(user.id), user.role.value)
    new_refresh = create_refresh_token(str(user.id))
    response.set_cookie("refresh_token", new_refresh, httponly=True, samesite="lax", max_age=7 * 86400)
    return TokenResponse(access_token=access, role=user.role.value)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password updated"}
