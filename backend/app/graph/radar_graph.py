import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END

from app.graph.state import RadarState
from app.schemas.radar import RadarItem

logger = logging.getLogger(__name__)


def node_search(state: RadarState) -> dict:
    keyword = state.get("keyword", "")
    if not keyword:
        return {"error": "No keyword provided"}

    from app.crawler.xiaohongshu import XiaohongshuCrawler

    crawler = XiaohongshuCrawler()
    try:
        raw_items = crawler.search(keyword, limit=20)
        items = [RadarItem(**item) for item in raw_items]
        logger.info(f"[node_search] Found {len(items)} items for '{keyword}'")
        if not items:
            return {"error": f"No results found for '{keyword}'"}
        return {"results": items}
    except Exception as e:
        logger.error(f"[node_search] Failed: {e}")
        return {"error": str(e)}
    finally:
        crawler.close()


def build_radar_graph() -> StateGraph:
    graph = StateGraph(RadarState)
    graph.add_node("search", node_search)
    graph.set_entry_point("search")
    graph.add_edge("search", END)
    return graph


def compile_radar_graph():
    return build_radar_graph().compile()


def run_radar_graph(task_id: str, keyword: str) -> RadarState:
    app = compile_radar_graph()
    initial_state: RadarState = {
        "task_id": task_id,
        "keyword": keyword,
        "results": [],
        "error": None,
    }
    return app.invoke(initial_state)
