import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'info_arbitrage.db'}",
)

DATA_DIR: Path = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv(
    "DEEPSEEK_BASE_URL",
    "https://api.deepseek.com",
)
DEEPSEEK_MODEL: str = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-chat",
)
DEEPSEEK_VISION_MODEL: str = os.getenv(
    "DEEPSEEK_VISION_MODEL",
    "deepseek-chat",
)
