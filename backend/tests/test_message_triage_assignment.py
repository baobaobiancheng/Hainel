from types import SimpleNamespace

import pytest

from app.api.v1 import messages
from app.services.doctor_service import Department
from app.services.triage_service import TriageResult


class FakeDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_apply_triage_assignment_updates_metadata_and_assigns_doctor(monkeypatch):
    conversation = SimpleNamespace(
        id=42,
        chief_complaint="胸口不舒服",
        extra_metadata={},
    )
    assigned_doctor = SimpleNamespace(id=7, username="cardiology_doctor")

    monkeypatch.setattr(
        messages.triage_service,
        "triage",
        lambda **kwargs: TriageResult(
            requires_doctor=True,
            department=Department.CARDIOLOGY,
            department_name="心内科",
            urgency="normal",
            confidence=0.93,
            reason="心脏不适优先心内科",
        ),
    )
    monkeypatch.setattr(
        messages.DoctorService,
        "auto_assign_doctor",
        lambda conversation_id, department, db: assigned_doctor,
    )

    result, doctor = messages._apply_triage_assignment(
        conversation=conversation,
        diagnosis_result={"diagnosis": "建议心内科评估", "kg_context": {"summary": "胸闷相关知识"}},
        user_message="心脏不舒服",
        health_profile=None,
        structured_intake=None,
        linked_reports=[],
        db=FakeDB(),
    )

    assert result.department == Department.CARDIOLOGY
    assert doctor == assigned_doctor
    assert conversation.extra_metadata["triage"]["department_name"] == "心内科"
    assert conversation.extra_metadata["assigned_doctor_id"] == 7


@pytest.mark.asyncio
async def test_notify_assigned_doctor_sends_targeted_new_session(monkeypatch):
    sent = {}

    async def fake_push_to_doctor(doctor_id, message_type, data):
        sent["doctor_id"] = doctor_id
        sent["message_type"] = message_type
        sent["data"] = data

    monkeypatch.setattr(messages, "push_to_doctor", fake_push_to_doctor)

    await messages._notify_assigned_doctor(
        assigned_doctor=SimpleNamespace(id=7),
        conversation=SimpleNamespace(id=42, patient_id=3, chief_complaint="胸口不舒服"),
        triage_result=TriageResult(
            requires_doctor=True,
            department=Department.CARDIOLOGY,
            department_name="心内科",
            urgency="normal",
            confidence=0.93,
            reason="心脏不适优先心内科",
        ),
    )

    assert sent["doctor_id"] == 7
    assert sent["message_type"] == "new_session"
    assert sent["data"]["conversation_id"] == 42
    assert sent["data"]["department"] == "心内科"
    assert sent["data"]["triage_reason"] == "心脏不适优先心内科"
