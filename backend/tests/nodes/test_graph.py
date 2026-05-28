import json
from unittest.mock import MagicMock, patch

import pytest

from app.graph.state import GraphState, _merge_atoms, _merge_errors
from app.graph.nodes import (
    node_scout,
    node_map_online,
    node_map_local,
    node_reduce_synthesize,
    node_export,
)
from app.graph.workflow import (
    _should_continue_after_scout,
    compile_workflow,
    run_workflow,
)
from app.schemas.atom import AtomSOP


class TestGraphStateReducers:
    def test_merge_atoms_both_none(self):
        assert _merge_atoms(None, None) == []

    def test_merge_atoms_existing_none(self):
        result = _merge_atoms(None, [AtomSOP(source="a", core_arguments=["b"], steps=["c"])])
        assert len(result) == 1

    def test_merge_atoms_new_none(self):
        result = _merge_atoms([AtomSOP(source="a", core_arguments=["b"], steps=["c"])], None)
        assert len(result) == 1

    def test_merge_atoms_both_present(self):
        a1 = AtomSOP(source="a", core_arguments=["b"], steps=["c"])
        a2 = AtomSOP(source="d", core_arguments=["e"], steps=["f"])
        result = _merge_atoms([a1], [a2])
        assert len(result) == 2

    def test_merge_errors_both_none(self):
        assert _merge_errors(None, None) is None

    def test_merge_errors_existing_none(self):
        assert _merge_errors(None, "err1") == "err1"

    def test_merge_errors_new_none(self):
        assert _merge_errors("err1", None) == "err1"

    def test_merge_errors_both_present(self):
        result = _merge_errors("err1", "err2")
        assert "err1" in result
        assert "err2" in result


class TestShouldContinueAfterScout:
    def test_error_goes_to_export(self):
        state: GraphState = {"error": "search failed"}
        assert _should_continue_after_scout(state) == ["export"]

    def test_no_error_goes_to_map(self):
        state: GraphState = {"scouted_urls": ["https://example.com"]}
        result = _should_continue_after_scout(state)
        assert "map_online" in result
        assert "map_local" in result

    def test_empty_state_goes_to_map(self):
        state: GraphState = {}
        result = _should_continue_after_scout(state)
        assert "map_online" in result
        assert "map_local" in result


