from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user, get_db
from backend.core.exceptions import (
    AddressValidationError,
    DuplicateWalletError,
    TagValidationError,
    WalletLimitReachedError,
    WalletNotFoundError,
)
from backend.models.user import User
from backend.repositories.transaction import TransactionRepository
from backend.repositories.wallet import WalletRepository
from backend.schemas.wallet import (
    TransactionResponse,
    WalletCreate,
    WalletListResponse,
    WalletResponse,
    WalletTagUpdate,
)
from backend.services.wallet import WalletService

router = APIRouter(
    prefix="/api/wallets",
    tags=["wallets"],
    dependencies=[Depends(get_current_user)],
)


def _wallet_dict_to_response(d: dict) -> WalletResponse:
    return WalletResponse(
        id=d["id"],
        network=d["network"],
        address=d["address"],
        tag=d["tag"],
        balance=d["balance"],
        balance_usd=d["balance_usd"],
        created_at=d["created_at"],
        last_updated=d["last_updated"],
        warning=d["warning"],
        history_status=d["history_status"],
    )


@router.get("/")
async def list_wallets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletListResponse:
    service = WalletService(db=db, user=current_user)
    wallets = await service.list_wallets()
    return WalletListResponse(
        wallets=[_wallet_dict_to_response(w) for w in wallets],
        count=len(wallets),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_wallet(
    body: WalletCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    service = WalletService(db=db, user=current_user)
    try:
        wallet = await service.add_wallet(body.network, body.address, body.tag)
    except WalletLimitReachedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except (AddressValidationError, DuplicateWalletError, TagValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    await db.commit()
    return WalletResponse(
        id=wallet.id,
        network=wallet.network,
        address=wallet.address,
        tag=wallet.tag,
        balance=None,
        balance_usd=None,
        created_at=wallet.created_at.isoformat(),
        last_updated=None,
        warning=None,
        history_status="pending",
    )


@router.patch("/{wallet_id}")
async def update_wallet_tag(
    wallet_id: str,
    body: WalletTagUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    service = WalletService(db=db, user=current_user)
    try:
        wallet = await service.update_tag(wallet_id, body.tag)
    except WalletNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found.",
        )
    except TagValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    await db.commit()
    return WalletResponse(
        id=wallet.id,
        network=wallet.network,
        address=wallet.address,
        tag=wallet.tag,
        balance=None,
        balance_usd=None,
        created_at=wallet.created_at.isoformat(),
        last_updated=None,
        warning=None,
        history_status="pending",
    )


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = WalletService(db=db, user=current_user)
    try:
        await service.remove_wallet(wallet_id)
    except WalletNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found.",
        )
    await db.commit()


@router.get("/{wallet_id}/transactions")
async def list_transactions(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TransactionResponse]:
    wallet_repo = WalletRepository(db)
    wallet = await wallet_repo.get_by_id(wallet_id, current_user.id)
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found.",
        )
    tx_repo = TransactionRepository(db)
    transactions = await tx_repo.list_by_wallet(wallet_id)
    return [
        TransactionResponse(
            id=tx.id,
            tx_hash=tx.tx_hash,
            amount=tx.amount,
            balance_after=tx.balance_after,
            block_height=tx.block_height,
            timestamp=tx.timestamp.isoformat(),
        )
        for tx in transactions
    ]


@router.post("/{wallet_id}/retry-history")
async def retry_history_import(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = WalletService(db=db, user=current_user)
    try:
        await service.retry_history_import(wallet_id)
    except WalletNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found.",
        )
    return {"ok": True, "message": "History import started."}
