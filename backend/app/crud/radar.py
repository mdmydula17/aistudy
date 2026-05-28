from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.task import RadarTask, RadarResult


def create_radar_task(db: Session, keyword: str) -> RadarTask:
    task = RadarTask(keyword=keyword, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_radar_task(db: Session, task_id: str) -> Optional[RadarTask]:
    return db.query(RadarTask).filter(RadarTask.id == task_id).first()


def list_radar_tasks(db: Session, limit: int = 50, offset: int = 0) -> List[RadarTask]:
    return (
        db.query(RadarTask)
        .order_by(RadarTask.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_radar_task_status(
    db: Session,
    task_id: str,
    status: str,
    error: Optional[str] = None,
) -> Optional[RadarTask]:
    task = get_radar_task(db, task_id)
    if task is None:
        return None
    task.status = status
    if error is not None:
        task.error = error
    db.commit()
    db.refresh(task)
    return task


def save_radar_results(db: Session, task_id: str, items: List[dict]) -> List[RadarResult]:
    results = []
    for item in items:
        result = RadarResult(
            task_id=task_id,
            title=item.get("title", ""),
            url=item.get("url", ""),
            author=item.get("author", ""),
            likes=item.get("likes", ""),
        )
        db.add(result)
        results.append(result)
    db.commit()
    for r in results:
        db.refresh(r)
    return results


def get_radar_results(db: Session, task_id: str) -> List[RadarResult]:
    return db.query(RadarResult).filter(RadarResult.task_id == task_id).all()
