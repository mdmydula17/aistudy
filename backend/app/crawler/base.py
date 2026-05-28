from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class CrawlResult:
    raw_text: Optional[str] = None
    image_urls: Optional[list[str]] = None
    error: Optional[str] = None


class BaseCrawler(ABC):
    @abstractmethod
    def crawl(self, url: str) -> CrawlResult:
        ...

    def search(self, keyword: str, limit: int = 10) -> List[str]:
        return []
