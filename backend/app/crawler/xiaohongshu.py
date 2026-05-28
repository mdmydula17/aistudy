import json
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
        logger.info(f"[search] Starting search for '{keyword}'")

        items = self._search_selenium(keyword, limit)
        if items:
            return items[:limit]

        logger.info("[search] Selenium search returned 0, trying Bing CN")
        items = self._search_bing(keyword, limit)
        if items:
            return items[:limit]

        logger.info("[search] Bing CN returned 0, trying Baidu")
        items = self._search_baidu(keyword, limit)
        if items:
            return items[:limit]

        logger.warning(f"[search] All methods returned 0 for '{keyword}'")
        return []

    def close(self):
        self._session.close()

    def _search_selenium(self, keyword: str, limit: int) -> List[dict]:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            logger.warning("[search_selenium] Selenium not installed, skipping")
            return []

        from app.core.config import XHS_COOKIE

        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        import os
        if not os.path.exists(chrome_path):
            logger.warning(f"[search_selenium] Chrome not found at {chrome_path}")
            return []

        options = Options()
        options.binary_location = chrome_path
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=zh-CN")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(20)

            search_url = (
                f"https://www.xiaohongshu.com/search_result?"
                f"keyword={quote(keyword)}&source=web_search_result_notes&type=51&sort=popularity"
            )
            logger.info(f"[search_selenium] Navigating to {search_url[:100]}")

            if XHS_COOKIE:
                driver.get("https://www.xiaohongshu.com")
                time.sleep(1)
                driver.delete_all_cookies()
                for cookie_str in XHS_COOKIE.split(";"):
                    cookie_str = cookie_str.strip()
                    if "=" in cookie_str:
                        name, value = cookie_str.split("=", 1)
                        try:
                            driver.add_cookie({
                                "name": name.strip(),
                                "value": value.strip(),
                                "domain": ".xiaohongshu.com",
                            })
                        except Exception:
                            pass
                logger.info(f"[search_selenium] Injected {len(XHS_COOKIE.split(';'))} cookies")

            driver.get(search_url)
            time.sleep(5)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "section.note-item, div.note-item, a[href*='/explore/']"))
                )
            except Exception:
                logger.warning("[search_selenium] No results loaded after waiting")

            html = driver.page_source
            logger.info(f"[search_selenium] Page length: {len(html)}")

            items = self._extract_items_from_xhs_html(html, limit)
            logger.info(f"[search_selenium] Found {len(items)} items for '{keyword}'")
            return items

        except Exception as e:
            logger.error(f"[search_selenium] Failed: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _extract_items_from_xhs_html(self, html: str, limit: int) -> List[dict]:
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

        if not items:
            soup = BeautifulSoup(html, "html.parser")
            seen = set()
            for section in soup.find_all("section"):
                a = section.find("a", href=True)
                if a:
                    href = a["href"]
                    match = _XHS_NOTE_PATTERN.search(href)
                    if match:
                        note_id = match.group(1)
                        if note_id not in seen:
                            seen.add(note_id)
                            title_el = section.find(class_=re.compile(r"title|desc", re.I))
                            title = title_el.get_text(strip=True) if title_el else ""
                            author_el = section.find(class_=re.compile(r"author|name|nick", re.I))
                            author = author_el.get_text(strip=True) if author_el else ""
                            likes_el = section.find(class_=re.compile(r"like|count", re.I))
                            likes = likes_el.get_text(strip=True) if likes_el else ""
                            items.append({
                                "title": title,
                                "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                                "author": author,
                                "likes": likes,
                            })

        return items[:limit]

    def _search_bing(self, keyword: str, limit: int) -> List[dict]:
        encoded = quote(keyword)
        bing_url = (
            f"https://cn.bing.com/search?"
            f"q=site%3Axiaohongshu.com+{encoded}&setlang=zh-Hans&cc=CN"
        )

        try:
            headers = dict(_DEFAULT_HEADERS)
            headers["Referer"] = "https://cn.bing.com/"
            resp = requests.get(bing_url, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
            items = self._extract_items_from_search_html(resp.text, limit)
            logger.info(f"[search_bing] Found {len(items)} items for '{keyword}'")
            return items
        except Exception as e:
            logger.error(f"[search_bing] Failed for '{keyword}': {e}")
            return []

    def _search_baidu(self, keyword: str, limit: int) -> List[dict]:
        encoded = quote(keyword)
        baidu_url = (
            f"https://www.baidu.com/s?"
            f"wd=site%3Axiaohongshu.com+{encoded}&rn=20"
        )

        try:
            headers = dict(_DEFAULT_HEADERS)
            headers["Referer"] = "https://www.baidu.com/"
            resp = requests.get(baidu_url, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
            items = self._extract_items_from_search_html(resp.text, limit)
            logger.info(f"[search_baidu] Found {len(items)} items for '{keyword}'")
            return items
        except Exception as e:
            logger.error(f"[search_baidu] Failed for '{keyword}': {e}")
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

        for text_node in soup.find_all(string=re.compile(r"xiaohongshu\.com/(?:explore|discovery)/[a-f0-9]{20,}")):
            match = _XHS_NOTE_PATTERN.search(str(text_node))
            if match:
                note_id = match.group(1)
                if note_id not in seen and len(note_id) >= 20:
                    seen.add(note_id)
                    parent = text_node.find_parent("a") or text_node.find_parent("div")
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
