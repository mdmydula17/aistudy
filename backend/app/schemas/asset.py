from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional
from datetime import datetime


class ExtractedAssetData(BaseModel):
    title: str = Field(..., description="剔除情绪化表达后的核心标题")
    core_logic: str = Field(..., description="底层逻辑或高频共识总结 (Markdown格式)")
    actionable_sop: List[Dict[str, str]] = Field(
        ...,
        description="可落地的结构化步骤，格式为 [{'step': '1', 'action': '...', 'detail': '...'}]",
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="AI 评估提取内容的置信度 (0.0 - 1.0)"
    )


class TaskCreateDTO(BaseModel):
    keyword: Optional[str] = Field(None, description="搜索关键词，如 '小红书无货源玩法'")
    urls: Optional[List[str]] = Field(None, description="手动指定的小红书笔记 URL 列表")
    contents: Optional[List[str]] = Field(None, description="手动粘贴的笔记文本内容列表，与 urls 一一对应或独立提供")

    @model_validator(mode="after")
    def check_keyword_or_urls(self):
        if not self.keyword and not self.urls and not self.contents:
            raise ValueError("keyword、urls、contents 至少需要提供一个")
        return self


class TaskDTO(BaseModel):
    id: str
    keyword: Optional[str] = None
    status: str
    needs_human_review: bool
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetDTO(BaseModel):
    id: str
    task_id: str
    title: str
    core_logic: str
    actionable_sop: str
    confidence_score: float
    raw_text: Optional[str] = None
    ocr_text: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportDTO(BaseModel):
    id: str
    task_id: str
    title: str
    markdown_content: str
    pdf_path: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
