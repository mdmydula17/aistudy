import logging
import re
import time
from typing import List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_XHS_NOTE_PATTERN = re.compile(
    r"xiaohongshu\.com/(?:explore|discovery/item)/([a-f0-9]{20,})"
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


class XiaohongshuCrawler:
    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(_DEFAULT_HEADERS)

    def search(self, keyword: str, limit: int = 10) -> List[dict]:
        if not keyword or not keyword.strip():
            logger.warning("[search] Empty keyword, skipping")
            return []

        keyword = keyword.strip()

        items = self._search_xhs(keyword, limit)
        if items:
            return items[:limit]

        logger.info("[search] XHS direct search returned 0, trying Bing fallback")
        items = self._search_bing(keyword, limit)
        if items:
            return items[:limit]

        logger.info("[search] Bing returned 0, trying Google fallback")
        items = self._search_google(keyword, limit)
        if items:
            return items[:limit]

        logger.warning(f"[search] All methods returned 0 for '{keyword}'")
        return []

    def close(self):
        self._session.close()

    def _search_xhs(self, keyword: str, limit: int) -> List[dict]:
        from app.core.config import XHS_COOKIE

        encoded = quote(keyword)
        search_url = (
            f"https://www.xiaohongshu.com/search_result?"
            f"keyword={encoded}&source=web_search_result_notes&type=51&sort=popularity"
        )

        try:
            headers = dict(_DEFAULT_HEADERS)
            if XHS_COOKIE:
                headers["Cookie"] = XHS_COOKIE
            resp = self._session.get(search_url, headers=headers, timeout=self._timeout)
            resp.raise_for_status()

            html = resp.text
            has_login_redirect = "登录" in html and len(html) < 5000

            logger.info(
                f"[search_xhs] len={len(html)}, "
                f"cookie={'yes' if XHS_COOKIE else 'no'}, "
                f"login_redirect={has_login_redirect}"
            )

            if has_login_redirect:
                logger.warning("[search_xhs] Login page returned, Cookie may be expired")
                return []

            items = self._extract_items_from_xhs_html(html, limit)
            logger.info(f"[search_xhs] Found {len(items)} items for '{keyword}'")
            return items
        except Exception as e:
            logger.error(f"[search_xhs] Failed for '{keyword}': {e}")
            return []

    def _extract_items_from_xhs_html(self, html: str, limit: int) -> List[dict]:
        import json

        items = []
        state_match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*({.+?})\s*</script>", html, re.DOTALL
        )
        if state_match:
            try:
                raw = state_match.group(1).replace("undefined", "null")
                state = json.loads(raw)
                feeds = self._find_key(state, "feeds") or self._find_key(state, "items") or []
                for feed in feeds[:limit]:
                    if not isinstance(feed, dict):
                        continue
                    note_card = feed.get("noteCard") or feed.get("note_card") or {}
                    note_id = (
                        note_card.get("noteId")
                        or note_card.get("note_id")
                        or feed.get("id")
                        or feed.get("noteId")
                        or ""
                    )
                    title = note_card.get("displayTitle") or note_card.get("title") or ""
                    user = note_card.get("user") or {}
                    author = user.get("nickname") or user.get("nickName") or ""
                    likes = str(note_card.get("interactInfo", {}).get("likedCount") or "")
                    if note_id:
                        items.append({
                            "title": title,
                            "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                            "author": author,
                            "likes": likes,
                        })
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[extract_xhs] JSON parse failed: {e}")

        if not items:
            soup = BeautifulSoup(html, "html.parser")
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                match = _XHS_NOTE_PATTERN.search(href)
                if match:
                    note_id = match.group(1)
                    if note_id not in seen:
                        seen.add(note_id)
                        title_el = a.find(["span", "div"])
                        title = title_el.get_text(strip=True) if title_el else ""
                        items.append({
                            "title": title,
                            "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                            "author": "",
                            "likes": "",
                        })

        return items[:limit]

    def _search_bing(self, keyword: str, limit: int) -> List[dict]:
        encoded = quote(keyword)
        bing_url = f"https://cn.bing.com/search?q=site%3Axiaohongshu.com+{encoded}&setlang=zh-Hans"

        try:
            resp = requests.get(bing_url, headers=_SEARCH_ENGINE_HEADERS, timeout=self._timeout)
            resp.raise_for_status()
            items = self._extract_items_from_search_html(resp.text, limit)
            logger.info(f"[search_bing] Found {len(items)} items for '{keyword}'")
            return items
        except Exception as e:
            logger.error(f"[search_bing] Failed for '{keyword}': {e}")
            return []

    def _search_google(self, keyword: str, limit: int) -> List[dict]:
        encoded = quote(keyword)
        google_url = f"https://www.google.com/search?q=site%3Axiaohongshu.com%2Fexplore+{encoded}&hl=zh-CN"

        try:
            resp = requests.get(google_url, headers=_SEARCH_ENGINE_HEADERS, timeout=self._timeout)
            resp.raise_for_status()
            items = self._extract_items_from_search_html(resp.text, limit)
            logger.info(f"[search_google] Found {len(items)} items for '{keyword}'")
            return items
        except Exception as e:
            logger.error(f"[search_google] Failed for '{keyword}': {e}")
            return []

    def _extract_items_from_search_html(self, html: str, limit: int) -> List[dict]:
        items = []
        seen = set()
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            match = _XHS_NOTE_PATTERN.search(href)
            if match:
                note_id = match.group(1)
                if note_id not in seen and len(note_id) >= 20:
                    seen.add(note_id)
                    title = a.get_text(strip=True)[:200]
                    items.append({
                        "title": title,
                        "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                        "author": "",
                        "likes": "",
                    })

        for cite in soup.find_all("cite"):
            text = cite.get_text()
            match = _XHS_NOTE_PATTERN.search(text)
            if match:
                note_id = match.group(1)
                if note_id not in seen and len(note_id) >= 20:
                    seen.add(note_id)
                    parent = cite.find_parent("a") or cite.find_parent("div")
                    title = parent.get_text(strip=True)[:200] if parent else ""
                    items.append({
                        "title": title,
                        "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                        "author": "",
                        "likes": "",
                    })

        return items[:limit]

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
