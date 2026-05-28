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

    def test_base_search_returns_empty(self):
        class DummyCrawler(BaseCrawler):
            def crawl(self, url: str) -> CrawlResult:
                return CrawlResult()

        crawler = DummyCrawler()
        assert crawler.search("test") == []


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


class TestXiaohongshuSearch:
    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_extracts_urls_from_state(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''
        <html>
        <script>window.__INITIAL_STATE__={"search":{"items":[{"id":"abc123"},{"id":"def456"},{"id":"ghi789"}]}}</script>
        </html>
        '''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        urls = crawler.search("小红书无货源", limit=10)

        assert len(urls) == 3
        assert "abc123" in urls[0]
        assert "def456" in urls[1]

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_uses_popularity_sort_by_default(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '<html><body></body></html>'
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        crawler.search("测试关键词")

        call_args = mock_session.get.call_args
        url_called = call_args[0][0]
        assert "sort=popularity" in url_called

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_uses_general_sort_when_specified(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '<html><body></body></html>'
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        crawler.search("测试关键词", sort="general")

        call_args = mock_session.get.call_args
        url_called = call_args[0][0]
        assert "sort=general" in url_called

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_respects_limit(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''
        <html>
        <script>window.__INITIAL_STATE__={"search":{"items":[{"id":"a1"},{"id":"b2"},{"id":"c3"},{"id":"d4"},{"id":"e5"}]}}</script>
        </html>
        '''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        urls = crawler.search("测试", limit=3)

        assert len(urls) == 3

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_extracts_urls_from_html_fallback(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''
        <html><body>
        <a href="https://www.xiaohongshu.com/explore/aa1110">笔记1</a>
        <a href="https://www.xiaohongshu.com/search_result/bb2220?xsec_token=abc">笔记2</a>
        <a href="https://www.xiaohongshu.com/discovery/item/cc3330">笔记3</a>
        </body></html>
        '''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        urls = crawler.search("测试", limit=10)

        assert len(urls) == 3
        assert all("xiaohongshu.com/explore/" in u for u in urls)

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_handles_network_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.side_effect = ConnectionError("Network error")

        crawler = XiaohongshuCrawler()
        urls = crawler.search("测试关键词")

        assert urls == []

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_deduplicates_urls(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''
        <html><body>
        <a href="https://www.xiaohongshu.com/explore/aa1110">笔记1</a>
        <a href="https://www.xiaohongshu.com/explore/aa1110">重复</a>
        <a href="https://www.xiaohongshu.com/explore/bb2220">笔记2</a>
        </body></html>
        '''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        urls = crawler.search("测试", limit=10)

        assert len(urls) == 2

    @patch("app.crawler.xiaohongshu.requests.Session")
    def test_search_extracts_from_note_card(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '''
        <html>
        <script>window.__INITIAL_STATE__={"search":{"items":[{"note_card":{"note_id":"xyz999"}}]}}</script>
        </html>
        '''
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        crawler = XiaohongshuCrawler()
        urls = crawler.search("测试")

        assert len(urls) == 1
        assert "xyz999" in urls[0]

    @patch("app.crawler.xiaohongshu.requests.Session")
    @patch("app.crawler.xiaohongshu.requests.get")
    def test_search_falls_back_to_bing(self, mock_bing_get, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        html = '<html><body></body></html>'
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        bing_html = '''
        <html><body>
        <cite>www.xiaohongshu.com/explore/abc001def002ghi003jk</cite>
        <a href="https://www.xiaohongshu.com/explore/def002ghi003abc001jk">笔记</a>
        </body></html>
        '''
        mock_bing_resp = MagicMock()
        mock_bing_resp.text = bing_html
        mock_bing_resp.raise_for_status = MagicMock()
        mock_bing_get.return_value = mock_bing_resp

        crawler = XiaohongshuCrawler()
        urls = crawler.search("测试关键词")

        assert len(urls) == 2
        assert any("abc001def002ghi003jk" in u for u in urls)
        assert any("def002ghi003abc001jk" in u for u in urls)
