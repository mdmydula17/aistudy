import json
import logging
import re
from typing import Optional, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.crawler.base import CrawlResult
from app.crawler.xiaohongshu import XiaohongshuCrawler
from app.graph.state import GraphState
from app.schemas.atom import AtomSOP
from app.schemas.report import MasterReport

logger = logging.getLogger(__name__)


def node_scout(state: GraphState) -> dict:
    keyword = state.get("keyword", "") or ""
    manual_urls = state.get("manual_urls") or []
    manual_contents = state.get("manual_contents") or []
    logger.info(f"[node_scout] keyword: '{keyword}', manual_urls: {len(manual_urls)}, manual_contents: {len(manual_contents)}")

    if not keyword and not manual_urls and not manual_contents:
        return {"error": "No keyword, URLs, or contents provided"}

    if not keyword and not manual_urls and manual_contents:
        logger.info(f"[node_scout] No keyword/urls, using {len(manual_contents)} manual contents directly")
        return {"scouted_urls": []}

    if not keyword:
        logger.info(f"[node_scout] No keyword, using {len(manual_urls)} manual URLs directly")
        return {"scouted_urls": manual_urls}

    crawler = XiaohongshuCrawler()
    try:
        searched_urls = crawler.search(keyword, limit=10)
        all_urls = list(dict.fromkeys(manual_urls + searched_urls))
        logger.info(f"[node_scout] Total {len(all_urls)} URLs (manual={len(manual_urls)}, searched={len(searched_urls)})")
        if not all_urls and not manual_contents:
            return {"error": f"Search returned no results for '{keyword}'"}
        return {"scouted_urls": all_urls}
    except Exception as e:
        logger.error(f"[node_scout] Search failed: {e}")
        if manual_urls:
            logger.info(f"[node_scout] Using {len(manual_urls)} manual URLs as fallback")
            return {"scouted_urls": manual_urls}
        if manual_contents:
            return {"scouted_urls": []}
        return {"error": str(e)}
    finally:
        crawler.close()


def node_map_online(
    state: GraphState, llm: Optional[BaseChatModel] = None
) -> dict:
    urls = state.get("scouted_urls") or []
    manual_contents = state.get("manual_contents") or []
    logger.info(f"[node_map_online] Processing {len(urls)} URLs, {len(manual_contents)} manual contents")

    new_atoms: List[AtomSOP] = []
    errors: List[str] = []

    for i, content in enumerate(manual_contents):
        if not content or not content.strip():
            continue
        source = f"manual_content_{i + 1}"
        atom = _text_to_atom(llm, source, content)
        if atom:
            new_atoms.append(atom)
            logger.info(f"[node_map_online] Converted manual_content_{i + 1} to atom")
        else:
            logger.warning(f"[node_map_online] Failed to convert manual_content_{i + 1}")

    if urls:
        crawler = XiaohongshuCrawler()
        for url in urls:
            try:
                result: CrawlResult = crawler.crawl(url)
                if result.error or not result.raw_text:
                    logger.warning(f"[node_map_online] Skip {url}: {result.error or 'no text'}")
                    continue

                atom = _text_to_atom(llm, url, result.raw_text)
                if atom:
                    new_atoms.append(atom)
            except Exception as e:
                msg = f"map_online:{url} - {e}"
                logger.warning(f"[node_map_online] Failed {url}: {e}")
                errors.append(msg)
        crawler.close()

    update = {"atoms": new_atoms}
    if not new_atoms and (urls or manual_contents):
        if errors and not manual_contents:
            update["error"] = f"All {len(urls)} URLs failed in map_online"
        elif manual_contents:
            update["error"] = "Failed to extract atoms from all provided contents"
    elif errors:
        logger.warning(f"[node_map_online] {len(errors)}/{len(urls)} URLs failed, {len(new_atoms)} atoms extracted")

    return update


def node_map_local(
    state: GraphState, llm: Optional[BaseChatModel] = None
) -> dict:
    task_id = state.get("task_id", "")

    from app.core.config import LOCAL_INPUTS_DIR
    from app.ingestion.parser import LocalIngestion

    ingestion = LocalIngestion(LOCAL_INPUTS_DIR)
    items = ingestion.ingest_task(task_id)

    if not items:
        logger.info(f"[node_map_local] No local files for task: {task_id}")
        return {"atoms": []}

    new_atoms: List[AtomSOP] = []
    for item in items:
        atom = _text_to_atom(llm, item["source"], item["text"])
        if atom:
            new_atoms.append(atom)

    logger.info(f"[node_map_local] Extracted {len(new_atoms)} atoms from local files")
    return {"atoms": new_atoms}


