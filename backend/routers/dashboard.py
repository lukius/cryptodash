import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user, get_db
from backend.models.user import User
from backend.repositories.snapshot import (
    BalanceSnapshotRepository,
    PriceSnapshotRepository,
)
from backend.repositories.wallet import WalletRepository
from backend.schemas.dashboard import (
    CompositionSegment,
    HistoryDataPoint,
    PortfolioComposition,
    PortfolioHistoryResponse,
    PortfolioSummary,
    PriceHistoryResponse,
    WalletHistoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)

_RANGE_DAYS: dict[str, int | None] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
    "all": None,
}


def _range_start(range_param: str) -> datetime | None:
    days = _RANGE_DAYS.get(range_param)
    if days is None:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/summary")
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioSummary:
    wallet_repo = WalletRepository(db)
    snap_repo = BalanceSnapshotRepository(db)
    price_repo = PriceSnapshotRepository(db)

    wallets = await wallet_repo.list_all(current_user.id)

    btc_price_snap = await price_repo.get_latest("BTC")
    kas_price_snap = await price_repo.get_latest("KAS")

    btc_price = Decimal(btc_price_snap.price_usd) if btc_price_snap else None
    kas_price = Decimal(kas_price_snap.price_usd) if kas_price_snap else None

    total_btc = Decimal("0")
    total_kas = Decimal("0")
    last_updated: datetime | None = None

    for wallet in wallets:
        snap = await snap_repo.get_latest_for_wallet(wallet.id)
        if snap is None:
            continue
        balance = Decimal(snap.balance)
        if wallet.network == "BTC":
            total_btc += balance
        elif wallet.network == "KAS":
            total_kas += balance
        if last_updated is None or snap.timestamp > last_updated:
            last_updated = snap.timestamp

    btc_value_usd = (total_btc * btc_price) if btc_price is not None else None
    kas_value_usd = (total_kas * kas_price) if kas_price is not None else None

    if btc_value_usd is not None or kas_value_usd is not None:
        total_value_usd = (btc_value_usd or Decimal("0")) + (
            kas_value_usd or Decimal("0")
        )
    else:
        total_value_usd = None

    # 24h change: find portfolio value ~24h ago
    change_24h_usd: Decimal | None = None
    change_24h_pct: Decimal | None = None

    if total_value_usd is not None and wallets:
        target_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        old_btc = Decimal("0")
        old_kas = Decimal("0")
        found_any = False

        for wallet in wallets:
            old_snap = await snap_repo.get_nearest_before(wallet.id, target_24h)
            if old_snap is not None:
                found_any = True
                bal = Decimal(old_snap.balance)
                if wallet.network == "BTC":
                    old_btc += bal
                elif wallet.network == "KAS":
                    old_kas += bal

        if found_any:
            old_btc_price_snap = await price_repo.get_nearest_before("BTC", target_24h)
            old_kas_price_snap = await price_repo.get_nearest_before("KAS", target_24h)
            old_btc_price = (
                Decimal(old_btc_price_snap.price_usd)
                if old_btc_price_snap is not None
                else btc_price
            )
            old_kas_price = (
                Decimal(old_kas_price_snap.price_usd)
                if old_kas_price_snap is not None
                else kas_price
            )
            old_btc_val = (
                (old_btc * old_btc_price) if old_btc_price is not None else Decimal("0")
            )
            old_kas_val = (
                (old_kas * old_kas_price) if old_kas_price is not None else Decimal("0")
            )
            old_total = old_btc_val + old_kas_val
            change_24h_usd = total_value_usd - old_total
            if old_total != Decimal("0"):
                change_24h_pct = (change_24h_usd / old_total) * Decimal("100")

    return PortfolioSummary(
        total_value_usd=str(total_value_usd) if total_value_usd is not None else None,
        total_btc=str(total_btc),
        total_kas=str(total_kas),
        btc_value_usd=str(btc_value_usd) if btc_value_usd is not None else None,
        kas_value_usd=str(kas_value_usd) if kas_value_usd is not None else None,
        change_24h_usd=str(change_24h_usd) if change_24h_usd is not None else None,
        change_24h_pct=str(change_24h_pct) if change_24h_pct is not None else None,
        btc_price_usd=str(btc_price) if btc_price is not None else None,
        kas_price_usd=str(kas_price) if kas_price is not None else None,
        last_updated=last_updated.isoformat() if last_updated is not None else None,
    )


