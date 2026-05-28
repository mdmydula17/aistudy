import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'info_arbitrage.db'}",
)

DATA_DIR: Path = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

LOCAL_INPUTS_DIR: Path = DATA_DIR / "local_inputs"
LOCAL_INPUTS_DIR.mkdir(exist_ok=True)

OUTPUTS_DIR: Path = DATA_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)


def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


DEEPSEEK_API_KEY: str = _get_env("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL: str = _get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = _get_env("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_VISION_MODEL: str = _get_env("DEEPSEEK_VISION_MODEL", "deepseek-chat")

_COOKIE_FILE: Path = DATA_DIR / "xhs_cookie.txt"

XHS_COOKIE: str = _get_env("XHS_COOKIE")

if not XHS_COOKIE and _COOKIE_FILE.exists():
    XHS_COOKIE = _COOKIE_FILE.read_text(encoding="utf-8").strip()


def save_xhs_cookie(cookie: str) -> None:
    global XHS_COOKIE
    XHS_COOKIE = cookie.strip()
    _COOKIE_FILE.write_text(XHS_COOKIE, encoding="utf-8")


def get_deepseek_api_key() -> str:
    return os.getenv("DEEPSEEK_API_KEY") or DEEPSEEK_API_KEY


def get_deepseek_base_url() -> str:
    return os.getenv("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL


def get_deepseek_model() -> str:
    return os.getenv("DEEPSEEK_MODEL") or DEEPSEEK_MODEL
