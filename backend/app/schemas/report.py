from pydantic import BaseModel, Field


class MasterReport(BaseModel):
    title: str = Field(..., description="重新生成的爆款研报标题")
    markdown_content: str = Field(..., description="超长、结构化的完整正文内容")
