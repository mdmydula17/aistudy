from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.task import Task, Asset
from app.schemas.asset import TaskCreateDTO


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, dto: TaskCreateDTO) -> Task:
        task = Task(url=dto.url, status="pending")
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.db.query(Task).filter(Task.id == task_id).first()

    def update_task_status(
        self,
        task_id: str,
        status: str,
        needs_human_review: bool = False,
        error: Optional[str] = None,
    ) -> Optional[Task]:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.status = status
        task.needs_human_review = needs_human_review
        if error is not None:
            task.error = error
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_assets_by_task(self, task_id: str) -> List[Asset]:
        return self.db.query(Asset).filter(Asset.task_id == task_id).all()

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        return self.db.query(Asset).filter(Asset.id == asset_id).first()
