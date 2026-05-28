import json
import pytest
from pydantic import ValidationError

from app.schemas.atom import AtomSOP
from app.schemas.report import MasterReport
from app.schemas.asset import (
    ExtractedAssetData,
    TaskCreateDTO,
    TaskDTO,
    AssetDTO,
    ReportDTO,
)


class TestAtomSOPContract:
    def test_valid_atom(self):
        atom = AtomSOP(
            source="https://example.com/note1",
            core_arguments=["论点1", "论点2"],
            steps=["步骤1", "步骤2"],
        )
        assert atom.source == "https://example.com/note1"
        assert len(atom.core_arguments) == 2
        assert len(atom.steps) == 2

    def test_local_file_source(self):
        atom = AtomSOP(
            source="干货手册.pdf",
            core_arguments=["核心论点"],
            steps=["操作步骤"],
        )
        assert atom.source == "干货手册.pdf"

    def test_missing_source_rejected(self):
        with pytest.raises(ValidationError):
            AtomSOP(core_arguments=["a"], steps=["b"])

    def test_missing_core_arguments_rejected(self):
        with pytest.raises(ValidationError):
            AtomSOP(source="test", steps=["b"])

    def test_missing_steps_rejected(self):
        with pytest.raises(ValidationError):
            AtomSOP(source="test", core_arguments=["a"])

    def test_serialization_roundtrip(self):
        atom = AtomSOP(
            source="test.pdf",
            core_arguments=["论点1"],
            steps=["步骤1"],
        )
        json_str = atom.model_dump_json()
        restored = AtomSOP.model_validate_json(json_str)
        assert restored.source == atom.source
        assert restored.core_arguments == atom.core_arguments


class TestMasterReportContract:
    def test_valid_report(self):
        report = MasterReport(
            title="2025小红书无货源全攻略",
            markdown_content="# 核心策略\n\n## 选品\n\n- 方法1\n- 方法2",
        )
        assert report.title == "2025小红书无货源全攻略"
        assert "核心策略" in report.markdown_content

    def test_missing_title_rejected(self):
        with pytest.raises(ValidationError):
            MasterReport(markdown_content="content")

    def test_missing_content_rejected(self):
        with pytest.raises(ValidationError):
            MasterReport(title="title")

    def test_serialization_roundtrip(self):
        report = MasterReport(
            title="研报标题",
            markdown_content="## 正文内容",
        )
        json_str = report.model_dump_json()
        restored = MasterReport.model_validate_json(json_str)
        assert restored.title == report.title


class TestExtractedAssetDataContract:
    def test_valid_extraction(self):
        data = {
            "title": "小红书副业赚钱攻略",
            "core_logic": "## 核心逻辑\n1. 选品 2. 引流 3. 转化",
            "actionable_sop": [
                {"step": "1", "action": "选品", "detail": "选择低客单价高复购品类"},
                {"step": "2", "action": "引流", "detail": "通过笔记内容获取自然流量"},
            ],
            "confidence_score": 0.85,
        }
        obj = ExtractedAssetData(**data)
        assert obj.title == data["title"]
        assert obj.confidence_score == 0.85
        assert len(obj.actionable_sop) == 2

    def test_confidence_score_below_zero_rejected(self):
        data = {
            "title": "test",
            "core_logic": "logic",
            "actionable_sop": [],
            "confidence_score": -0.1,
        }
        with pytest.raises(ValidationError):
            ExtractedAssetData(**data)

    def test_confidence_score_above_one_rejected(self):
        data = {
            "title": "test",
            "core_logic": "logic",
            "actionable_sop": [],
            "confidence_score": 1.5,
        }
        with pytest.raises(ValidationError):
            ExtractedAssetData(**data)

    def test_missing_required_field_rejected(self):
        data = {
            "title": "test",
            "core_logic": "logic",
        }
        with pytest.raises(ValidationError):
            ExtractedAssetData(**data)

    def test_serialization_roundtrip(self):
        data = {
            "title": "测试标题",
            "core_logic": "## 逻辑",
            "actionable_sop": [
                {"step": "1", "action": "a", "detail": "d"},
            ],
            "confidence_score": 0.9,
        }
        obj = ExtractedAssetData(**data)
        json_str = obj.model_dump_json()
        restored = ExtractedAssetData.model_validate_json(json_str)
        assert restored.title == obj.title


class TestTaskCreateDTOContract:
    def test_valid_create_with_keyword(self):
        dto = TaskCreateDTO(keyword="小红书无货源玩法")
        assert dto.keyword == "小红书无货源玩法"

    def test_valid_create_with_urls_only(self):
        dto = TaskCreateDTO(urls=["https://www.xiaohongshu.com/explore/abc123"])
        assert dto.keyword is None
        assert len(dto.urls) == 1

    def test_valid_create_with_keyword_and_urls(self):
        dto = TaskCreateDTO(keyword="测试", urls=["https://www.xiaohongshu.com/explore/abc"])
        assert dto.keyword == "测试"
        assert len(dto.urls) == 1

    def test_missing_both_keyword_and_urls_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO()


class TestTaskDTOContract:
    def test_from_attributes_style(self):
        obj = TaskDTO(
            id="abc-123",
            keyword="小红书无货源",
            status="pending",
            needs_human_review=False,
            error=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert obj.id == "abc-123"
        assert obj.keyword == "小红书无货源"
        assert obj.status == "pending"


class TestReportDTOContract:
    def test_from_attributes_style(self):
        obj = ReportDTO(
            id="report-1",
            task_id="task-1",
            title="研报标题",
            markdown_content="# 正文",
            pdf_path="/data/outputs/task-1.pdf",
            created_at="2025-01-01T00:00:00",
        )
        assert obj.task_id == "task-1"
        assert obj.title == "研报标题"

    def test_pdf_path_optional(self):
        obj = ReportDTO(
            id="report-2",
            task_id="task-2",
            title="标题",
            markdown_content="内容",
            pdf_path=None,
            created_at="2025-01-01T00:00:00",
        )
        assert obj.pdf_path is None
