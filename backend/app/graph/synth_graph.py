import json
import logging
import re
from functools import partial
from pathlib import Path
from typing import Optional, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.graph.state import SynthState
from app.schemas.atom import AtomSOP, MasterReport

logger = logging.getLogger(__name__)


def _get_default_llm() -> Optional[BaseChatModel]:
    from dotenv import load_dotenv
    import os

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(env_path, override=True)

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        logger.error("[_get_default_llm] No DEEPSEEK_API_KEY found")
        return None

    from app.core.llm import get_chat_llm
    try:
        llm = get_chat_llm()
        logger.info(f"[_get_default_llm] LLM created: {llm.model_name}")
        return llm
    except Exception as e:
        logger.error(f"[_get_default_llm] Failed: {e}")
        return None


def _parse_json_from_text(text: str) -> Optional[dict]:
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()
    text = text.strip()
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _invoke_structured_or_fallback(llm, prompt: str, schema_class, source: str = ""):
    try:
        structured_llm = llm.with_structured_output(schema_class)
        result = structured_llm.invoke(prompt)
        if result and isinstance(result, schema_class):
            return result
    except Exception as e:
        logger.warning(f"[_invoke_structured] with_structured_output failed: {e}, falling back to JSON parse")

    json_prompt = prompt
    if "JSON" not in json_prompt and "json" not in json_prompt:
        schema_str = json.dumps(schema_class.model_json_schema()["properties"], ensure_ascii=False, indent=2)
        json_prompt = (
            f"{prompt}\n\n"
            f"你必须严格按照以下 JSON Schema 输出，不要添加任何多余文字：\n"
            f"```json\n{schema_str}\n```\n"
        )

    try:
        response = llm.invoke([HumanMessage(content=json_prompt)])
        data = _parse_json_from_text(response.content)
        if data:
            if source:
                data["source"] = source
            return schema_class(**data)
    except Exception as e:
        logger.error(f"[_invoke_structured] JSON fallback also failed: {e}")

    return None


def node_ingest(state: SynthState) -> dict:
    task_id = state.get("task_id", "")

    from app.core.config import LOCAL_INPUTS_DIR
    from app.ingestion.local_parser import LocalParser

    parser = LocalParser(LOCAL_INPUTS_DIR)
    items = parser.ingest_task(task_id)

    if not items:
        logger.info(f"[node_ingest] No local files for task: {task_id}")
        return {"error": f"No local files found in data/local_inputs/{task_id}"}

    logger.info(f"[node_ingest] Found {len(items)} files for task: {task_id}")
    return {"atoms": []}


def node_extract(state: SynthState, llm: Optional[BaseChatModel] = None) -> dict:
    task_id = state.get("task_id", "")

    from app.core.config import LOCAL_INPUTS_DIR
    from app.ingestion.local_parser import LocalParser

    parser = LocalParser(LOCAL_INPUTS_DIR)
    items = parser.ingest_task(task_id)

    if not items:
        logger.warning("[node_extract] No items to extract")
        return {"atoms": []}

    chat_llm = llm or _get_default_llm()
    if chat_llm is None:
        logger.error("[node_extract] No LLM available")
        return {"error": "No LLM available for extraction"}

    new_atoms: List[AtomSOP] = []
    for item in items:
        try:
            prompt = (
                f"从以下内容中提取底层逻辑（core_logic）和操作步骤（action_steps）。\n"
                f"来源文件：{item['source']}\n\n"
                f"{item['text'][:6000]}"
            )
            atom = _invoke_structured_or_fallback(chat_llm, prompt, AtomSOP, source=item["source"])
            if atom and isinstance(atom, AtomSOP):
                new_atoms.append(atom)
                logger.info(f"[node_extract] Extracted atom from {item['source']}")
        except Exception as e:
            logger.warning(f"[node_extract] Failed for {item['source']}: {e}")

    if not new_atoms:
        return {"error": "Failed to extract atoms from all files"}

    logger.info(f"[node_extract] Total {len(new_atoms)} atoms extracted")
    return {"atoms": new_atoms}


