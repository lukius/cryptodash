from pydantic import BaseModel, Field, field_validator


class SettingsResponse(BaseModel):
    refresh_interval_minutes: int | None


class SettingsUpdate(BaseModel):
    refresh_interval_minutes: int | None = Field(None)

    @field_validator("refresh_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v not in (5, 15, 30, 60):
            raise ValueError(
                "Refresh interval must be 5, 15, 30, or 60 minutes, or null to disable."
            )
        return v
