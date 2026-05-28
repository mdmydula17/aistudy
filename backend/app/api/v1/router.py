from fastapi import APIRouter

from app.api.v1.endpoints import radar, synthesizer, settings

api_router = APIRouter()

api_router.include_router(radar.router)
api_router.include_router(synthesizer.router)
api_router.include_router(settings.router)
