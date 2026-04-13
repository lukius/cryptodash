from dataclasses import dataclass
import os


@dataclass
class AppConfig:
    db_path: str = os.getenv("CRYPTODASH_DB_PATH", "data/cryptodash.db")
    host: str = os.getenv("CRYPTODASH_HOST", "0.0.0.0")
    port: int = int(os.getenv("CRYPTODASH_PORT", "8000"))
    log_level: str = os.getenv("CRYPTODASH_LOG_LEVEL", "info")


config = AppConfig()
