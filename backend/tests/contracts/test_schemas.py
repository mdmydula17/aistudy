import json
import pytest
from pydantic import ValidationError

from app.schemas.asset import (
    ExtractedAssetData,
    TaskCreateDTO,
    TaskDTO,
    AssetDTO,
)


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

    def test_actionable_sop_structure(self):
        data = {
            "title": "test",
            "core_logic": "logic",
            "actionable_sop": [
                {"step": "1", "action": "do", "detail": "detail"},
            ],
            "confidence_score": 0.7,
        }
        obj = ExtractedAssetData(**data)
        assert obj.actionable_sop[0]["step"] == "1"

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
        assert restored.confidence_score == obj.confidence_score


class TestTaskCreateDTOContract:
    def test_valid_create(self):
        dto = TaskCreateDTO(url="https://www.xiaohongshu.com/explore/123456")
        assert "xiaohongshu.com" in dto.url

    def test_missing_url_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO()


class TestTaskDTOContract:
    def test_from_attributes_style(self):
        obj = TaskDTO(
            id="abc-123",
            url="https://example.com",
            status="pending",
            needs_human_review=False,
            error=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert obj.id == "abc-123"
        assert obj.status == "pending"


class TestAssetDTOContract:
    def test_from_attributes_style(self):
        obj = AssetDTO(
            id="asset-1",
            task_id="task-1",
            title="标题",
            core_logic="逻辑",
            actionable_sop='[{"step":"1"}]',
            confidence_score=0.8,
            raw_text=None,
            ocr_text=None,
            created_at="2025-01-01T00:00:00",
        )
        assert obj.task_id == "task-1"
