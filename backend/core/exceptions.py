class CryptoDashError(Exception):
    """Base exception for all application errors."""

    pass


class AccountExistsError(CryptoDashError): ...


class AccountNotFoundError(CryptoDashError): ...


class InvalidCredentialsError(CryptoDashError): ...


class RateLimitedError(CryptoDashError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(
            f"Too many failed attempts. Please wait {retry_after} seconds."
        )


class InvalidSessionError(CryptoDashError): ...


class AddressValidationError(CryptoDashError): ...


class ExtendedKeyValidationError(AddressValidationError):
    """Raised for xpub/ypub/zpub format errors.

    Subclasses AddressValidationError so the existing 400 handler catches it
    without modification.
    """


class DuplicateWalletError(CryptoDashError): ...


class WalletLimitReachedError(CryptoDashError): ...


class TagValidationError(CryptoDashError): ...


class WalletNotFoundError(CryptoDashError): ...


class ExternalAPIError(CryptoDashError): ...
