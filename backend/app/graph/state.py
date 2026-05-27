from typing import List, Optional
from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    task_id: str
    url: str
    raw_text: Optional[str]
    image_urls: Optional[List[str]]
    ocr_text: Optional[str]
    structured_data: Optional[dict]
    needs_human_review: bool
    retry_count: int
    error: Optional[str]
