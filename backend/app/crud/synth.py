from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.task import SynthTask, Report


def create_synth_task(db: Session, keyword: str, radar_task_id: Optional[str] = None) -> SynthTask:
    task = SynthTask(keyword=keyword, radar_task_id=radar_task_id, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_synth_task(db: Session, task_id: str) -> Optional[SynthTask]:
    return db.query(SynthTask).filter(SynthTask.id == task_id).first()


def list_synth_tasks(db: Session, limit: int = 50, offset: int = 0) -> List[SynthTask]:
    return (
        db.query(SynthTask)
        .order_by(SynthTask.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_synth_task_status(
    db: Session,
    task_id: str,
    status: str,
    error: Optional[str] = None,
) -> Optional[SynthTask]:
    task = get_synth_task(db, task_id)
    if task is None:
        return None
    task.status = status
    if error is not None:
        task.error = error
    db.commit()
    db.refresh(task)
    return task


def create_report(
    db: Session,
    synth_task_id: str,
    title: str,
    markdown_content: str,
    pdf_path: Optional[str] = None,
) -> Report:
    report = Report(
        synth_task_id=synth_task_id,
        title=title,
        markdown_content=markdown_content,
        pdf_path=pdf_path,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_synth_task(db: Session, synth_task_id: str) -> Optional[Report]:
    return db.query(Report).filter(Report.synth_task_id == synth_task_id).first()
