from pydantic import BaseModel, Field, field_validator

_MAX_TZ_LEN = 64


class SettingsResponse(BaseModel):
    refresh_interval_minutes: int | None
    preferred_timezone: str


class SettingsUpdate(BaseModel):
    refresh_interval_minutes: int | None = Field(None)
    preferred_timezone: str | None = Field(None)

    @field_validator("refresh_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v not in (5, 15, 30, 60):
            raise ValueError(
                "Refresh interval must be 5, 15, 30, or 60 minutes, or null to disable."
            )
        return v

    @field_validator("preferred_timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError("Timezone must not be blank.")
            if len(v) > _MAX_TZ_LEN:
                raise ValueError(f"Timezone must be at most {_MAX_TZ_LEN} characters.")
        return v
