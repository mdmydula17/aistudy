from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.task_service import TaskService
from app.schemas.asset import TaskCreateDTO, TaskDTO

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _run_workflow_background(task_id: str, url: str):
    from app.core.database import SessionLocal
    from app.graph.workflow import run_workflow

    db = SessionLocal()
    try:
        svc = TaskService(db)
        try:
            run_workflow(task_id=task_id, url=url, db_session=db)
        except Exception as e:
            svc.update_task_status(task_id, status="failed", error=str(e))
    finally:
        db.close()


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
        task.url,
    )
    return task


@router.get("/{task_id}", response_model=TaskDTO)
def get_task_detail(task_id: str, db: Session = Depends(get_db)):
    svc = TaskService(db)
    task = svc.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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
