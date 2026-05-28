from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base
from app.core.config import OUTPUTS_DIR
from app.models.task import Task, Asset, Report
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Info-Arbitrage-Factory",
    version="6.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

try:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/api/v1/files", StaticFiles(directory=str(OUTPUTS_DIR)), name="files")
except Exception:
    pass


@app.get("/health")
def health_check():
    return {"status": "ok"}
