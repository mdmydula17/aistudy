from pydantic import BaseModel, Field
from typing import List


class AtomSOP(BaseModel):
    source: str = Field(..., description="来源标识，如 URL 或 本地文件名")
    core_arguments: List[str] = Field(..., description="核心论点数组")
    steps: List[str] = Field(..., description="具体操作步骤")
