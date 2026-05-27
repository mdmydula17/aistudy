from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.services.task_service import TaskService
from app.schemas.asset import AssetDTO

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/task/{task_id}", response_model=List[AssetDTO])
def list_assets_by_task(task_id: str, db: Session = Depends(get_db)):
    svc = TaskService(db)
    assets = svc.get_assets_by_task(task_id)
    return assets


@router.get("/{asset_id}", response_model=AssetDTO)
def get_asset_detail(asset_id: str, db: Session = Depends(get_db)):
    svc = TaskService(db)
    asset = svc.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