class TestNodeScout:
    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_success(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.search.return_value = [
            "https://www.xiaohongshu.com/explore/abc",
            "https://www.xiaohongshu.com/explore/def",
        ]
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {"keyword": "小红书无货源"}
        result = node_scout(state)

        assert len(result["scouted_urls"]) == 2
        mock_crawler.search.assert_called_once_with("小红书无货源", limit=10)

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_error(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.search.side_effect = Exception("Network error")
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {"keyword": "测试"}
        result = node_scout(state)

        assert result["error"] is not None

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_empty_results(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.search.return_value = []
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {"keyword": "冷门关键词"}
        result = node_scout(state)

        assert result.get("error") is not None

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_with_manual_urls(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.search.return_value = [
            "https://www.xiaohongshu.com/explore/searched1",
        ]
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {
            "keyword": "测试",
            "manual_urls": ["https://www.xiaohongshu.com/explore/manual1"],
        }
        result = node_scout(state)

        assert len(result["scouted_urls"]) == 2

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_manual_urls_dedup(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.search.return_value = [
            "https://www.xiaohongshu.com/explore/dup1",
        ]
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {
            "keyword": "测试",
            "manual_urls": ["https://www.xiaohongshu.com/explore/dup1"],
        }
        result = node_scout(state)

        assert len(result["scouted_urls"]) == 1

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_error_with_manual_urls_fallback(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.search.side_effect = Exception("Search failed")
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {
            "keyword": "测试",
            "manual_urls": ["https://www.xiaohongshu.com/explore/fallback1"],
        }
        result = node_scout(state)

        assert len(result["scouted_urls"]) == 1
        assert "fallback1" in result["scouted_urls"][0]

    def test_scout_no_keyword_with_manual_urls(self):
        state: GraphState = {
            "keyword": "",
            "manual_urls": ["https://www.xiaohongshu.com/explore/manual1"],
        }
        result = node_scout(state)

        assert len(result["scouted_urls"]) == 1
        assert "manual1" in result["scouted_urls"][0]

    def test_scout_no_keyword_no_urls(self):
        state: GraphState = {
            "keyword": "",
            "manual_urls": [],
        }
        result = node_scout(state)

        assert result.get("error") is not None


class TestNodeMapOnline:
    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_map_online_extracts_atoms(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = CrawlResult(raw_text="副业攻略内容")
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "source": "test",
            "core_arguments": ["论点1"],
            "steps": ["步骤1"],
        })
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "scouted_urls": ["https://www.xiaohongshu.com/explore/abc"],
        }
        result = node_map_online(state, llm=mock_llm)

        assert len(result["atoms"]) == 1
        assert result["atoms"][0].source == "https://www.xiaohongshu.com/explore/abc"

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_map_online_skips_failed_crawls(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = CrawlResult(error="No content")
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {
            "scouted_urls": ["https://bad-url.com"],
        }
        result = node_map_online(state, llm=None)

        assert len(result["atoms"]) == 0

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_map_online_no_urls(self, mock_crawler_cls):
        state: GraphState = {"scouted_urls": []}
        result = node_map_online(state, llm=None)
        assert len(result["atoms"]) == 0

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_map_online_partial_failure(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.crawl.side_effect = [
            CrawlResult(raw_text="有效内容"),
            Exception("Timeout"),
        ]
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "source": "test",
            "core_arguments": ["论点"],
            "steps": ["步骤"],
        })
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "scouted_urls": ["https://good.com", "https://bad.com"],
        }
        result = node_map_online(state, llm=mock_llm)

        assert len(result["atoms"]) == 1

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_map_online_all_fail_sets_error(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.crawl.side_effect = Exception("All fail")
        mock_crawler_cls.return_value = mock_crawler

        state: GraphState = {
            "scouted_urls": ["https://fail1.com", "https://fail2.com"],
        }
        result = node_map_online(state, llm=None)

        assert len(result["atoms"]) == 0
        assert result.get("error") is not None


class TestNodeMapLocal:
    def test_map_local_no_dir(self):
        state: GraphState = {
            "task_id": "nonexistent-task",
        }
        result = node_map_local(state, llm=None)
        assert len(result["atoms"]) == 0

    def test_map_local_empty_dir(self, tmp_path):
        from app.core import config

        original = config.LOCAL_INPUTS_DIR
        config.LOCAL_INPUTS_DIR = tmp_path
        local_dir = tmp_path / "test-task"
        local_dir.mkdir()

        try:
            state: GraphState = {"task_id": "test-task"}
            result = node_map_local(state, llm=None)
            assert len(result["atoms"]) == 0
        finally:
            config.LOCAL_INPUTS_DIR = original

    def test_map_local_reads_txt(self, tmp_path):
        from app.core import config

        original = config.LOCAL_INPUTS_DIR
        config.LOCAL_INPUTS_DIR = tmp_path
        local_dir = tmp_path / "test-task-txt"
        local_dir.mkdir()
        (local_dir / "notes.txt").write_text("这是本地干货内容", encoding="utf-8")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "source": "test",
            "core_arguments": ["本地论点"],
            "steps": ["本地步骤"],
        })
        mock_llm.invoke.return_value = mock_response

        try:
            state: GraphState = {"task_id": "test-task-txt"}
            result = node_map_local(state, llm=mock_llm)
            assert len(result["atoms"]) == 1
            assert result["atoms"][0].source == "notes.txt"
        finally:
            config.LOCAL_INPUTS_DIR = original

    def test_map_local_with_mock_ingestion(self):
        with patch("app.ingestion.parser.LocalIngestion") as mock_cls:
            mock_ingestion = MagicMock()
            mock_cls.return_value = mock_ingestion
            mock_ingestion.ingest_task.return_value = [
                {"source": "manual.pdf", "text": "付费干货内容"},
            ]

            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "source": "test",
                "core_arguments": ["付费论点"],
                "steps": ["付费步骤"],
            })
            mock_llm.invoke.return_value = mock_response

            state: GraphState = {"task_id": "task-with-local"}
            result = node_map_local(state, llm=mock_llm)

            assert len(result["atoms"]) == 1
            assert result["atoms"][0].source == "manual.pdf"


