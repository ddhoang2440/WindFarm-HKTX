"""
AuthController – class diagram: + login()
Routes: POST /api/auth/login, POST /api/auth/register, GET /api/auth/me
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

from src.modules.Auth import auth_service
from src.modules.Auth.auth_dto import (
    LoginDTO,
    RegisterDTO,
    TokenResponseDTO,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.post(
    "/login",
    response_model=TokenResponseDTO,
    summary="AuthController.login()",
)
async def login(body: LoginDTO):
    """login() – diagram method."""
    token = await auth_service.login_user(body.email, body.password)
    return TokenResponseDTO(access_token=token)


@router.post("/register", status_code=201)
async def register(body: RegisterDTO):
    user = await auth_service.register_user(
        body.email, body.password, body.full_name
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "status": user.status.value,
        "message": "Account created. Awaiting admin approval.",
    }


@router.get("/me")
async def me(token: str = Depends(oauth2_scheme)):
    user = await auth_service.get_current_user(token)
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
    }