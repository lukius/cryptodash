class GhostStackError(Exception):
    """Base exception for all application errors."""

    pass


class AccountExistsError(GhostStackError): ...


class AccountNotFoundError(GhostStackError): ...


class InvalidCredentialsError(GhostStackError): ...


class RateLimitedError(GhostStackError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(
            f"Too many failed attempts. Please wait {retry_after} seconds."
        )


class InvalidSessionError(GhostStackError): ...


class AddressValidationError(GhostStackError): ...


class ExtendedKeyValidationError(AddressValidationError):
    """Raised for xpub/ypub/zpub format errors.

    Subclasses AddressValidationError so the existing 400 handler catches it
    without modification.
    """


class DuplicateWalletError(GhostStackError): ...


class WalletLimitReachedError(GhostStackError): ...


class TagValidationError(GhostStackError): ...


class WalletNotFoundError(GhostStackError): ...


class ExternalAPIError(GhostStackError): ...