def node_reduce_synthesize(
    state: GraphState, llm: Optional[BaseChatModel] = None
) -> dict:
    atoms = state.get("atoms") or []
    keyword = state.get("keyword", "")

    if not atoms:
        logger.warning("[node_reduce_synthesize] No atoms to synthesize")
        return {"error": "No atoms to synthesize", "final_markdown": None}

    if llm is None:
        logger.warning("[node_reduce_synthesize] No LLM provided")
        return {"error": "No LLM provided for synthesis", "final_markdown": None}

    logger.info(f"[node_reduce_synthesize] Synthesizing {len(atoms)} atoms")

    atoms_json = json.dumps(
        [a.model_dump() for a in atoms], ensure_ascii=False, indent=2
    )

    system_prompt = (
        "你是一位顶级知识主理人。请分析传入的多个不同来源的方案。\n"
        "1. 寻找高频共识（大家都在用的核心套路）并保留。\n"
        "2. 剔除边缘特例和无意义的废话。\n"
        "3. 绝对禁止直接使用原文的句子结构。你必须用专业、精炼的商业研报口吻，重新组织一套完整的体系。\n"
        "4. 输出为带有丰富层级（H1, H2, 列表, 引用）的完整 Markdown 文档。\n\n"
        "你必须严格按照 JSON Schema 输出，不要添加任何多余文字。\n"
        "Schema:\n"
        "{\n"
        '  "title": "重新生成的爆款研报标题",\n'
        '  "markdown_content": "超长、结构化的完整正文内容 (Markdown格式)"\n'
        "}\n"
    )

    user_prompt = f"关键词：{keyword}\n\n以下是 {len(atoms)} 份不同来源的原子化知识：\n\n{atoms_json}"

    try:
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        content = response.content

        json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        content = content.strip()
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        report = MasterReport(**data)

        return {"final_markdown": f"# {report.title}\n\n{report.markdown_content}"}

    except Exception as e:
        logger.error(f"[node_reduce_synthesize] Failed: {e}")
        return {"error": str(e), "final_markdown": None}


def node_export(state: GraphState, db_session=None) -> dict:
    from app.crud.task import create_report, update_task_status

    task_id = state.get("task_id", "")
    final_markdown = state.get("final_markdown")
    error = state.get("error")

    if error and not final_markdown:
        if db_session:
            update_task_status(db_session, task_id, status="failed", error=error)
        return {"pdf_path": None}

    if not final_markdown:
        if db_session:
            update_task_status(db_session, task_id, status="failed", error="No markdown to export")
        return {"pdf_path": None}

    title_match = re.search(r"^#\s+(.+)$", final_markdown, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled Report"

    pdf_path: Optional[str] = None
    try:
        from app.exporter.pdf_renderer import render_pdf

        pdf_path = render_pdf(task_id, final_markdown)
        logger.info(f"[node_export] PDF saved: {pdf_path}")
    except Exception as e:
        logger.warning(f"[node_export] PDF render failed, saving markdown only: {e}")

    if db_session:
        create_report(
            db_session,
            task_id=task_id,
            title=title,
            markdown_content=final_markdown,
            pdf_path=pdf_path,
        )
        update_task_status(db_session, task_id, status="completed")

    return {"pdf_path": pdf_path}


def _text_to_atom(
    llm: Optional[BaseChatModel], source: str, text: str
) -> Optional[AtomSOP]:
    if not llm:
        return AtomSOP(source=source, core_arguments=["(LLM unavailable)"], steps=["(LLM unavailable)"])

    system_prompt = (
        "你是一个信息提取专家。从以下内容中提取核心论点和操作步骤。\n"
        "你必须严格按照 JSON Schema 输出，不要添加任何多余文字。\n\n"
        "Schema:\n"
        "{\n"
        '  "source": "来源标识",\n'
        '  "core_arguments": ["核心论点1", "核心论点2"],\n'
        '  "steps": ["步骤1", "步骤2"]\n'
        "}\n"
    )

    try:
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=text[:4000]),
            ]
        )
        content = response.content

        json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        content = content.strip()
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        data["source"] = source
        return AtomSOP(**data)

    except Exception as e:
        logger.warning(f"[_text_to_atom] Failed for {source}: {e}")
        return None
