import json
import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from app.crawler.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

_XHS_NOTE_PATTERN = re.compile(
    r"xiaohongshu\.com/(?:explore|discovery/item|search_result)/([a-f0-9]+)"
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.xiaohongshu.com/",
}


class XiaohongshuCrawler(BaseCrawler):
    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(_DEFAULT_HEADERS)

    def crawl(self, url: str) -> CrawlResult:
        try:
            resp = self._session.get(url, timeout=self._timeout)
            resp.raise_for_status()
            return self._extract(resp.text, url)
        except Exception as e:
            logger.error(f"Crawl failed for {url}: {e}")
            return CrawlResult(error=str(e))

    def _extract(self, html: str, url: str) -> CrawlResult:
        state_data = self._extract_state_from_html(html)
        if state_data:
            return self._parse_state_data(state_data, url)

        raw_text = self._extract_text_from_html(html)
        image_urls = self._extract_images_from_html(html)

        if not raw_text and not image_urls:
            return CrawlResult(error=f"No content extracted from {url}")
        return CrawlResult(raw_text=raw_text, image_urls=image_urls)

    def _extract_state_from_html(self, html: str) -> Optional[dict]:
        patterns = [
            re.compile(
                r"window\.__INITIAL_STATE__\s*=\s*({.+?})\s*</script>",
                re.DOTALL,
            ),
            re.compile(
                r"window\.__INITIAL_SSR_DATA__\s*=\s*({.+?})\s*</script>",
                re.DOTALL,
            ),
        ]
        for pattern in patterns:
            match = pattern.search(html)
            if match:
                try:
                    raw = match.group(1)
                    raw = raw.replace("undefined", "null")
                    return json.loads(raw)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse state JSON: {e}")
                    continue
        return None

    def _parse_state_data(self, state: dict, url: str) -> CrawlResult:
        note_data = None

        note_data = self._find_key(state, "noteDetailMap")
        if note_data:
            for note_id, note_obj in note_data.items():
                note = note_obj.get("note", {})
                return self._build_result_from_note(note)

        note = self._find_key(state, "note")
        if note and isinstance(note, dict):
            return self._build_result_from_note(note)

        return CrawlResult(error=f"Could not parse note data from state for {url}")

    def _build_result_from_note(self, note: dict) -> CrawlResult:
        raw_text = None
        desc = note.get("desc", "")
        title = note.get("title", "")
        if desc or title:
            parts = []
            if title:
                parts.append(f"# {title}")
            if desc:
                parts.append(desc)
            raw_text = "\n".join(parts)

        image_urls = None
        image_list = note.get("imageList") or note.get("image_list") or []
        if image_list:
            urls = []
            for img in image_list:
                url = (
                    img.get("urlDefault")
                    or img.get("url_default")
                    or img.get("url")
                    or img.get("liveUrl")
                    or ""
                )
                if url and url.startswith("http"):
                    if not url.startswith("http://"):
                        url = url.replace("http://", "https://")
                    urls.append(url)
            if urls:
                image_urls = urls

        if not raw_text and not image_urls:
            return CrawlResult(error="No content found in note data")
        return CrawlResult(raw_text=raw_text, image_urls=image_urls)

    def _find_key(self, obj, key, depth=0):
        if depth > 10:
            return None
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            for v in obj.values():
                result = self._find_key(v, key, depth + 1)
                if result is not None:
                    return result
        return None

    def _extract_text_from_html(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")

        selectors = [
            "#detail-desc",
            ".note-text",
            ".desc",
            "[class*='noteContent']",
            "[class*='desc']",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()

        return None

    def _extract_images_from_html(self, html: str) -> Optional[list[str]]:
        soup = BeautifulSoup(html, "html.parser")
        img_tags = soup.select("img")

        urls = []
        seen = set()
        for img in img_tags:
            src = img.get("src") or img.get("data-src") or ""
            if (
                src
                and src.startswith("http")
                and ("sns-webpic" in src or "xhscdn" in src)
                and src not in seen
            ):
                seen.add(src)
                urls.append(src)

        return urls if urls else None

    def close(self):
        self._session.close()
