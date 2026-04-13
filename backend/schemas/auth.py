from pydantic import BaseModel, Field, model_validator


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8)
    password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> "SetupRequest":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    token: str
    expires_at: str  # ISO 8601


class AuthStatusResponse(BaseModel):
    account_exists: bool
    authenticated: bool
    username: str | None = None
