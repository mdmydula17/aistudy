from pydantic import BaseModel, Field
from typing import List


class AtomSOP(BaseModel):
    source: str = Field(..., description="来源文件名标识")
    core_logic: List[str] = Field(..., description="提取出的底层逻辑或干货论点")
    action_steps: List[str] = Field(..., description="具体的操作步骤、话术或套路")


class MasterReport(BaseModel):
    title: str = Field(..., description="重新构思的极具吸引力的商业研报标题")
    markdown_content: str = Field(..., description="逻辑严密、分层清晰的完整 Markdown 正文（绝对禁止照抄原文句式）")
