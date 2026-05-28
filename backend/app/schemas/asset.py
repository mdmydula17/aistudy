from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.schemas.radar import RadarItem


class RadarTaskCreateDTO(BaseModel):
    keyword: str = Field(..., description="搜索关键词，如 '小红书无货源玩法'")


class RadarTaskDTO(BaseModel):
    id: str
    keyword: str
    status: str
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    results: Optional[List[RadarItem]] = None

    model_config = {"from_attributes": True}


class SynthTaskCreateDTO(BaseModel):
    radar_task_id: Optional[str] = Field(None, description="关联的雷达任务 ID")
    keyword: str = Field(..., description="研报主题关键词")


class SynthTaskDTO(BaseModel):
    id: str
    radar_task_id: Optional[str] = None
    keyword: str
    status: str
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportDTO(BaseModel):
    id: str
    synth_task_id: str
    title: str
    markdown_content: str
    pdf_path: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
