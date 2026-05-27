from unittest.mock import MagicMock, patch
import pytest

from app.crawler.base import BaseCrawler, CrawlResult
from app.crawler.xiaohongshu import XiaohongshuCrawler


class TestCrawlResult:
    def test_default_values(self):
        result = CrawlResult()
        assert result.raw_text is None
        assert result.image_urls is None
        assert result.error is None

    def test_with_data(self):
        result = CrawlResult(
            raw_text="some text",
            image_urls=["https://img.example.com/1.jpg"],
        )
        assert result.raw_text == "some text"
        assert len(result.image_urls) == 1


class TestBaseCrawler:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseCrawler()

    def test_subclass_must_implement_crawl(self):
        class IncompleteCrawler(BaseCrawler):
            pass

        with pytest.raises(TypeError):
            IncompleteCrawler()

    def test_subclass_with_crawl(self):
        class DummyCrawler(BaseCrawler):
            def crawl(self, url: str) -> CrawlResult:
                return CrawlResult(raw_text="hello")

        crawler = DummyCrawler()
        result = crawler.crawl("https://example.com")
        assert result.raw_text == "hello"


class TestXiaohongshuCrawler:
    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_crawl_extracts_text_from_state(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''
        <html>
        <script>window.__INITIAL_STATE__={"noteDetailMap":{"abc":{"note":{"title":"副业攻略","desc":"分享副业经验","imageList":[]}}}}</script>
        </html>
        '''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        result = crawler.crawl("https://www.xiaohongshu.com/explore/abc123")

        assert result.raw_text is not None
        assert "副业攻略" in result.raw_text
        assert result.error is None

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_crawl_extracts_images_from_state(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''
        <html>
        <script>window.__INITIAL_STATE__={"noteDetailMap":{"abc":{"note":{"title":"图文","desc":"内容","imageList":[{"urlDefault":"https://sns-webpic.xhscdn.com/img1.jpg"},{"urlDefault":"https://sns-webpic.xhscdn.com/img2.jpg"}]}}}}</script>
        </html>
        '''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        result = crawler.crawl("https://www.xiaohongshu.com/explore/abc123")

        assert result.image_urls is not None
        assert len(result.image_urls) == 2

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_crawl_handles_exception(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.side_effect = ConnectionError("Network error")

        crawler = XiaohongshuCrawler()
        result = crawler.crawl("https://www.xiaohongshu.com/explore/abc123")

        assert result.error is not None
        assert "Network error" in result.error

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_crawl_no_content_returns_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = "<html><body>Nothing useful here</body></html>"
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        result = crawler.crawl("https://www.xiaohongshu.com/explore/abc123")

        assert result.error is not None
        assert "No content" in result.error

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_crawl_falls_back_to_html_parsing(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''<html><head><meta name="description" content="这是小红书笔记的描述文字"></head><body></body></html>'''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        result = crawler.crawl("https://www.xiaohongshu.com/explore/abc123")

        assert result.raw_text is not None
        assert "小红书笔记" in result.raw_text

    def test_close_cleans_up(self):
        crawler = XiaohongshuCrawler()
        mock_session = MagicMock()
        crawler._session = mock_session
        crawler.close()
        mock_session.close.assert_called_once()
