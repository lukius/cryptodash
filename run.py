#!/usr/bin/env python3
"""CryptoDash — self-hosted crypto portfolio dashboard."""

import sys
import os


def main():
    if sys.version_info < (3, 11):
        print("Error: Python 3.11+ is required.", file=sys.stderr)
        sys.exit(1)

    db_path = os.getenv("CRYPTODASH_DB_PATH", "data/cryptodash.db")
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    import uvicorn
    from backend.config import config

    uvicorn.run(
        "backend.app:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        log_level=config.log_level,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset-password":
        from backend.cli import reset_password
        import asyncio

        asyncio.run(reset_password())
    else:
        main()
