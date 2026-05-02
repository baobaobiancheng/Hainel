from datetime import datetime
import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import conversations as conversations_api
from app.models.message import MessageRole
from app.services.conversation_service import ConversationService


class FakeQuery:
    def __init__(self, items):
        self._items = list(items)
        self._limit = None

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self._limit = value
        return self

    def first(self):
        items = self.all()
        return items[0] if items else None

    def all(self):
        if self._limit is None:
            return list(self._items)
        return list(self._items)[: self._limit]


class FakeDB:
    def __init__(self, data_map):
        self.data_map = data_map

    def query(self, model):
        return FakeQuery(self.data_map.get(model, []))


def make_message(message_id, created_at, metadata=None, content="diagnosis content"):
    return SimpleNamespace(
        id=message_id,
        conversation_id=1,
        role=MessageRole.ASSISTANT,
        content=content,
        extra_metadata=metadata or {},
        created_at=created_at,
        message_type="text",
        file_name=None,
        file_type=None,
    )


def test_select_latest_diagnosis_message_prefers_primary_analysis_type():
    older_primary = make_message(
        1,
        datetime(2026, 4, 29, 9, 0, 0),
        {"analysis_type": "智能诊断"},
    )
    newer_fallback = make_message(
        2,
        datetime(2026, 4, 29, 10, 0, 0),
        {"action_checklist": {"observe": ["watch"]}},
    )

    selected = ConversationService.select_latest_diagnosis_message([newer_fallback, older_primary])

    assert selected.id == 1


def test_get_diagnosis_context_groups_kg_knowledge_and_fallback_reports(monkeypatch):
    from app.models.user import User
    from app.models.message import Message
    from app.models.medical_record import MedicalRecord

    conversation = SimpleNamespace(
        id=1,
        patient_id=101,
        title="chest pain session",
        chief_complaint="chest pain for 2 hours",
        status=SimpleNamespace(value="active"),
        created_at=datetime(2026, 4, 29, 8, 0, 0),
        updated_at=datetime(2026, 4, 29, 8, 30, 0),
        extra_metadata={
            "structured_intake": {"main_symptom": "chest pain"},
            "triage": {"department_name": "cardiology", "urgency": "high"},
        },
    )
    patient = SimpleNamespace(
        id=101,
        username="patient_a",
        full_name="Alice",
        health_profile={"gender": "female", "birth_date": "1990-01-01", "allergies": "penicillin"},
    )
    diagnosis_message = make_message(
        8,
        datetime(2026, 4, 29, 8, 40, 0),
        {
            "analysis_type": "智能诊断",
            "difficulty": "urgent",
            "red_flags": [{"category": "chest pain", "keywords": ["chest pain"]}],
            "action_checklist": {"observe": ["record symptom change"], "when_to_seek_care": ["worsening pain"]},
            "kg_context": {
                "summary": "knowledge summary",
                "knowledge": [
                    {"source": "symptom_a", "relation": "has_symptom", "target": "disease_a", "target_labels": ["Disease"]},
                    {"source": "symptom_a", "relation": "do_eat", "target": "food_a", "target_labels": ["Food"]},
                    {"source": "symptom_a", "relation": "common_drug", "target": "drug_a", "target_labels": ["Drug"]},
                    {"source": "symptom_a", "relation": "need_check", "target": "exam_a", "target_labels": ["Exam"]},
                ],
            },
        },
        "seek offline care immediately",
    )
    report_message = SimpleNamespace(
        id=21,
        conversation_id=1,
        role=MessageRole.ASSISTANT,
        file_name="ecg.pdf",
        file_type="application/pdf",
        message_type="file",
        extra_metadata={"report_type": "ECG", "ocr_result": {"text": "sinus rhythm"}},
        created_at=datetime(2026, 4, 29, 8, 35, 0),
    )
    medical_record = SimpleNamespace(
        id=31,
        title="initial record",
        status=SimpleNamespace(value="draft"),
        updated_at=datetime(2026, 4, 29, 8, 50, 0),
        conversation_id=1,
    )

    fake_db = FakeDB(
        {
            User: [patient],
            Message: [diagnosis_message, report_message],
            MedicalRecord: [medical_record],
        }
    )

    monkeypatch.setattr(ConversationService, "get_conversation_by_id", staticmethod(lambda conversation_id, db: conversation))

    context = ConversationService.get_diagnosis_context(1, fake_db)

    assert context["patient"]["name"] == "Alice"
    assert context["structured_intake"]["main_symptom"] == "chest pain"
    assert context["triage"]["department_name"] == "cardiology"
    assert context["latest_diagnosis"]["difficulty"] == "urgent"
    assert context["latest_diagnosis"]["red_flags"][0]["category"] == "chest pain"
    assert context["linked_reports"][0]["file_name"] == "ecg.pdf"
    assert context["medical_records"][0]["title"] == "initial record"

    kg_context = context["latest_diagnosis"]["kg_context"]
    assert "has_symptom" not in kg_context["summary"]
    assert "symptom_a" in kg_context["summary"]
    group_titles = {group["key"] for group in kg_context["groups"]}
    assert {"disease", "food_recommended", "drug", "exam"}.issubset(group_titles)
    food_group = next(group for group in kg_context["groups"] if group["key"] == "food_recommended")
    assert food_group["items"][0]["relation_label"] == "do_eat" or food_group["items"][0]["relation_label"]
    assert food_group["items"][0]["target"] == "food_a"


