from dataclasses import dataclass
import os


@dataclass
class AppConfig:
    db_path: str = os.getenv("GHOSTSTACK_DB_PATH", "data/ghoststack.db")
    host: str = os.getenv("GHOSTSTACK_HOST", "0.0.0.0")
    port: int = int(os.getenv("GHOSTSTACK_PORT", "8000"))
    log_level: str = os.getenv("GHOSTSTACK_LOG_LEVEL", "info")


config = AppConfig()
