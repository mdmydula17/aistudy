import json
from unittest.mock import MagicMock, patch

import pytest

from app.graph.state import GraphState
from app.graph.nodes import (
    node_crawl,
    node_vision,
    node_extract,
    node_save,
    MAX_RETRIES,
    CONFIDENCE_THRESHOLD,
)
from app.graph.workflow import (
    _should_vision,
    _should_retry_or_review,
    compile_workflow,
    run_workflow,
)


class TestGraphState:
    def test_default_state(self):
        state: GraphState = {
            "task_id": "test-1",
            "url": "https://example.com",
        }
        assert state["task_id"] == "test-1"
        assert state["url"] == "https://example.com"


class TestShouldVision:
    def test_has_images_goes_to_vision(self):
        state: GraphState = {"image_urls": ["https://img.jpg"]}
        assert _should_vision(state) == "vision"

    def test_no_images_goes_to_extract(self):
        state: GraphState = {"image_urls": []}
        assert _should_vision(state) == "extract"

    def test_none_images_goes_to_extract(self):
        state: GraphState = {}
        assert _should_vision(state) == "extract"


class TestShouldRetryOrReview:
    def test_error_with_review_goes_to_save(self):
        state: GraphState = {
            "error": "parse failed",
            "needs_human_review": True,
        }
        assert _should_retry_or_review(state) == "save"

    def test_review_max_retries_goes_to_save(self):
        state: GraphState = {
            "needs_human_review": True,
            "retry_count": MAX_RETRIES,
        }
        assert _should_retry_or_review(state) == "save"

    def test_review_under_retries_goes_to_extract(self):
        state: GraphState = {
            "needs_human_review": True,
            "retry_count": 1,
        }
        assert _should_retry_or_review(state) == "extract"

    def test_no_review_goes_to_save(self):
        state: GraphState = {
            "needs_human_review": False,
            "structured_data": {"title": "ok"},
        }
        assert _should_retry_or_review(state) == "save"


class TestNodeCrawl:
    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_crawl_success(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        from app.crawler.base import CrawlResult

        mock_crawler.crawl.return_value = CrawlResult(
            raw_text="副业攻略",
            image_urls=["https://sns-webpic.xhscdn.com/img1.jpg"],
        )
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {"url": "https://www.xiaohongshu.com/explore/abc"}
        result = node_crawl(state)

        assert result["raw_text"] == "副业攻略"
        assert len(result["image_urls"]) == 1

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_crawl_error(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        from app.crawler.base import CrawlResult

        mock_crawler.crawl.return_value = CrawlResult(error="Page not found")
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {"url": "https://bad-url.com"}
        result = node_crawl(state)

        assert result["error"] == "Page not found"


class TestNodeVision:
    def test_no_images_returns_none(self):
        state: GraphState = {"image_urls": []}
        result = node_vision(state, llm=None)
        assert result["ocr_text"] is None

    def test_no_llm_returns_none(self):
        state: GraphState = {"image_urls": ["https://img.jpg"]}
        result = node_vision(state, llm=None)
        assert result["ocr_text"] is None

    def test_vision_with_mock_llm(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "图片中的文字内容"
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "image_urls": ["https://sns-webpic.xhscdn.com/img1.jpg"]
        }
        result = node_vision(state, llm=mock_llm)

        assert result["ocr_text"] == "图片中的文字内容"
        mock_llm.invoke.assert_called_once()


class TestNodeExtract:
    def test_no_text_returns_error(self):
        state: GraphState = {"raw_text": None, "ocr_text": None}
        result = node_extract(state, llm=None)
        assert result["error"] == "No text available for extraction"

    def test_no_llm_sets_human_review(self):
        state: GraphState = {"raw_text": "some text", "ocr_text": ""}
        result = node_extract(state, llm=None)
        assert result["needs_human_review"] is True

    def test_extract_high_confidence(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "title": "副业赚钱攻略",
            "core_logic": "## 核心逻辑\n选品引流转化",
            "actionable_sop": [
                {"step": "1", "action": "选品", "detail": "选择低客单价品类"}
            ],
            "confidence_score": 0.9,
        })
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "raw_text": "副业赚钱攻略分享",
            "ocr_text": "",
            "retry_count": 0,
        }
        result = node_extract(state, llm=mock_llm)

        assert result["structured_data"] is not None
        assert result["structured_data"]["title"] == "副业赚钱攻略"
        assert result["needs_human_review"] is False

    def test_extract_low_confidence_triggers_review(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "title": "模糊内容",
            "core_logic": "不确定",
            "actionable_sop": [],
            "confidence_score": 0.4,
        })
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "raw_text": "一些模糊的文字",
            "ocr_text": "",
            "retry_count": 0,
        }
        result = node_extract(state, llm=mock_llm)

        assert result["needs_human_review"] is True

    def test_extract_json_parse_failure_retries(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "this is not json"
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "raw_text": "some text",
            "ocr_text": "",
            "retry_count": 0,
        }
        result = node_extract(state, llm=mock_llm)

        assert result["retry_count"] == 1

    def test_extract_max_retries_sets_review(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "still not json"
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "raw_text": "some text",
            "ocr_text": "",
            "retry_count": MAX_RETRIES - 1,
        }
        result = node_extract(state, llm=mock_llm)

        assert result["needs_human_review"] is True
        assert result["retry_count"] == MAX_RETRIES