def test_diagnosis_context_classifies_cmekg_entities_before_relation(monkeypatch):
    from app.models.user import User
    from app.models.message import Message
    from app.models.medical_record import MedicalRecord
    conversation_module = importlib.import_module("app.services.conversation_service")

    monkeypatch.setattr(
        conversation_module,
        "_CMEKG_ENTITY_GROUPS",
        {
            "symptom": {"symptom_true"},
            "disease": {"disease_target"},
            "exam": {"exam_target"},
            "drug": {"drug_target"},
            "food_recommended": {"food_target", "food_target_2"},
            "food_avoid": {"avoid_target"},
            "department": {"department_target"},
            "complication": set(),
            "treatment": set(),
            "other": set(),
        },
    )

    conversation = SimpleNamespace(
        id=1,
        patient_id=101,
        title="session",
        chief_complaint="palpitation",
        status=SimpleNamespace(value="active"),
        created_at=datetime(2026, 4, 29, 8, 0, 0),
        updated_at=datetime(2026, 4, 29, 8, 30, 0),
        extra_metadata={},
    )
    patient = SimpleNamespace(id=101, username="patient_a", full_name="Alice", health_profile={})
    diagnosis_message = make_message(
        8,
        datetime(2026, 4, 29, 8, 40, 0),
        {
            "analysis_type": "智能诊断",
            "kg_context": {
                "summary": "raw summary with has_symptom",
                "knowledge": [
                    {"source": "source_a", "relation": "has_symptom", "target": "disease_target", "target_labels": ["Disease"]},
                    {"source": "source_a", "relation": "has_symptom", "target": "department_target", "target_labels": ["Department"]},
                    {"source": "source_a", "relation": "has_symptom", "target": "food_target", "target_labels": ["Food"]},
                    {"source": "source_a", "relation": "has_symptom", "target": "food_target_2", "target_labels": ["Food"]},
                    {"source": "source_a", "relation": "not_eat", "target": "avoid_target", "target_labels": ["Food"]},
                    {"source": "source_a", "relation": "common_drug", "target": "drug_target", "target_labels": ["Drug"]},
                    {"source": "source_a", "relation": "need_check", "target": "exam_target", "target_labels": ["Exam"]},
                ],
            },
        },
    )

    fake_db = FakeDB({User: [patient], Message: [diagnosis_message], MedicalRecord: []})
    monkeypatch.setattr(ConversationService, "get_conversation_by_id", staticmethod(lambda conversation_id, db: conversation))

    context = ConversationService.get_diagnosis_context(1, fake_db)
    kg_context = context["latest_diagnosis"]["kg_context"]
    grouped_targets = {
        group["key"]: {item["target"] for item in group["items"]}
        for group in kg_context["groups"]
    }

    assert "has_symptom" not in kg_context["summary"]
    assert grouped_targets["disease"] == {"disease_target"}
    assert grouped_targets["department"] == {"department_target"}
    assert grouped_targets["food_recommended"] == {"food_target", "food_target_2"}
    assert grouped_targets["food_avoid"] == {"avoid_target"}
    assert grouped_targets["drug"] == {"drug_target"}
    assert grouped_targets["exam"] == {"exam_target"}
    assert "food_target" not in grouped_targets.get("symptom", set())
    assert "department_target" not in grouped_targets.get("symptom", set())


