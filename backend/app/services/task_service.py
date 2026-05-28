from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.task import Task, Asset, Report
from app.schemas.asset import TaskCreateDTO


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, dto: TaskCreateDTO) -> Task:
        keyword = dto.keyword or "(手动URL任务)"
        task = Task(keyword=keyword, status="pending")
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.db.query(Task).filter(Task.id == task_id).first()

    def list_tasks(self, limit: int = 50, offset: int = 0) -> List[Task]:
        return (
            self.db.query(Task)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

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

    def get_report_by_task(self, task_id: str) -> Optional[Report]:
        return self.db.query(Report).filter(Report.task_id == task_id).first()

    def get_report(self, report_id: str) -> Optional[Report]:
        return self.db.query(Report).filter(Report.id == report_id).first()
