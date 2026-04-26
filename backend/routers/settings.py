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
_TZ_KEY = "preferred_timezone"
_DEFAULT_TIMEZONE = "UTC"


@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    config_repo = ConfigRepository(db)
    raw_interval = await config_repo.get(_CONFIG_KEY)
    if raw_interval is None:
        interval = _DEFAULT_REFRESH_INTERVAL
    elif raw_interval == "":
        interval = None
    else:
        interval = int(raw_interval)
    tz = await config_repo.get(_TZ_KEY) or _DEFAULT_TIMEZONE
    return SettingsResponse(refresh_interval_minutes=interval, preferred_timezone=tz)


@router.put("/")
async def update_settings(
    body: SettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    config_repo = ConfigRepository(db)

    if "refresh_interval_minutes" in body.model_fields_set:
        if body.refresh_interval_minutes is None:
            await config_repo.set(_CONFIG_KEY, "")
        else:
            await config_repo.set(_CONFIG_KEY, str(body.refresh_interval_minutes))

    if "preferred_timezone" in body.model_fields_set and body.preferred_timezone:
        await config_repo.set(_TZ_KEY, body.preferred_timezone)

    await db.commit()

    if "refresh_interval_minutes" in body.model_fields_set:
        scheduler = request.app.state.scheduler
        await scheduler.restart(body.refresh_interval_minutes)

    ws_manager = request.app.state.ws_manager
    await ws_manager.broadcast("settings:updated", {"key": "settings", "value": None})

    # Build response using provided values; read back others from DB
    if "refresh_interval_minutes" in body.model_fields_set:
        resp_interval = body.refresh_interval_minutes
    else:
        raw = await config_repo.get(_CONFIG_KEY)
        if raw is None:
            resp_interval = _DEFAULT_REFRESH_INTERVAL
        elif raw == "":
            resp_interval = None
        else:
            resp_interval = int(raw)

    resp_tz = body.preferred_timezone if "preferred_timezone" in body.model_fields_set else (
        await config_repo.get(_TZ_KEY) or _DEFAULT_TIMEZONE
    )

    return SettingsResponse(refresh_interval_minutes=resp_interval, preferred_timezone=resp_tz)
