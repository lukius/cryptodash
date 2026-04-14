"""HD wallet support

Revision ID: 002
Revises: 001
Create Date: 2026-04-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add wallet_type to wallets (non-null; server_default classifies existing rows)
    op.add_column(
        "wallets",
        sa.Column(
            "wallet_type",
            sa.String(10),
            nullable=False,
            server_default="individual",
        ),
    )

    # Add extended_key_type to wallets (nullable; None for individual wallets)
    op.add_column(
        "wallets",
        sa.Column("extended_key_type", sa.String(4), nullable=True),
    )

    # Create derived_addresses table
    op.create_table(
        "derived_addresses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wallet_id",
            sa.String(36),
            sa.ForeignKey("wallets.id"),
            nullable=False,
        ),
        sa.Column("address", sa.String(64), nullable=False),
        sa.Column("current_balance_native", sa.String(40), nullable=False),
        sa.Column("balance_sat", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("wallet_id", "address", name="uq_derived_wallet_address"),
    )


def downgrade() -> None:
    # Dropping columns from SQLite requires table rebuilding; not supported here.
    # To downgrade manually: restore the database from a backup taken before migration 002.
    raise NotImplementedError("Downgrade of 002 is not supported; restore from backup.")
