"""
Shared FastAPI dependencies (auth, role checks).
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from src.modules.Auth.auth_service import get_current_user
from src.models.User import User, UserRole
from src.core.exceptions import ForbiddenException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user_dep(
    token: str = Depends(oauth2_scheme),
) -> User:
    return await get_current_user(token)


async def require_admin(
    user: User = Depends(get_current_user_dep),
) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenException("Admin access required")
    return user


async def require_engineer_or_admin(
    user: User = Depends(get_current_user_dep),
) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.ENGINEER):
        raise ForbiddenException("Engineer or Admin access required")
    return user