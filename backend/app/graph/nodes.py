import json
import logging
import re
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.crawler.base import CrawlResult
from app.crawler.xiaohongshu import XiaohongshuCrawler
from app.graph.state import GraphState
from app.schemas.asset import ExtractedAssetData

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
CONFIDENCE_THRESHOLD = 0.6


def node_crawl(state: GraphState) -> dict:
    url = state.get("url", "")
    logger.info(f"[node_crawl] Crawling: {url}")

    crawler = XiaohongshuCrawler()
    try:
        result: CrawlResult = crawler.crawl(url)
        if result.error:
            return {"error": result.error}
        return {
            "raw_text": result.raw_text,
            "image_urls": result.image_urls,
        }
    except Exception as e:
        logger.error(f"[node_crawl] Exception: {e}")
        return {"error": str(e)}
    finally:
        crawler.close()


def node_vision(state: GraphState, llm: Optional[BaseChatModel] = None) -> dict:
    image_urls = state.get("image_urls") or []
    if not image_urls:
        logger.info("[node_vision] No images, skipping OCR")
        return {"ocr_text": None}

    if llm is None:
        logger.warning("[node_vision] No LLM provided, skipping vision")
        return {"ocr_text": None}

    model_name = getattr(llm, "model_name", "") or getattr(llm, "model", "") or ""
    if "deepseek-chat" in str(model_name):
        logger.info("[node_vision] deepseek-chat does not support vision, skipping OCR")
        return {"ocr_text": None}

    logger.info(f"[node_vision] Processing {len(image_urls)} images")
    ocr_parts = []

    for img_url in image_urls[:5]:
        try:
            message = HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": img_url},
                    },
                    {
                        "type": "text",
                        "text": "请提取这张图片中的所有文字内容，只输出提取的文字，不要添加任何解释。",
                    },
                ]
            )
            response = llm.invoke([message])
            if response.content:
                ocr_parts.append(response.content.strip())
        except Exception as e:
            logger.warning(f"[node_vision] Failed to OCR image: {e}")
            break

    ocr_text = "\n".join(ocr_parts) if ocr_parts else None
    return {"ocr_text": ocr_text}


def node_extract(
    state: GraphState, llm: Optional[BaseChatModel] = None
) -> dict:
    raw_text = state.get("raw_text") or ""
    ocr_text = state.get("ocr_text") or ""
    retry_count = state.get("retry_count", 0)

    combined_text = f"{raw_text}\n{ocr_text}".strip()
    if not combined_text:
        return {"error": "No text available for extraction"}

    if llm is None:
        logger.warning("[node_extract] No LLM provided, returning raw state")
        return {"structured_data": None, "needs_human_review": True}

    logger.info(f"[node_extract] Extracting (attempt {retry_count + 1})")

    system_prompt = (
        "你是一个信息提取专家。从以下小红书笔记内容中提取结构化信息。"
        "你必须严格按照 JSON Schema 输出，不要添加任何多余文字。\n\n"
        "Schema:\n"
        "{\n"
        '  "title": "剔除情绪化表达后的核心标题",\n'
        '  "core_logic": "底层逻辑或高频共识总结 (Markdown格式)",\n'
        '  "actionable_sop": [{"step": "1", "action": "动作描述", "detail": "详细说明"}],\n'
        '  "confidence_score": 0.85\n'
        "}\n\n"
        "confidence_score 范围 0.0-1.0，表示你对提取内容准确性的信心。"
    )

    try:
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=combined_text),
            ]
        )
        content = response.content

        json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        elif "```" in content:
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        content = content.strip()
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        extracted = ExtractedAssetData(**data)

        if extracted.confidence_score < CONFIDENCE_THRESHOLD:
            logger.warning(
                f"[node_extract] Low confidence: {extracted.confidence_score}"
            )
            new_retry = retry_count + 1
            if new_retry >= MAX_RETRIES:
                return {
                    "structured_data": extracted.model_dump(),
                    "needs_human_review": True,
                    "retry_count": new_retry,
                }
            return {
                "structured_data": extracted.model_dump(),
                "needs_human_review": True,
                "retry_count": new_retry,
            }

        return {
            "structured_data": extracted.model_dump(),
            "needs_human_review": False,
            "retry_count": retry_count,
        }

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[node_extract] Parse failed: {e}")
        new_retry = retry_count + 1
        if new_retry >= MAX_RETRIES:
            return {
                "error": f"Extraction failed after {MAX_RETRIES} retries",
                "needs_human_review": True,
                "retry_count": new_retry,
            }
        return {"retry_count": new_retry}

    except Exception as e:
        logger.error(f"[node_extract] Unexpected error: {e}")
        return {"error": str(e), "needs_human_review": True}


def node_save(state: GraphState, db_session=None) -> dict:
    from app.crud.task import create_asset, update_task_status
    from app.schemas.asset import ExtractedAssetData

    task_id = state.get("task_id", "")
    structured_data = state.get("structured_data")
    needs_human_review = state.get("needs_human_review", False)
    error = state.get("error")

    if db_session is None:
        logger.warning("[node_save] No db_session provided, skipping save")
        return {}

    if error and needs_human_review:
        update_task_status(
            db_session,
            task_id,
            status="needs_review",
            needs_human_review=True,
            error=error,
        )
        return {}

    if not structured_data:
        update_task_status(
            db_session,
            task_id,
            status="failed",
            error="No structured data to save",
        )
        return {}

    try:
        extracted = ExtractedAssetData(**structured_data)
        create_asset(
            db_session,
            task_id=task_id,
            extracted=extracted,
            raw_text=state.get("raw_text"),
            ocr_text=state.get("ocr_text"),
        )
        final_status = "needs_review" if needs_human_review else "completed"
        update_task_status(
            db_session,
            task_id,
            status=final_status,
            needs_human_review=needs_human_review,
        )
        logger.info(f"[node_save] Task {task_id} saved as '{final_status}'")
    except Exception as e:
        logger.error(f"[node_save] Save failed: {e}")
        update_task_status(
            db_session,
            task_id,
            status="failed",
            error=str(e),
        )

    return {}
