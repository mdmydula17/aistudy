from typing import List, Optional, Annotated
from typing_extensions import TypedDict

from app.schemas.atom import AtomSOP


def _merge_atoms(existing: List[AtomSOP], new: List[AtomSOP]) -> List[AtomSOP]:
    if existing is None:
        existing = []
    if new is None:
        new = []
    return existing + new


def _merge_errors(existing: Optional[str], new: Optional[str]) -> Optional[str]:
    if not existing and not new:
        return None
    if not existing:
        return new
    if not new:
        return existing
    return f"{existing}; {new}"


class GraphState(TypedDict, total=False):
    task_id: str
    keyword: str
    manual_urls: List[str]
    manual_contents: List[str]
    scouted_urls: Annotated[List[str], _merge_atoms]
    atoms: Annotated[List[AtomSOP], _merge_atoms]
    final_markdown: Optional[str]
    pdf_path: Optional[str]
    error: Annotated[Optional[str], _merge_errors]
