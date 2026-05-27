import logging
from functools import partial
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END

from app.graph.state import GraphState
from app.graph.nodes import node_crawl, node_vision, node_extract, node_save

logger = logging.getLogger(__name__)


def _should_vision(state: GraphState) -> str:
    image_urls = state.get("image_urls") or []
    if image_urls:
        return "vision"
    return "extract"


def _should_retry_or_review(state: GraphState) -> str:
    needs_review = state.get("needs_human_review", False)
    retry_count = state.get("retry_count", 0)
    error = state.get("error")

    if error and needs_review:
        return "save"

    if needs_review and retry_count >= 3:
        return "save"

    if needs_review:
        return "extract"

    return "save"


def _get_default_llm() -> Optional[BaseChatModel]:
    from app.core.config import DEEPSEEK_API_KEY
    if not DEEPSEEK_API_KEY:
        return None
    from app.core.llm import get_chat_llm
    return get_chat_llm()


def _get_default_vision_llm() -> Optional[BaseChatModel]:
    from app.core.config import DEEPSEEK_API_KEY
    if not DEEPSEEK_API_KEY:
        return None
    from app.core.llm import get_vision_llm
    return get_vision_llm()


def build_workflow(
    llm: Optional[BaseChatModel] = None,
    vision_llm: Optional[BaseChatModel] = None,
    db_session=None,
) -> StateGraph:
    graph = StateGraph(GraphState)

    chat_llm = llm or _get_default_llm()
    v_llm = vision_llm or _get_default_vision_llm()

    crawl_fn = node_crawl
    vision_fn = partial(node_vision, llm=v_llm)
    extract_fn = partial(node_extract, llm=chat_llm)
    save_fn = partial(node_save, db_session=db_session)

    graph.add_node("crawl", crawl_fn)
    graph.add_node("vision", vision_fn)
    graph.add_node("extract", extract_fn)
    graph.add_node("save", save_fn)

    graph.set_entry_point("crawl")

    graph.add_conditional_edges(
        "crawl",
        _should_vision,
        {"vision": "vision", "extract": "extract"},
    )

    graph.add_edge("vision", "extract")

    graph.add_conditional_edges(
        "extract",
        _should_retry_or_review,
        {"extract": "extract", "save": "save"},
    )

    graph.add_edge("save", END)

    return graph


def compile_workflow(
    llm: Optional[BaseChatModel] = None,
    vision_llm: Optional[BaseChatModel] = None,
    db_session=None,
):
    graph = build_workflow(llm=llm, vision_llm=vision_llm, db_session=db_session)
    return graph.compile()


def run_workflow(
    task_id: str,
    url: str,
    llm: Optional[BaseChatModel] = None,
    vision_llm: Optional[BaseChatModel] = None,
    db_session=None,
) -> GraphState:
    app = compile_workflow(llm=llm, vision_llm=vision_llm, db_session=db_session)

    initial_state: GraphState = {
        "task_id": task_id,
        "url": url,
        "raw_text": None,
        "image_urls": None,
        "ocr_text": None,
        "structured_data": None,
        "needs_human_review": False,
        "retry_count": 0,
        "error": None,
    }

    result = app.invoke(initial_state)
    return result