class TestNodeReduceSynthesize:
    def test_no_atoms_returns_error(self):
        state: GraphState = {"atoms": [], "keyword": "test"}
        result = node_reduce_synthesize(state, llm=MagicMock())
        assert result["error"] is not None
        assert result["final_markdown"] is None

    def test_no_llm_returns_error(self):
        state: GraphState = {
            "atoms": [AtomSOP(source="test", core_arguments=["a"], steps=["b"])],
            "keyword": "test",
        }
        result = node_reduce_synthesize(state, llm=None)
        assert result["error"] is not None

    def test_synthesize_success(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "title": "小红书无货源全攻略",
            "markdown_content": "## 核心策略\n\n- 选品\n- 引流\n- 转化",
        })
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "atoms": [
                AtomSOP(source="url1", core_arguments=["论点1"], steps=["步骤1"]),
                AtomSOP(source="url2", core_arguments=["论点2"], steps=["步骤2"]),
            ],
            "keyword": "小红书无货源",
        }
        result = node_reduce_synthesize(state, llm=mock_llm)

        assert result["final_markdown"] is not None
        assert "小红书无货源全攻略" in result["final_markdown"]

    def test_synthesize_wrapped_in_code_block(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "```json\n" + json.dumps({
            "title": "测试研报",
            "markdown_content": "## 内容",
        }) + "\n```"
        mock_llm.invoke.return_value = mock_response

        state: GraphState = {
            "atoms": [AtomSOP(source="test", core_arguments=["a"], steps=["b"])],
            "keyword": "test",
        }
        result = node_reduce_synthesize(state, llm=mock_llm)

        assert result["final_markdown"] is not None
        assert "测试研报" in result["final_markdown"]

    def test_synthesize_llm_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API error")

        state: GraphState = {
            "atoms": [AtomSOP(source="test", core_arguments=["a"], steps=["b"])],
            "keyword": "test",
        }
        result = node_reduce_synthesize(state, llm=mock_llm)

        assert result["error"] is not None
        assert result["final_markdown"] is None


class TestNodeExport:
    def test_export_no_markdown_no_error(self):
        state: GraphState = {
            "task_id": "t1",
            "final_markdown": None,
            "error": None,
        }
        result = node_export(state, db_session=None)
        assert result["pdf_path"] is None

    def test_export_with_error_no_markdown(self):
        mock_db = MagicMock()
        state: GraphState = {
            "task_id": "t1",
            "final_markdown": None,
            "error": "synthesis failed",
        }
        result = node_export(state, db_session=mock_db)
        assert result["pdf_path"] is None

    def test_export_with_markdown(self):
        mock_db = MagicMock()
        state: GraphState = {
            "task_id": "t1",
            "final_markdown": "# 研报标题\n\n## 内容\n\n正文",
            "error": None,
        }
        with patch("app.exporter.pdf_renderer.render_pdf", return_value="/data/outputs/t1.pdf"):
            result = node_export(state, db_session=mock_db)

        assert result["pdf_path"] is not None

    def test_export_with_error_but_has_markdown(self):
        mock_db = MagicMock()
        state: GraphState = {
            "task_id": "t1",
            "final_markdown": "# 研报\n\n内容",
            "error": "partial error",
        }
        with patch("app.exporter.pdf_renderer.render_pdf", return_value="/data/outputs/t1.pdf"):
            result = node_export(state, db_session=mock_db)

        assert result["pdf_path"] is not None

    def test_export_creates_report_in_db(self):
        mock_db = MagicMock()
        state: GraphState = {
            "task_id": "t1",
            "final_markdown": "# 标题\n\n内容",
            "error": None,
        }
        with patch("app.exporter.pdf_renderer.render_pdf", return_value="/data/outputs/t1.pdf"):
            result = node_export(state, db_session=mock_db)

        assert result["pdf_path"] is not None


class TestWorkflowTopologyIntegration:
    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_full_map_reduce_workflow(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.search.return_value = [
            "https://www.xiaohongshu.com/explore/abc",
        ]
        mock_crawler.crawl.return_value = CrawlResult(
            raw_text="副业攻略内容",
            image_urls=None,
        )
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()

        atom_response = MagicMock()
        atom_response.content = json.dumps({
            "source": "test",
            "core_arguments": ["核心论点"],
            "steps": ["操作步骤"],
        })

        report_response = MagicMock()
        report_response.content = json.dumps({
            "title": "综合研报",
            "markdown_content": "## 核心策略\n\n- 方法1\n- 方法2",
        })

        mock_llm.invoke.side_effect = [atom_response, report_response]

        app = compile_workflow(llm=mock_llm, db_session=None)

        initial_state: GraphState = {
            "task_id": "test-task-1",
            "keyword": "小红书无货源",
            "manual_urls": [],
            "scouted_urls": [],
            "atoms": [],
            "final_markdown": None,
            "pdf_path": None,
            "error": None,
        }

        result = app.invoke(initial_state)

        assert result["final_markdown"] is not None
        assert "综合研报" in result["final_markdown"]

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_failure_goes_to_export(self, mock_crawler_cls):
        mock_crawler = MagicMock()
        mock_crawler.search.side_effect = Exception("Search failed")
        mock_crawler_cls.return_value = mock_crawler

        app = compile_workflow(llm=None, db_session=None)

        initial_state: GraphState = {
            "task_id": "test-task-2",
            "keyword": "测试关键词",
            "manual_urls": [],
            "scouted_urls": [],
            "atoms": [],
            "final_markdown": None,
            "pdf_path": None,
            "error": None,
        }

        result = app.invoke(initial_state)

        assert result.get("error") is not None

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_scout_empty_results_then_reduce_no_atoms(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.search.return_value = []
        mock_crawler.crawl.return_value = CrawlResult(error="No content")
        mock_crawler_cls.return_value = mock_crawler

        app = compile_workflow(llm=None, db_session=None)

        initial_state: GraphState = {
            "task_id": "test-task-3",
            "keyword": "冷门关键词",
            "manual_urls": [],
            "scouted_urls": [],
            "atoms": [],
            "final_markdown": None,
            "pdf_path": None,
            "error": None,
        }

        result = app.invoke(initial_state)

        assert result.get("error") is not None
        assert result["final_markdown"] is None

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_map_online_fails_but_local_succeeds(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.search.return_value = ["https://fail.com"]
        mock_crawler.crawl.side_effect = Exception("Crawl failed")
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()

        local_atom_response = MagicMock()
        local_atom_response.content = json.dumps({
            "source": "test",
            "core_arguments": ["本地论点"],
            "steps": ["本地步骤"],
        })

        report_response = MagicMock()
        report_response.content = json.dumps({
            "title": "本地融合研报",
            "markdown_content": "## 本地策略",
        })

        mock_llm.invoke.side_effect = [local_atom_response, report_response]

        with patch("app.ingestion.parser.LocalIngestion") as mock_ingestion_cls:
            mock_ingestion = MagicMock()
            mock_ingestion_cls.return_value = mock_ingestion
            mock_ingestion.ingest_task.return_value = [
                {"source": "manual.pdf", "text": "本地干货"},
            ]

            app = compile_workflow(llm=mock_llm, db_session=None)

            initial_state: GraphState = {
                "task_id": "test-task-4",
                "keyword": "测试",
                "manual_urls": [],
                "scouted_urls": [],
                "atoms": [],
                "final_markdown": None,
                "pdf_path": None,
                "error": None,
            }

            result = app.invoke(initial_state)

            assert result["final_markdown"] is not None
            assert "本地融合研报" in result["final_markdown"]

    @patch("app.graph.nodes.XiaohongshuCrawler")
    def test_reduce_llm_failure_goes_to_export(self, mock_crawler_cls):
        from app.crawler.base import CrawlResult

        mock_crawler = MagicMock()
        mock_crawler.search.return_value = ["https://ok.com"]
        mock_crawler.crawl.return_value = CrawlResult(raw_text="有效内容")
        mock_crawler_cls.return_value = mock_crawler

        mock_llm = MagicMock()

        atom_response = MagicMock()
        atom_response.content = json.dumps({
            "source": "test",
            "core_arguments": ["论点"],
            "steps": ["步骤"],
        })

        mock_llm.invoke.side_effect = [atom_response, Exception("LLM API error")]

        app = compile_workflow(llm=mock_llm, db_session=None)

        initial_state: GraphState = {
            "task_id": "test-task-5",
            "keyword": "测试",
            "manual_urls": [],
            "scouted_urls": [],
            "atoms": [],
            "final_markdown": None,
            "pdf_path": None,
            "error": None,
        }

        result = app.invoke(initial_state)

        assert result.get("error") is not None

    def test_run_workflow_convenience_function(self):
        with patch("app.graph.nodes.XiaohongshuCrawler") as mock_cls:
            mock_crawler = MagicMock()
            mock_crawler.search.return_value = []
            mock_cls.return_value = mock_crawler

            result = run_workflow(
                task_id="conv-test",
                keyword="便捷测试",
                llm=None,
                db_session=None,
            )

            assert result["task_id"] == "conv-test"
            assert result["keyword"] == "便捷测试"
