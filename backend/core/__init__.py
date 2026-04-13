from backend.core.dependencies import (
    bearer_scheme,
    get_auth_token,
    get_current_user,
    get_db,
)
from backend.core.exceptions import (
    AccountExistsError,
    AddressValidationError,
    CryptoDashError,
    DuplicateWalletError,
    ExternalAPIError,
    InvalidCredentialsError,
    InvalidSessionError,
    RateLimitedError,
    TagValidationError,
    WalletLimitReachedError,
    WalletNotFoundError,
)
from backend.core.scheduler import Scheduler
from backend.core.security import generate_token, hash_password, verify_password
from backend.core.websocket_manager import ConnectionManager

__all__ = [
    "bearer_scheme",
    "get_auth_token",
    "get_current_user",
    "get_db",
    "AccountExistsError",
    "AddressValidationError",
    "CryptoDashError",
    "DuplicateWalletError",
    "ExternalAPIError",
    "InvalidCredentialsError",
    "InvalidSessionError",
    "RateLimitedError",
    "TagValidationError",
    "WalletLimitReachedError",
    "WalletNotFoundError",
    "Scheduler",
    "generate_token",
    "hash_password",
    "verify_password",
    "ConnectionManager",
]
