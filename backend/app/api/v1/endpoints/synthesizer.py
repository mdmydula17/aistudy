import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.crud.synth import (
    create_synth_task,
    get_synth_task,
    list_synth_tasks,
    update_synth_task_status,
    get_report_by_synth_task,
)
from app.schemas.asset import SynthTaskCreateDTO, SynthTaskDTO, ReportDTO

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/synth", tags=["synth"])


def _run_synth_background(task_id: str, keyword: str):
    from app.core.database import SessionLocal
    from app.graph.synth_graph import run_synth_graph

    db = SessionLocal()
    try:
        try:
            run_synth_graph(task_id=task_id, keyword=keyword, db_session=db)
        except Exception as e:
            logger.error(f"[synth_background] Failed for {task_id}: {e}", exc_info=True)
            update_synth_task_status(db, task_id, status="failed", error=str(e))
    finally:
        db.close()


@router.get("/", response_model=List[SynthTaskDTO])
def list_synth(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return list_synth_tasks(db, limit=limit, offset=offset)


@router.post("/", response_model=SynthTaskDTO, status_code=201)
def create_synth(
    dto: SynthTaskCreateDTO,
    db: Session = Depends(get_db),
):
    task = create_synth_task(db, keyword=dto.keyword, radar_task_id=dto.radar_task_id)
    return task


@router.get("/{task_id}", response_model=SynthTaskDTO)
def get_synth_detail(task_id: str, db: Session = Depends(get_db)):
    task = get_synth_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Synth task not found")
    return task


@router.get("/{task_id}/report", response_model=ReportDTO)
def get_synth_report(task_id: str, db: Session = Depends(get_db)):
    report = get_report_by_synth_task(db, task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/{task_id}/upload", status_code=200)
async def upload_files(
    task_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    from app.core.config import LOCAL_INPUTS_DIR
    from pathlib import Path

    task = get_synth_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Synth task not found")

    task_dir = LOCAL_INPUTS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for f in files:
        dest = task_dir / f.filename
        content = await f.read()
        dest.write_bytes(content)
        saved.append(f.filename)

    return {"saved": saved, "task_id": task_id}


@router.post("/{task_id}/run", response_model=SynthTaskDTO)
def run_synth(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = get_synth_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Synth task not found")

    if task.status not in ("pending",):
        raise HTTPException(status_code=400, detail=f"Task status is '{task.status}', cannot run")

    update_synth_task_status(db, task_id, status="processing")
    task.status = "processing"

    background_tasks.add_task(_run_synth_background, task_id, task.keyword)
    return task
