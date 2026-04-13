"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_sessions_token", "sessions", ["token"], unique=True)

    op.create_table(
        "wallets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("network", sa.String(3), nullable=False),
        sa.Column("address", sa.String(128), nullable=False),
        sa.Column("tag", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint(
            "user_id", "network", "address", name="uq_wallet_network_address"
        ),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wallet_id",
            sa.String(36),
            sa.ForeignKey("wallets.id"),
            nullable=False,
        ),
        sa.Column("tx_hash", sa.String(128), nullable=False),
        sa.Column("amount", sa.String(40), nullable=False),
        sa.Column("balance_after", sa.String(40), nullable=True),
        sa.Column("block_height", sa.Integer, nullable=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("wallet_id", "tx_hash", name="uq_tx_wallet_hash"),
    )
    op.create_index(
        "ix_tx_wallet_height", "transactions", ["wallet_id", "block_height"]
    )

    op.create_table(
        "balance_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wallet_id",
            sa.String(36),
            sa.ForeignKey("wallets.id"),
            nullable=False,
        ),
        sa.Column("balance", sa.String(40), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
    )
    op.create_index(
        "ix_bs_wallet_timestamp", "balance_snapshots", ["wallet_id", "timestamp"]
    )

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("coin", sa.String(3), nullable=False),
        sa.Column("price_usd", sa.String(40), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
    )
    op.create_index("ix_ps_coin_timestamp", "price_snapshots", ["coin", "timestamp"])

    op.create_table(
        "configuration",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(256), nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("configuration")
    op.drop_index("ix_ps_coin_timestamp", table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.drop_index("ix_bs_wallet_timestamp", table_name="balance_snapshots")
    op.drop_table("balance_snapshots")
    op.drop_index("ix_tx_wallet_height", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("wallets")
    op.drop_index("ix_sessions_token", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
