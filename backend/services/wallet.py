import asyncio
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import (
    AddressValidationError,
    DuplicateWalletError,
    TagValidationError,
    WalletLimitReachedError,
    WalletNotFoundError,
)
from backend.models.user import User
from backend.models.wallet import Wallet
from backend.repositories.snapshot import (
    BalanceSnapshotRepository,
    PriceSnapshotRepository,
)
from backend.repositories.wallet import WalletRepository

logger = logging.getLogger(__name__)


def validate_btc_address(address: str) -> str | None:
    """Returns None if valid, error message string if invalid."""
    address = address.strip().replace("\n", "").replace(" ", "")

    # P2PKH (Legacy) — starts with '1'
    if address.startswith("1"):
        if 25 <= len(address) <= 34 and re.fullmatch(
            r"[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+", address
        ):
            return None
        return "Invalid Bitcoin address format."

    # P2SH — starts with '3'
    if address.startswith("3"):
        if 25 <= len(address) <= 34 and re.fullmatch(
            r"[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+", address
        ):
            return None
        return "Invalid Bitcoin address format."

    # Bech32 SegWit v0 — starts with 'bc1q'
    if address.lower().startswith("bc1q"):
        address = address.lower()
        bech32_chars = r"[023456789acdefghjklmnpqrstuvwxyz]"
        if len(address) in (42, 62) and re.fullmatch(f"bc1q{bech32_chars}+", address):
            return None
        return "Invalid Bitcoin address format."

    # Bech32m Taproot — starts with 'bc1p'
    if address.lower().startswith("bc1p"):
        address = address.lower()
        bech32_chars = r"[023456789acdefghjklmnpqrstuvwxyz]"
        if len(address) == 62 and re.fullmatch(f"bc1p{bech32_chars}+", address):
            return None
        return "Invalid Bitcoin address format."

    return "Invalid Bitcoin address format."


def validate_kas_address(address: str) -> str | None:
    """Returns None if valid, error message string if invalid."""
    address = address.strip().replace("\n", "").replace(" ", "")

    if not address.startswith("kaspa:"):
        return "Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'."

    remainder = address[6:]  # after "kaspa:"
    bech32_chars = r"[023456789acdefghjklmnpqrstuvwxyz]"
    if 60 <= len(remainder) <= 63 and re.fullmatch(bech32_chars + "+", remainder):
        return None

    return "Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'."


