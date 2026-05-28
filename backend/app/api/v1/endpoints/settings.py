from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import save_xhs_cookie, XHS_COOKIE

router = APIRouter(prefix="/settings", tags=["settings"])


class CookiePayload(BaseModel):
    cookie: str


class CookieResponse(BaseModel):
    saved: bool
    preview: str


@router.post("/cookie", response_model=CookieResponse)
def save_cookie(payload: CookiePayload):
    save_xhs_cookie(payload.cookie)
    preview = payload.cookie[:20] + "..." if len(payload.cookie) > 20 else payload.cookie
    return CookieResponse(saved=True, preview=preview)


@router.get("/cookie", response_model=CookieResponse)
def get_cookie_status():
    has_cookie = bool(XHS_COOKIE)
    preview = XHS_COOKIE[:20] + "..." if has_cookie and len(XHS_COOKIE) > 20 else XHS_COOKIE
    return CookieResponse(saved=has_cookie, preview=preview if has_cookie else "")