@router.get("/portfolio-history")
async def get_portfolio_history(
    range: str = Query("30d"),
    unit: str = Query("usd"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioHistoryResponse:
    if range not in _RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid range. Must be one of: {', '.join(_RANGE_DAYS)}",
        )
    if unit not in ("usd", "btc", "kas"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid unit. Must be one of: usd, btc, kas",
        )

    wallet_repo = WalletRepository(db)
    snap_repo = BalanceSnapshotRepository(db)
    price_repo = PriceSnapshotRepository(db)

    wallets = await wallet_repo.list_all(current_user.id)

    start = _range_start(range)
    now = datetime.now(timezone.utc)
    # Extend end to 23:59:59 of today so that historical end-of-day snapshots
    # (stored at HH=23, MM=59, SS=59) are included in the query window.
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Gather all balance snapshots per wallet in range
    # We build a unified timeline: bucket by timestamp, sum per timestamp key
    # Strategy: collect all snapshots, sort by time, aggregate per wallet at each point
    all_snapshots: list[tuple[datetime, str, Decimal]] = []  # (ts, wallet_id, balance)

    for wallet in wallets:
        snaps = await snap_repo.get_range(
            wallet.id, start or datetime.min.replace(tzinfo=timezone.utc), end
        )
        for snap in snaps:
            ts = snap.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            all_snapshots.append((ts, wallet.id, Decimal(snap.balance)))

    if not all_snapshots:
        return PortfolioHistoryResponse(data_points=[], range=range, unit=unit)

    # Group by timestamp (exact match). For portfolio history use a per-point approach.
    # For each unique timestamp, get all wallet balances at that point and compute USD value.
    unique_timestamps = sorted({ts for ts, _, _ in all_snapshots})

    data_points: list[HistoryDataPoint] = []

    for ts in unique_timestamps:
        # Get the balance for each wallet at this timestamp (nearest-before or exact)
        total_value = Decimal("0")
        has_value = False

        for wallet in wallets:
            bal_snap = await snap_repo.get_nearest_before(wallet.id, ts)
            if bal_snap is None:
                continue
            balance = Decimal(bal_snap.balance)

            price_snap = await price_repo.get_nearest_before(wallet.network, ts)
            if price_snap is None:
                continue
            price = Decimal(price_snap.price_usd)

            total_value += balance * price
            has_value = True

        if has_value:
            display_value = total_value
            if unit == "btc":
                btc_snap = await price_repo.get_nearest_before("BTC", ts)
                if btc_snap is None or Decimal(btc_snap.price_usd) == 0:
                    continue
                display_value = total_value / Decimal(btc_snap.price_usd)
            elif unit == "kas":
                kas_snap = await price_repo.get_nearest_before("KAS", ts)
                if kas_snap is None or Decimal(kas_snap.price_usd) == 0:
                    continue
                display_value = total_value / Decimal(kas_snap.price_usd)
            data_points.append(
                HistoryDataPoint(
                    timestamp=ts.isoformat(),
                    value=str(display_value),
                )
            )

    return PortfolioHistoryResponse(data_points=data_points, range=range, unit=unit)


@router.get("/wallet-history/{wallet_id}")
async def get_wallet_history(
    wallet_id: str,
    range: str = Query("30d"),
    unit: str = Query("usd"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletHistoryResponse:
    if range not in _RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid range. Must be one of: {', '.join(_RANGE_DAYS)}",
        )

    wallet_repo = WalletRepository(db)
    snap_repo = BalanceSnapshotRepository(db)
    price_repo = PriceSnapshotRepository(db)

    wallet = await wallet_repo.get_by_id(wallet_id, current_user.id)
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found."
        )

    start = _range_start(range)
    now = datetime.now(timezone.utc)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    snaps = await snap_repo.get_range(
        wallet_id, start or datetime.min.replace(tzinfo=timezone.utc), end
    )

    data_points: list[HistoryDataPoint] = []
    for snap in snaps:
        ts = snap.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        balance = Decimal(snap.balance)

        if unit == "usd":
            price_snap = await price_repo.get_nearest_before(wallet.network, ts)
            if price_snap is None:
                continue
            value = balance * Decimal(price_snap.price_usd)
        else:
            value = balance

        data_points.append(
            HistoryDataPoint(
                timestamp=ts.isoformat(),
                value=str(value),
            )
        )

    return WalletHistoryResponse(
        wallet_id=wallet_id,
        data_points=data_points,
        range=range,
        unit=unit,
    )


@router.get("/price-history")
async def get_price_history(
    range: str = Query("30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PriceHistoryResponse:
    if range not in _RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid range. Must be one of: {', '.join(_RANGE_DAYS)}",
        )

    price_repo = PriceSnapshotRepository(db)
    start = _range_start(range)
    now = datetime.now(timezone.utc)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    btc_snaps = await price_repo.get_range(
        "BTC", start or datetime.min.replace(tzinfo=timezone.utc), end
    )
    kas_snaps = await price_repo.get_range(
        "KAS", start or datetime.min.replace(tzinfo=timezone.utc), end
    )

    def to_data_points(snaps) -> list[HistoryDataPoint]:
        result = []
        for snap in snaps:
            ts = snap.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            result.append(
                HistoryDataPoint(
                    timestamp=ts.isoformat(),
                    value=snap.price_usd,
                )
            )
        return result

    return PriceHistoryResponse(
        btc=to_data_points(btc_snaps),
        kas=to_data_points(kas_snaps),
        range=range,
    )


@router.get("/composition")
async def get_composition(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioComposition:
    wallet_repo = WalletRepository(db)
    snap_repo = BalanceSnapshotRepository(db)
    price_repo = PriceSnapshotRepository(db)

    wallets = await wallet_repo.list_all(current_user.id)
    if not wallets:
        return PortfolioComposition(segments=[])

    network_values: dict[str, Decimal] = {}

    for wallet in wallets:
        snap = await snap_repo.get_latest_for_wallet(wallet.id)
        if snap is None:
            continue
        price_snap = await price_repo.get_latest(wallet.network)
        if price_snap is None:
            continue

        balance = Decimal(snap.balance)
        price = Decimal(price_snap.price_usd)
        value = balance * price
        network_values[wallet.network] = (
            network_values.get(wallet.network, Decimal("0")) + value
        )

    if not network_values:
        return PortfolioComposition(segments=[])

    total = sum(network_values.values())
    segments: list[CompositionSegment] = []

    for network, value in network_values.items():
        pct = (value / total * Decimal("100")) if total > Decimal("0") else Decimal("0")
        segments.append(
            CompositionSegment(
                network=network,
                value_usd=str(value),
                percentage=str(pct.quantize(Decimal("0.1"))),
            )
        )

    return PortfolioComposition(segments=segments)


@router.post("/refresh")
async def trigger_refresh(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict:
    from backend.services.refresh import RefreshResult

    refresh_service = request.app.state.refresh_service
    result: RefreshResult = await refresh_service.run_full_refresh()

    response_data = {
        "skipped": result.skipped,
        "success_count": result.success_count,
        "failure_count": result.failure_count,
        "errors": result.errors,
        "timestamp": result.timestamp.isoformat(),
    }

    if result.skipped:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response_data)

    return response_data
