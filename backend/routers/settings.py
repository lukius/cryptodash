from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user, get_db
from backend.models.user import User
from backend.repositories.config import ConfigRepository
from backend.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)],
)

_DEFAULT_REFRESH_INTERVAL = 15
_CONFIG_KEY = "refresh_interval_minutes"


@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    config_repo = ConfigRepository(db)
    value = await config_repo.get_int(_CONFIG_KEY)
    if value is None:
        value = _DEFAULT_REFRESH_INTERVAL
    return SettingsResponse(refresh_interval_minutes=value)


@router.put("/")
async def update_settings(
    body: SettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    config_repo = ConfigRepository(db)

    if body.refresh_interval_minutes is None:
        await config_repo.set(_CONFIG_KEY, "")
    else:
        await config_repo.set(_CONFIG_KEY, str(body.refresh_interval_minutes))

    await db.commit()

    scheduler = request.app.state.scheduler
    await scheduler.restart(body.refresh_interval_minutes)

    ws_manager = request.app.state.ws_manager
    await ws_manager.broadcast(
        "settings:updated",
        {
            "key": _CONFIG_KEY,
            "value": str(body.refresh_interval_minutes)
            if body.refresh_interval_minutes is not None
            else None,
        },
    )

    return SettingsResponse(refresh_interval_minutes=body.refresh_interval_minutes)
