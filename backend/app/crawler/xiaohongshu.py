import json
import logging
import re
import time
from typing import Optional, List
from urllib.parse import quote, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from app.crawler.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

_XHS_NOTE_PATTERN = re.compile(
    r"xiaohongshu\.com/(?:explore|discovery/item)/([a-f0-9]{20,})"
)

_XHS_NOTE_PATTERN_LOOSE = re.compile(
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

_SEARCH_ENGINE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class XiaohongshuCrawler(BaseCrawler):
    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(_DEFAULT_HEADERS)

    def crawl(self, url: str) -> CrawlResult:
        from app.core.config import XHS_COOKIE

        try:
            headers = dict(_DEFAULT_HEADERS)
            if XHS_COOKIE:
                headers["Cookie"] = XHS_COOKIE
            resp = self._session.get(url, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
            return self._extract(resp.text, url)
        except Exception as e:
            logger.error(f"Crawl failed for {url}: {e}")
            return CrawlResult(error=str(e))

    def search(self, keyword: str, limit: int = 10, sort: str = "popularity") -> List[str]:
        if not keyword or not keyword.strip():
            logger.warning("[search] Empty keyword, skipping search")
            return []

        keyword = keyword.strip()

        urls = self._search_xhs(keyword, limit, sort)
        if urls:
            return urls[:limit]

        logger.info("[search] XHS direct search returned 0, trying Bing fallback")
        urls = self._search_bing(keyword, limit)
        if urls:
            return urls[:limit]

        logger.info("[search] Bing returned 0, trying Google fallback")
        urls = self._search_google(keyword, limit)
        if urls:
            return urls[:limit]

        logger.warning(f"[search] All search methods returned 0 for '{keyword}'")
        return []

    def _search_xhs(self, keyword: str, limit: int, sort: str) -> List[str]:
        from app.core.config import XHS_COOKIE

        encoded = quote(keyword)
        sort_param = "popularity" if sort == "popularity" else "general"
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded}&source=web_search_result_notes&type=51&sort={sort_param}"

        try:
            headers = dict(_DEFAULT_HEADERS)
            if XHS_COOKIE:
                headers["Cookie"] = XHS_COOKIE
            resp = self._session.get(search_url, headers=headers, timeout=self._timeout)
            resp.raise_for_status()

            html = resp.text
            has_state = "__INITIAL_STATE__" in html
            has_login_redirect = "登录" in html and len(html) < 5000

            logger.info(
                f"[search_xhs] Response len={len(html)}, "
                f"has_state={has_state}, has_login_redirect={has_login_redirect}, "
                f"cookie={'yes' if XHS_COOKIE else 'no'}"
            )

            if has_login_redirect:
                logger.warning("[search_xhs] XHS returned login page, Cookie may be invalid or expired")
                return []

            urls = self._extract_note_urls(html, limit)
            logger.info(f"[search_xhs] Found {len(urls)} URLs for keyword: {keyword}")
            return urls
        except Exception as e:
            logger.error(f"[search_xhs] Failed for '{keyword}': {e}")
            return []

    def _search_bing(self, keyword: str, limit: int) -> List[str]:
        encoded = quote(keyword)
        bing_url = f"https://cn.bing.com/search?q=site%3Axiaohongshu.com+{encoded}&setlang=zh-Hans"

        try:
            resp = requests.get(bing_url, headers=_SEARCH_ENGINE_HEADERS, timeout=self._timeout)
            resp.raise_for_status()

            urls = self._extract_note_ids_from_search_html(resp.text, limit)
            logger.info(f"[search_bing] Found {len(urls)} URLs for keyword: {keyword}")
            return urls[:limit]
        except Exception as e:
            logger.error(f"[search_bing] Failed for '{keyword}': {e}")
            return []

    def _search_google(self, keyword: str, limit: int) -> List[str]:
        encoded = quote(keyword)
        google_url = f"https://www.google.com/search?q=site%3Axiaohongshu.com%2Fexplore+{encoded}&hl=zh-CN"

        try:
            resp = requests.get(google_url, headers=_SEARCH_ENGINE_HEADERS, timeout=self._timeout)
            resp.raise_for_status()

            urls = self._extract_note_ids_from_search_html(resp.text, limit)
            logger.info(f"[search_google] Found {len(urls)} URLs for keyword: {keyword}")
            return urls[:limit]
        except Exception as e:
            logger.error(f"[search_google] Failed for '{keyword}': {e}")
            return []

    def _extract_note_ids_from_search_html(self, html: str, limit: int) -> List[str]:
        urls = []
        seen = set()
        soup = BeautifulSoup(html, "html.parser")

        for pattern in [_XHS_NOTE_PATTERN, _XHS_NOTE_PATTERN_LOOSE]:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                match = pattern.search(href)
                if match:
                    note_id = match.group(1)
                    if note_id not in seen and len(note_id) >= 20:
                        seen.add(note_id)
                        urls.append(f"https://www.xiaohongshu.com/explore/{note_id}")

            for cite in soup.find_all("cite"):
                text = cite.get_text()
                match = pattern.search(text)
                if match:
                    note_id = match.group(1)
                    if note_id not in seen and len(note_id) >= 20:
                        seen.add(note_id)
                        urls.append(f"https://www.xiaohongshu.com/explore/{note_id}")

        if not urls:
            all_hrefs = [a.get("href", "") for a in soup.find_all("a", href=True)]
            xhs_hrefs = [h for h in all_hrefs if "xiaohongshu" in h]
            logger.debug(f"[extract_note_ids] No note IDs found. XHS-related hrefs: {xhs_hrefs[:5]}")

        return urls[:limit]

    def _extract_note_urls(self, html: str, limit: int) -> List[str]:
        state_data = self._extract_state_from_html(html)
        if state_data:
            return self._extract_urls_from_state(state_data, limit)

        return self._extract_urls_from_html(html, limit)

    def _extract_urls_from_state(self, state: dict, limit: int) -> List[str]:
        urls = []
        items = self._find_key(state, "items") or self._find_key(state, "feeds") or []

        for item in items[:limit]:
            if isinstance(item, dict):
                note_id = (
                    item.get("id")
                    or item.get("noteId")
                    or item.get("note_card", {}).get("note_id")
                    or ""
                )
                if note_id:
                    urls.append(f"https://www.xiaohongshu.com/explore/{note_id}")
                    continue

                note_card = item.get("noteCard") or item.get("note_card") or {}
                nid = note_card.get("noteId") or note_card.get("note_id") or ""
                if nid:
                    urls.append(f"https://www.xiaohongshu.com/explore/{nid}")

        return urls[:limit]

    def _extract_urls_from_html(self, html: str, limit: int) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            match = _XHS_NOTE_PATTERN_LOOSE.search(href)
            if match:
                note_id = match.group(1)
                if note_id not in seen:
                    seen.add(note_id)
                    full_url = f"https://www.xiaohongshu.com/explore/{note_id}"
                    urls.append(full_url)

        return urls[:limit]

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
