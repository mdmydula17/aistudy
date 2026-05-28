from pydantic import BaseModel, Field


class RadarItem(BaseModel):
    title: str = Field(..., description="笔记标题")
    url: str = Field(..., description="笔记链接")
    author: str = Field(..., description="作者名称")
    likes: str = Field(..., description="点赞数量(支持带有万/w等字符)")