def test_get_medical_record_draft_prefills_from_context(monkeypatch):
    from app.models.user import User
    from app.models.message import Message
    from app.models.medical_record import MedicalRecord

    conversation = SimpleNamespace(
        id=1,
        patient_id=101,
        title="cardiac session",
        chief_complaint="palpitations",
        status=SimpleNamespace(value="active"),
        created_at=datetime(2026, 4, 29, 8, 0, 0),
        updated_at=datetime(2026, 4, 29, 8, 30, 0),
        extra_metadata={
            "structured_intake": {"main_symptom": "palpitations", "duration": "2 days"},
            "triage": {"department_name": "cardiology"},
        },
    )
    patient = SimpleNamespace(
        id=101,
        username="patient_a",
        full_name="Alice",
        health_profile={"gender": "female", "past_history": "hypertension"},
    )
    diagnosis_message = make_message(
        9,
        datetime(2026, 4, 29, 8, 45, 0),
        {
            "analysis_type": "primary",
            "action_checklist": {
                "observe": ["monitor heart rate"],
                "when_to_seek_care": ["severe dizziness"],
            },
        },
        "Likely benign palpitations",
    )
    report_message = SimpleNamespace(
        id=22,
        conversation_id=1,
        role=MessageRole.ASSISTANT,
        file_name="echo.pdf",
        file_type="application/pdf",
        message_type="file",
        extra_metadata={"report_type": "Echo", "ocr_result": {"text": "normal chambers"}},
        created_at=datetime(2026, 4, 29, 8, 40, 0),
    )

    fake_db = FakeDB(
        {
            User: [patient],
            Message: [diagnosis_message, report_message],
            MedicalRecord: [],
        }
    )

    monkeypatch.setattr(ConversationService, "get_conversation_by_id", staticmethod(lambda conversation_id, db: conversation))

    draft = ConversationService.get_medical_record_draft(1, fake_db)

    assert draft["patient"]["name"] == "Alice"
    assert draft["conversation"]["chief_complaint"] == "palpitations"
    assert draft["draft_record"]["chief_complaint"] == "palpitations"
    assert "main_symptom" not in (draft["draft_record"]["present_illness"] or "")
    assert "palpitations" in (draft["draft_record"]["present_illness"] or "")
    assert "echo.pdf" in (draft["draft_record"]["auxiliary_examination"] or "")
    assert draft["draft_record"]["preliminary_diagnosis"] == "Likely benign palpitations"
    assert draft["draft_record"]["metadata"]["source"] == "ai_draft"
    assert draft["draft_record"]["metadata"]["source_conversation_id"] == 1


def test_get_diagnosis_context_handles_missing_diagnosis(monkeypatch):
    from app.models.user import User
    from app.models.message import Message
    from app.models.medical_record import MedicalRecord

    conversation = SimpleNamespace(
        id=1,
        patient_id=101,
        title="new session",
        chief_complaint="headache",
        status=SimpleNamespace(value="active"),
        created_at=datetime(2026, 4, 29, 8, 0, 0),
        updated_at=datetime(2026, 4, 29, 8, 30, 0),
        extra_metadata={},
    )
    patient = SimpleNamespace(
        id=101,
        username="patient_a",
        full_name=None,
        health_profile={},
    )

    fake_db = FakeDB(
        {
            User: [patient],
            Message: [],
            MedicalRecord: [],
        }
    )

    monkeypatch.setattr(ConversationService, "get_conversation_by_id", staticmethod(lambda conversation_id, db: conversation))

    context = ConversationService.get_diagnosis_context(1, fake_db)

    assert context["latest_diagnosis"] is None
    assert context["linked_reports"] == []
    assert context["medical_records"] == []


@pytest.mark.asyncio
async def test_diagnosis_context_route_rejects_unassigned_doctor(monkeypatch):
    conversation = SimpleNamespace(id=1, patient_id=101, doctor_id=999)

    monkeypatch.setattr(
        conversations_api.ConversationService,
        "get_conversation_by_id",
        staticmethod(lambda conversation_id, db: conversation),
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations_api.get_diagnosis_context(
            conversation_id=1,
            current_user={"id": 12, "role": "doctor"},
            db=object(),
        )

    assert exc_info.value.status_code == 403
