import logging
from pathlib import Path

from app.core.config import OUTPUTS_DIR

logger = logging.getLogger(__name__)


def render_pdf(task_id: str, markdown_content: str) -> str:
    output_dir = OUTPUTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / f"{task_id}.md"
    md_path.write_text(markdown_content, encoding="utf-8")

    pdf_path = output_dir / f"{task_id}.pdf"

    try:
        from weasyprint import HTML

        html_content = _markdown_to_html(markdown_content)
        html_path = output_dir / f"{task_id}.html"
        html_path.write_text(html_content, encoding="utf-8")

        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        logger.info(f"[render_pdf] PDF generated: {pdf_path}")
        return str(pdf_path)
    except ImportError:
        logger.warning("[render_pdf] weasyprint not installed, trying markdown-pdf")

    try:
        import subprocess

        result = subprocess.run(
            ["mdpdf", "-i", str(md_path), "-o", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and pdf_path.exists():
            logger.info(f"[render_pdf] PDF generated via mdpdf: {pdf_path}")
            return str(pdf_path)
        logger.warning(f"[render_pdf] mdpdf failed: {result.stderr}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("[render_pdf] mdpdf not available")

    logger.info(f"[render_pdf] No PDF renderer available, markdown saved at {md_path}")
    return str(md_path)


def _markdown_to_html(md_text: str) -> str:
    try:
        import markdown

        body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    except ImportError:
        body = _simple_md_to_html(md_text)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
body {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    max-width: 800px;
    margin: 40px auto;
    padding: 0 20px;
    line-height: 1.8;
    color: #333;
}}
h1 {{ font-size: 1.8em; border-bottom: 2px solid #333; padding-bottom: 8px; }}
h2 {{ font-size: 1.5em; border-bottom: 1px solid #666; padding-bottom: 6px; margin-top: 1.5em; }}
h3 {{ font-size: 1.2em; margin-top: 1.2em; }}
blockquote {{ border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #666; background: #f9f9f9; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
pre {{ background: #f4f4f4; padding: 12px; border-radius: 6px; overflow-x: auto; }}
ul, ol {{ padding-left: 2em; }}
li {{ margin: 0.3em 0; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _simple_md_to_html(md_text: str) -> str:
    import re

    text = md_text
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
    text = re.sub(r"^\> (.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)
    text = re.sub(r"^\- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"^\* (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append("<br>")
        elif not stripped.startswith("<"):
            result.append(f"<p>{stripped}</p>")
        else:
            result.append(stripped)
    return "\n".join(result)
