import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import (
    get_current_user,
    get_db,
    get_history_service,
    get_refresh_service,
)
from backend.utils import utc_isoformat
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
    DerivedAddressResponse,
    TransactionPage,
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
    derived: list[DerivedAddressResponse] | None = None
    raw_derived = d.get("derived_addresses")
    if raw_derived is not None:
        derived = [
            DerivedAddressResponse(
                address=a["address"],
                balance_native=a["balance_native"],
                balance_usd=a.get("balance_usd"),
            )
            for a in raw_derived
        ]
    return WalletResponse(
        id=d["id"],
        network=d["network"],
        address=d["address"],
        tag=d["tag"],
        wallet_type=d.get("wallet_type", "individual"),
        extended_key_type=d.get("extended_key_type"),
        balance=d["balance"],
        balance_usd=d["balance_usd"],
        created_at=d["created_at"],
        last_updated=d["last_updated"],
        warning=d["warning"],
        history_status=d["history_status"],
        derived_addresses=derived,
        derived_address_count=d.get("derived_address_count"),
        derived_address_total=d.get("derived_address_total"),
        hd_loading=d.get("hd_loading", False),
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
    refresh_service=Depends(get_refresh_service),
    history_service=Depends(get_history_service),
) -> WalletResponse:
    service = WalletService(
        db=db,
        user=current_user,
        refresh_service=refresh_service,
        history_service=history_service,
    )
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
    wallet_type = getattr(wallet, "wallet_type", "individual")
    return WalletResponse(
        id=wallet.id,
        network=wallet.network,
        address=wallet.address,
        tag=wallet.tag,
        wallet_type=wallet_type,
        extended_key_type=getattr(wallet, "extended_key_type", None),
        balance=None,
        balance_usd=None,
        created_at=utc_isoformat(wallet.created_at),
        last_updated=None,
        warning=None,
        history_status="pending",
        derived_addresses=None,
        derived_address_count=None,
        derived_address_total=None,
        hd_loading=wallet_type == "hd",
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
        wallet_type=getattr(wallet, "wallet_type", "individual"),
        extended_key_type=getattr(wallet, "extended_key_type", None),
        balance=None,
        balance_usd=None,
        created_at=utc_isoformat(wallet.created_at),
        last_updated=None,
        warning=None,
        history_status="pending",
        derived_addresses=None,
        derived_address_count=None,
        derived_address_total=None,
        hd_loading=False,
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
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionPage:
    wallet_repo = WalletRepository(db)
    wallet = await wallet_repo.get_by_id(wallet_id, current_user.id)
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found.",
        )
    tx_repo = TransactionRepository(db)
    offset = (page - 1) * page_size
    transactions, total = await tx_repo.list_by_wallet_paginated(
        wallet_id, page_size, offset
    )
    total_pages = max(1, math.ceil(total / page_size))
    return TransactionPage(
        transactions=[
            TransactionResponse(
                id=tx.id,
                tx_hash=tx.tx_hash,
                amount=tx.amount,
                balance_after=tx.balance_after,
                block_height=tx.block_height,
                timestamp=utc_isoformat(tx.timestamp),
            )
            for tx in transactions
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


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
