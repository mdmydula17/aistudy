import operator
from typing import List, Optional, Annotated
from typing_extensions import TypedDict

from app.schemas.atom import AtomSOP
from app.schemas.radar import RadarItem


class RadarState(TypedDict, total=False):
    task_id: str
    keyword: str
    results: Annotated[List[RadarItem], operator.add]
    error: Optional[str]


class SynthState(TypedDict, total=False):
    task_id: str
    keyword: str
    atoms: Annotated[List[AtomSOP], operator.add]
    final_markdown: Optional[str]
    pdf_path: Optional[str]
    error: Optional[str]