class WalletService:
    MAX_WALLETS = 50

    def __init__(
        self,
        db: AsyncSession,
        user: User,
        refresh_service=None,
        history_service=None,
        ws_manager=None,
    ) -> None:
        self.db = db
        self.user = user
        self.refresh_service = refresh_service
        self.history_service = history_service
        self.ws_manager = ws_manager
        self.wallet_repo = WalletRepository(db)
        self.balance_repo = BalanceSnapshotRepository(db)
        self.price_repo = PriceSnapshotRepository(db)

    async def list_wallets(self) -> list[dict]:
        wallets = await self.wallet_repo.list_all(self.user.id)
        result = []
        for wallet in wallets:
            balance_snap = await self.balance_repo.get_latest_for_wallet(wallet.id)
            price_snap = await self.price_repo.get_latest(wallet.network)

            balance: str | None = None
            balance_usd: str | None = None
            last_updated: str | None = None

            if balance_snap is not None:
                balance = str(balance_snap.balance)
                last_updated = balance_snap.timestamp.isoformat()
                if price_snap is not None and price_snap.price_usd is not None:
                    balance_usd = str(
                        Decimal(str(balance_snap.balance))
                        * Decimal(str(price_snap.price_usd))
                    )

            history_status = "complete" if balance_snap is not None else "pending"

            result.append(
                {
                    "id": wallet.id,
                    "network": wallet.network,
                    "address": wallet.address,
                    "tag": wallet.tag,
                    "balance": balance,
                    "balance_usd": balance_usd,
                    "created_at": wallet.created_at.isoformat(),
                    "last_updated": last_updated,
                    "warning": None,
                    "history_status": history_status,
                }
            )
        return result

    async def add_wallet(self, network: str, address: str, tag: str | None) -> Wallet:
        # 1. Check wallet limit
        count = await self.wallet_repo.count_by_user(self.user.id)
        if count >= self.MAX_WALLETS:
            raise WalletLimitReachedError(
                "Wallet limit reached (50). Remove a wallet to add a new one."
            )

        # 2. Normalize address
        address = address.strip().replace("\n", "").replace(" ", "")

        # 3. Validate address format
        if network == "BTC":
            error = validate_btc_address(address)
        elif network == "KAS":
            error = validate_kas_address(address)
        else:
            raise ValueError(f"Unsupported network: {network}")
        if error:
            raise AddressValidationError(error)

        # 4. Check duplicate (BTC case-insensitive, KAS exact)
        normalized = address.lower() if network == "BTC" else address
        exists = await self.wallet_repo.exists_by_address(
            self.user.id, network, normalized
        )
        if exists:
            raise DuplicateWalletError("This wallet address is already being tracked.")

        # 5. Handle tag
        if not tag or not tag.strip():
            tag = await self._generate_default_tag(network)
        else:
            tag = tag.strip()
            if len(tag) > 50:
                raise TagValidationError("Tag must be 50 characters or fewer.")
            if await self.wallet_repo.tag_exists(self.user.id, tag):
                raise TagValidationError("A wallet with this tag already exists.")

        # 6. Persist wallet
        wallet = Wallet(
            id=str(uuid4()),
            user_id=self.user.id,
            network=network,
            address=address,
            tag=tag,
            created_at=datetime.now(timezone.utc),
        )
        await self.wallet_repo.create(wallet)

        # 7. Spawn background tasks (non-blocking)
        asyncio.create_task(self._fetch_initial_data(wallet))

        return wallet

    async def update_tag(self, wallet_id: str, new_tag: str) -> Wallet:
        wallet = await self.wallet_repo.get_by_id(wallet_id, self.user.id)
        if wallet is None:
            raise WalletNotFoundError(f"Wallet {wallet_id} not found.")

        new_tag = new_tag.strip()
        if len(new_tag) > 50:
            raise TagValidationError("Tag must be 50 characters or fewer.")
        if await self.wallet_repo.tag_exists(
            self.user.id, new_tag, exclude_wallet_id=wallet_id
        ):
            raise TagValidationError("A wallet with this tag already exists.")

        await self.wallet_repo.update_tag(wallet_id, new_tag)
        wallet.tag = new_tag
        return wallet

    async def remove_wallet(self, wallet_id: str) -> None:
        wallet = await self.wallet_repo.get_by_id(wallet_id, self.user.id)
        if wallet is None:
            raise WalletNotFoundError(f"Wallet {wallet_id} not found.")
        await self.wallet_repo.delete(wallet_id)

    async def retry_history_import(self, wallet_id: str) -> None:
        wallet = await self.wallet_repo.get_by_id(wallet_id, self.user.id)
        if wallet is None:
            raise WalletNotFoundError(f"Wallet {wallet_id} not found.")
        if self.history_service is not None:
            asyncio.create_task(self._run_history_import(wallet))

    async def _generate_default_tag(self, network: str) -> str:
        prefix = "BTC" if network == "BTC" else "KAS"
        n = 1
        while True:
            candidate = f"{prefix} Wallet #{n}"
            exists = await self.wallet_repo.tag_exists(self.user.id, candidate)
            if not exists:
                return candidate
            n += 1

    async def _fetch_initial_data(self, wallet: Wallet) -> None:
        """Fetch current balance + start history import. Runs as background task."""
        if self.refresh_service is not None:
            try:
                await self.refresh_service.refresh_single_wallet(wallet)
            except Exception:
                logger.warning("Could not fetch initial balance for %s", wallet.tag)
        if self.history_service is not None:
            try:
                await self.history_service.full_import(wallet)
            except Exception:
                logger.warning("History import failed for %s", wallet.tag)
        if self.ws_manager is not None:
            try:
                await self.ws_manager.broadcast(
                    "wallet:added", {"wallet_id": wallet.id}
                )
            except Exception:
                logger.warning("WebSocket broadcast failed for %s", wallet.tag)

    async def _run_history_import(self, wallet: Wallet) -> None:
        try:
            await self.history_service.full_import(wallet)
        except Exception:
            logger.warning("History import retry failed for %s", wallet.tag)