def node_reduce(state: SynthState, llm: Optional[BaseChatModel] = None) -> dict:
    atoms = state.get("atoms") or []
    keyword = state.get("keyword", "")

    if not atoms:
        logger.warning("[node_reduce] No atoms to synthesize")
        return {"error": "No atoms to synthesize", "final_markdown": None}

    chat_llm = llm or _get_default_llm()
    if chat_llm is None:
        logger.error("[node_reduce] No LLM available")
        return {"error": "No LLM available for synthesis", "final_markdown": None}

    atoms_summary = "\n\n".join(
        f"【来源：{a.source}】\n核心逻辑：{', '.join(a.core_logic)}\n操作步骤：{', '.join(a.action_steps)}"
        for a in atoms
    )

    prompt = (
        f"关键词：{keyword}\n\n"
        f"以下是 {len(atoms)} 份不同来源的原子化知识：\n\n{atoms_summary}\n\n"
        "请融合以上所有知识，去重并重新组织语言，生成一篇拥有独立版权的商业研报。"
        "绝对禁止照抄原文句式，必须用专业、精炼的商业研报口吻重新组织。"
        "输出需要包含丰富的层级（H1, H2, 列表, 引用）的完整 Markdown 文档。"
    )

    try:
        report = _invoke_structured_or_fallback(chat_llm, prompt, MasterReport)
        if report and isinstance(report, MasterReport):
            logger.info(f"[node_reduce] Report generated: {report.title}")
            return {"final_markdown": f"# {report.title}\n\n{report.markdown_content}"}
        else:
            logger.error("[node_reduce] LLM returned unexpected format")
            return {"error": "LLM returned unexpected format", "final_markdown": None}
    except Exception as e:
        logger.error(f"[node_reduce] Failed: {e}")
        return {"error": str(e), "final_markdown": None}


def node_export(state: SynthState, db_session=None) -> dict:
    from app.crud.synth import update_synth_task_status, create_report

    task_id = state.get("task_id", "")
    final_markdown = state.get("final_markdown")
    error = state.get("error")

    if error and not final_markdown:
        if db_session:
            update_synth_task_status(db_session, task_id, status="failed", error=error)
        return {"pdf_path": None}

    if not final_markdown:
        if db_session:
            update_synth_task_status(db_session, task_id, status="failed", error="No markdown to export")
        return {"pdf_path": None}

    title_match = re.search(r"^#\s+(.+)$", final_markdown, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled Report"

    md_path: Optional[str] = None
    pdf_path: Optional[str] = None

    try:
        from app.core.config import OUTPUTS_DIR
        output_file = OUTPUTS_DIR / f"{task_id}.md"
        output_file.write_text(final_markdown, encoding="utf-8")
        md_path = str(output_file)
        logger.info(f"[node_export] Markdown saved: {md_path}")
    except Exception as e:
        logger.warning(f"[node_export] Markdown save failed: {e}")

    try:
        from app.exporter.pdf_renderer import render_pdf
        pdf_path = render_pdf(task_id, final_markdown)
        logger.info(f"[node_export] PDF saved: {pdf_path}")
    except Exception as e:
        logger.warning(f"[node_export] PDF render failed, markdown only: {e}")

    if db_session:
        create_report(
            db_session,
            synth_task_id=task_id,
            title=title,
            markdown_content=final_markdown,
            pdf_path=pdf_path or md_path,
        )
        update_synth_task_status(db_session, task_id, status="completed")

    return {"pdf_path": pdf_path or md_path}


def build_synth_graph(llm: Optional[BaseChatModel] = None, db_session=None) -> StateGraph:
    graph = StateGraph(SynthState)

    chat_llm = llm or _get_default_llm()

    ingest_fn = node_ingest
    extract_fn = partial(node_extract, llm=chat_llm)
    reduce_fn = partial(node_reduce, llm=chat_llm)
    export_fn = partial(node_export, db_session=db_session)

    graph.add_node("ingest", ingest_fn)
    graph.add_node("extract", extract_fn)
    graph.add_node("reduce", reduce_fn)
    graph.add_node("export", export_fn)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "extract")
    graph.add_edge("extract", "reduce")
    graph.add_edge("reduce", "export")
    graph.add_edge("export", END)

    return graph


def compile_synth_graph(llm: Optional[BaseChatModel] = None, db_session=None):
    return build_synth_graph(llm=llm, db_session=db_session).compile()


def run_synth_graph(
    task_id: str,
    keyword: str,
    llm: Optional[BaseChatModel] = None,
    db_session=None,
) -> SynthState:
    app = compile_synth_graph(llm=llm, db_session=db_session)
    initial_state: SynthState = {
        "task_id": task_id,
        "keyword": keyword,
        "atoms": [],
        "final_markdown": None,
        "pdf_path": None,
        "error": None,
    }
    return app.invoke(initial_state)
