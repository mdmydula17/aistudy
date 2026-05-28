import logging
from functools import partial
from pathlib import Path
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END

from app.graph.state import GraphState
from app.graph.nodes import (
    node_scout,
    node_map_online,
    node_map_local,
    node_reduce_synthesize,
    node_export,
)

logger = logging.getLogger(__name__)


def _should_continue_after_scout(state: GraphState) -> list[str]:
    error = state.get("error")
    if error:
        return ["export"]
    return ["map_online", "map_local"]


def _get_default_llm() -> Optional[BaseChatModel]:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(env_path, override=True)

    import os
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    logger.info(f"[_get_default_llm] DEEPSEEK_API_KEY loaded: {'yes' if api_key else 'NO'} (len={len(api_key)})")

    if not api_key:
        logger.error("[_get_default_llm] No DEEPSEEK_API_KEY found in environment!")
        return None

    from app.core.llm import get_chat_llm
    try:
        llm = get_chat_llm()
        logger.info(f"[_get_default_llm] LLM created successfully: {llm.model_name}")
        return llm
    except Exception as e:
        logger.error(f"[_get_default_llm] Failed to create LLM: {e}")
        return None


def build_workflow(
    llm: Optional[BaseChatModel] = None,
    db_session=None,
) -> StateGraph:
    graph = StateGraph(GraphState)

    chat_llm = llm or _get_default_llm()
    if chat_llm is None:
        logger.error("[build_workflow] No LLM available! All LLM-dependent nodes will fail.")

    scout_fn = node_scout
    map_online_fn = partial(node_map_online, llm=chat_llm)
    map_local_fn = partial(node_map_local, llm=chat_llm)
    reduce_fn = partial(node_reduce_synthesize, llm=chat_llm)
    export_fn = partial(node_export, db_session=db_session)

    graph.add_node("scout", scout_fn)
    graph.add_node("map_online", map_online_fn)
    graph.add_node("map_local", map_local_fn)
    graph.add_node("reduce", reduce_fn)
    graph.add_node("export", export_fn)

    graph.set_entry_point("scout")

    graph.add_conditional_edges(
        "scout",
        _should_continue_after_scout,
        {
            "map_online": "map_online",
            "map_local": "map_local",
            "export": "export",
        },
    )

    graph.add_edge("map_online", "reduce")
    graph.add_edge("map_local", "reduce")

    graph.add_edge("reduce", "export")

    graph.add_edge("export", END)

    return graph


def compile_workflow(
    llm: Optional[BaseChatModel] = None,
    db_session=None,
):
    graph = build_workflow(llm=llm, db_session=db_session)
    return graph.compile()


def run_workflow(
    task_id: str,
    keyword: str,
    manual_urls: Optional[list[str]] = None,
    manual_contents: Optional[list[str]] = None,
    llm: Optional[BaseChatModel] = None,
    db_session=None,
) -> GraphState:
    app = compile_workflow(llm=llm, db_session=db_session)

    initial_state: GraphState = {
        "task_id": task_id,
        "keyword": keyword,
        "manual_urls": manual_urls or [],
        "manual_contents": manual_contents or [],
        "scouted_urls": [],
        "atoms": [],
        "final_markdown": None,
        "pdf_path": None,
        "error": None,
    }

    result = app.invoke(initial_state)
    return result
