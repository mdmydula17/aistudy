import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.task_service import TaskService
from app.schemas.asset import TaskCreateDTO, TaskDTO, ReportDTO

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _run_workflow_background(task_id: str, keyword: str, manual_urls: list[str] = None, manual_contents: list[str] = None):
    from app.core.database import SessionLocal
    from app.graph.workflow import run_workflow

    db = SessionLocal()
    try:
        svc = TaskService(db)
        try:
            run_workflow(
                task_id=task_id,
                keyword=keyword,
                manual_urls=manual_urls,
                manual_contents=manual_contents,
                db_session=db,
            )
        except Exception as e:
            logger.error(f"[background] Workflow failed for task {task_id}: {e}", exc_info=True)
            try:
                svc.update_task_status(task_id, status="failed", error=str(e))
            except Exception:
                logger.error(f"[background] Failed to update task status for {task_id}")
    finally:
        db.close()


@router.get("/", response_model=list[TaskDTO])
def list_tasks(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    svc = TaskService(db)
    return svc.list_tasks(limit=limit, offset=offset)


@router.post("/", response_model=TaskDTO, status_code=201)
def create_new_task(
    dto: TaskCreateDTO,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    svc = TaskService(db)
    task = svc.create_task(dto)
    background_tasks.add_task(
        _run_workflow_background,
        task.id,
        task.keyword,
        dto.urls,
        dto.contents,
    )
    return task


@router.get("/{task_id}", response_model=TaskDTO)
def get_task_detail(task_id: str, db: Session = Depends(get_db)):
    svc = TaskService(db)
    task = svc.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/report", response_model=ReportDTO)
def get_task_report(task_id: str, db: Session = Depends(get_db)):
    svc = TaskService(db)
    report = svc.get_report_by_task(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.patch("/{task_id}/approve", response_model=TaskDTO)
def approve_task(task_id: str, db: Session = Depends(get_db)):
    svc = TaskService(db)
    task = svc.update_task_status(task_id, status="completed", needs_human_review=False)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}/reject", response_model=TaskDTO)
def reject_task(task_id: str, db: Session = Depends(get_db)):
    svc = TaskService(db)
    task = svc.update_task_status(task_id, status="rejected", needs_human_review=False)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
