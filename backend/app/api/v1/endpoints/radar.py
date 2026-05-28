import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.radar import (
    create_radar_task,
    get_radar_task,
    list_radar_tasks,
    update_radar_task_status,
    save_radar_results,
    get_radar_results,
)
from app.schemas.asset import RadarTaskCreateDTO, RadarTaskDTO
from app.schemas.radar import RadarItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/radar", tags=["radar"])


def _run_radar_background(task_id: str, keyword: str):
    from app.core.database import SessionLocal
    from app.graph.radar_graph import run_radar_graph

    db = SessionLocal()
    try:
        try:
            result = run_radar_graph(task_id=task_id, keyword=keyword)
            error = result.get("error")
            items = result.get("results", [])

            if error and not items:
                update_radar_task_status(db, task_id, status="failed", error=error)
            else:
                if items:
                    raw_items = [item.model_dump() for item in items]
                    save_radar_results(db, task_id, raw_items)
                status = "completed" if items else "failed"
                err = error if not items else None
                update_radar_task_status(db, task_id, status=status, error=err)
        except Exception as e:
            logger.error(f"[radar_background] Failed for {task_id}: {e}", exc_info=True)
            update_radar_task_status(db, task_id, status="failed", error=str(e))
    finally:
        db.close()


@router.get("/", response_model=List[RadarTaskDTO])
def list_radar(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    tasks = list_radar_tasks(db, limit=limit, offset=offset)
    dtos = []
    for t in tasks:
        results = get_radar_results(db, t.id)
        dto = RadarTaskDTO(
            id=t.id,
            keyword=t.keyword,
            status=t.status,
            error=t.error,
            created_at=t.created_at,
            updated_at=t.updated_at,
            results=[RadarItem(title=r.title, url=r.url, author=r.author, likes=r.likes) for r in results],
        )
        dtos.append(dto)
    return dtos


@router.post("/", response_model=RadarTaskDTO, status_code=201)
def create_radar(
    dto: RadarTaskCreateDTO,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = create_radar_task(db, dto.keyword)
    background_tasks.add_task(_run_radar_background, task.id, task.keyword)
    return RadarTaskDTO(
        id=task.id,
        keyword=task.keyword,
        status=task.status,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        results=None,
    )


@router.get("/{task_id}", response_model=RadarTaskDTO)
def get_radar_detail(task_id: str, db: Session = Depends(get_db)):
    task = get_radar_task(db, task_id)
    if task is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Radar task not found")
    results = get_radar_results(db, task_id)
    return RadarTaskDTO(
        id=task.id,
        keyword=task.keyword,
        status=task.status,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        results=[RadarItem(title=r.title, url=r.url, author=r.author, likes=r.likes) for r in results],
    )