class TestNodeSave:
    def test_save_no_session_returns_empty(self):
        state: GraphState = {
            "task_id": "t1",
            "structured_data": {"title": "ok"},
            "needs_human_review": False,
        }
        result = node_save(state, db_session=None)
        assert result == {}

    def test_save_with_error_and_review(self):
        mock_db = MagicMock()
        state: GraphState = {
            "task_id": "t1",
            "error": "parse failed",
            "needs_human_review": True,
        }
        result = node_save(state, db_session=mock_db)
        assert result == {}

    def test_save_success(self):
        mock_db = MagicMock()
        state: GraphState = {
            "task_id": "t1",
            "structured_data": {
                "title": "攻略",
                "core_logic": "逻辑",
                "actionable_sop": [{"step": "1", "action": "a", "detail": "d"}],
                "confidence_score": 0.85,
            },
            "needs_human_review": False,
            "raw_text": "raw",
            "ocr_text": None,
        }
        result = node_save(state, db_session=mock_db)
        assert result == {}


class TestWorkflowIntegration:
    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_full_workflow_text_only(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = CrawlResult(
            raw_text="副业赚钱攻略分享，核心是选品和引流",
            image_urls=None,
        )
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()
        extract_response = MagicMock()
        extract_response.content = json.dumps({
            "title": "副业赚钱攻略",
            "core_logic": "## 核心逻辑\n选品与引流",
            "actionable_sop": [
                {"step": "1", "action": "选品", "detail": "选择品类"}
            ],
            "confidence_score": 0.88,
        })
        mock_llm.invoke.return_value = extract_response

        app = compile_workflow(llm=mock_llm, vision_llm=mock_llm, db_session=None)

        initial_state: GraphState = {
            "task_id": "test-task-1",
            "url": "https://www.xiaohongshu.com/explore/abc",
            "raw_text": None,
            "image_urls": None,
            "ocr_text": None,
            "structured_data": None,
            "needs_human_review": False,
            "retry_count": 0,
            "error": None,
        }

        result = app.invoke(initial_state)

        assert result["structured_data"] is not None
        assert result["structured_data"]["title"] == "副业赚钱攻略"
        assert result["needs_human_review"] is False

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_full_workflow_with_images(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = CrawlResult(
            raw_text="图文攻略",
            image_urls=["https://sns-webpic.xhscdn.com/img1.jpg"],
        )
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()
        vision_response = MagicMock()
        vision_response.content = "图片中的文字"

        extract_response = MagicMock()
        extract_response.content = json.dumps({
            "title": "图文攻略",
            "core_logic": "逻辑",
            "actionable_sop": [],
            "confidence_score": 0.75,
        })
        mock_llm.invoke.side_effect = [vision_response, extract_response]

        app = compile_workflow(llm=mock_llm, vision_llm=mock_llm, db_session=None)

        initial_state: GraphState = {
            "task_id": "test-task-2",
            "url": "https://www.xiaohongshu.com/explore/def",
            "raw_text": None,
            "image_urls": None,
            "ocr_text": None,
            "structured_data": None,
            "needs_human_review": False,
            "retry_count": 0,
            "error": None,
        }

        result = app.invoke(initial_state)

        assert result["ocr_text"] == "图片中的文字"
        assert result["structured_data"] is not None

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_full_workflow_low_confidence_hitl(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = CrawlResult(
            raw_text="模糊内容",
            image_urls=None,
        )
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()
        extract_response = MagicMock()
        extract_response.content = json.dumps({
            "title": "模糊",
            "core_logic": "不确定",
            "actionable_sop": [],
            "confidence_score": 0.3,
        })
        mock_llm.invoke.return_value = extract_response

        app = compile_workflow(llm=mock_llm, vision_llm=mock_llm, db_session=None)

        initial_state: GraphState = {
            "task_id": "test-task-3",
            "url": "https://www.xiaohongshu.com/explore/ghi",
            "raw_text": None,
            "image_urls": None,
            "ocr_text": None,
            "structured_data": None,
            "needs_human_review": False,
            "retry_count": 0,
            "error": None,
        }

        result = app.invoke(initial_state)

        assert result["needs_human_review"] is True
