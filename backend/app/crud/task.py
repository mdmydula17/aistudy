import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.task import Task, Asset, Report
from app.schemas.asset import ExtractedAssetData, TaskCreateDTO


def create_task(db: Session, dto: TaskCreateDTO) -> Task:
    task = Task(keyword=dto.keyword, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id).first()


def list_tasks(db: Session, limit: int = 50, offset: int = 0) -> list[Task]:
    return (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_task_status(
    db: Session,
    task_id: str,
    status: str,
    needs_human_review: bool = False,
    error: Optional[str] = None,
) -> Optional[Task]:
    task = get_task(db, task_id)
    if task is None:
        return None
    task.status = status
    task.needs_human_review = needs_human_review
    if error is not None:
        task.error = error
    db.commit()
    db.refresh(task)
    return task


def create_asset(
    db: Session,
    task_id: str,
    extracted: ExtractedAssetData,
    raw_text: Optional[str] = None,
    ocr_text: Optional[str] = None,
) -> Asset:
    asset = Asset(
        task_id=task_id,
        title=extracted.title,
        core_logic=extracted.core_logic,
        actionable_sop=json.dumps(
            extracted.actionable_sop, ensure_ascii=False
        ),
        confidence_score=extracted.confidence_score,
        raw_text=raw_text,
        ocr_text=ocr_text,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_assets_by_task(db: Session, task_id: str) -> list[Asset]:
    return db.query(Asset).filter(Asset.task_id == task_id).all()


def get_asset(db: Session, asset_id: str) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.id == asset_id).first()


def create_report(
    db: Session,
    task_id: str,
    title: str,
    markdown_content: str,
    pdf_path: Optional[str] = None,
) -> Report:
    report = Report(
        task_id=task_id,
        title=title,
        markdown_content=markdown_content,
        pdf_path=pdf_path,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_task(db: Session, task_id: str) -> Optional[Report]:
    return db.query(Report).filter(Report.task_id == task_id).first()


def get_report(db: Session, report_id: str) -> Optional[Report]:
    return db.query(Report).filter(Report.id == report_id).first()
