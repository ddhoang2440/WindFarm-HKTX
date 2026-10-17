from src.core.dependencies import require_admin
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

from src.modules.Settings import settings_service
from src.modules.Settings.settings_dto import UpdateSettingsDTO
from src.models.User import User

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.get("/")
async def get_settings(admin: User = Depends(require_admin)):
    """Get all settings (secrets masked)."""
    return await settings_service.get_settings_data()


@router.put("/")
async def update_settings(
    body: UpdateSettingsDTO,
    admin: User = Depends(require_admin),
):
    """Update settings (Admin only)."""
    return await settings_service.update_settings_data(body, str(admin.id))