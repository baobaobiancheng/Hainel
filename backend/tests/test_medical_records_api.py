from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import medical_records as medical_records_api
from app.models.medical_record import MedicalRecordStatus


class FakeDB:
    def commit(self):
        return None

    def refresh(self, record):
        return None


@pytest.mark.asyncio
async def test_doctor_can_read_draft_record_detail():
    record = SimpleNamespace(
        id=11,
        patient_id=101,
        conversation_id=9,
        reviewed_by=None,
        title="draft record",
        chief_complaint="palpitations",
        present_illness="2 days",
        past_history=None,
        physical_examination=None,
        auxiliary_examination=None,
        diagnosis=[],
        treatment_plan=None,
        medications=None,
        medical_advice=None,
        follow_up=None,
        status=MedicalRecordStatus.DRAFT,
        content=None,
        agent_name=None,
        agent_id=None,
        review_comment=None,
        reviewed_at=None,
        archived_at=None,
        extra_metadata={"source": "ai_draft"},
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 5, 0),
        patient=SimpleNamespace(full_name="Alice", username="alice"),
        conversation=SimpleNamespace(title="session title", chief_complaint="palpitations"),
    )

    medical_records_api.MedicalRecordService.get_medical_record_by_id = staticmethod(lambda record_id, db: record)

    response = await medical_records_api.get_medical_record(
        record_id=11,
        current_user={"id": 12, "role": "doctor"},
        db=object(),
    )

    assert response.id == 11
    assert response.status == MedicalRecordStatus.DRAFT.value
    assert response.patient_name == "Alice"


@pytest.mark.asyncio
async def test_doctor_cannot_read_reviewed_record_of_other_doctor():
    record = SimpleNamespace(
        id=12,
        patient_id=101,
        conversation_id=9,
        reviewed_by=99,
        title="reviewed record",
        chief_complaint="palpitations",
        present_illness="2 days",
        past_history=None,
        physical_examination=None,
        auxiliary_examination=None,
        diagnosis=[],
        treatment_plan=None,
        medications=None,
        medical_advice=None,
        follow_up=None,
        status=MedicalRecordStatus.REVIEWED,
        content=None,
        agent_name=None,
        agent_id=None,
        review_comment=None,
        reviewed_at=None,
        archived_at=None,
        extra_metadata={},
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 5, 0),
        patient=None,
        conversation=None,
    )

    medical_records_api.MedicalRecordService.get_medical_record_by_id = staticmethod(lambda record_id, db: record)

    with pytest.raises(HTTPException) as exc_info:
        await medical_records_api.get_medical_record(
            record_id=12,
            current_user={"id": 12, "role": "doctor"},
            db=object(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_confirmed_record_can_be_archived():
    record = SimpleNamespace(
        id=13,
        patient_id=101,
        conversation_id=9,
        reviewed_by=None,
        title="confirmed record",
        chief_complaint="palpitations",
        present_illness="2 days",
        past_history=None,
        physical_examination=None,
        auxiliary_examination=None,
        diagnosis=[{"name": "palpitations", "type": "primary"}],
        treatment_plan="follow up",
        medications=None,
        medical_advice="seek care if worse",
        follow_up=None,
        status=MedicalRecordStatus.CONFIRMED,
        content=None,
        agent_name=None,
        agent_id=None,
        review_comment=None,
        reviewed_at=None,
        archived_at=None,
        extra_metadata={},
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 5, 0),
        patient=None,
        conversation=None,
        mark_as_archived=lambda: setattr(record, "status", MedicalRecordStatus.ARCHIVED),
    )

    medical_records_api.MedicalRecordService.get_medical_record_by_id = staticmethod(lambda record_id, db: record)

    response = await medical_records_api.archive_medical_record(record_id=13, db=FakeDB())

    assert response.status == MedicalRecordStatus.ARCHIVED.value


@pytest.mark.asyncio
async def test_quality_check_blocks_record_without_diagnosis_on_confirm():
    record = SimpleNamespace(
        id=14,
        patient_id=101,
        conversation_id=9,
        reviewed_by=None,
        title="draft record",
        chief_complaint="palpitations",
        present_illness="2 days",
        past_history=None,
        physical_examination=None,
        auxiliary_examination=None,
        diagnosis=[],
        treatment_plan="follow up",
        medications=None,
        medical_advice="seek care if worse",
        follow_up=None,
        status=MedicalRecordStatus.DRAFT,
        content=None,
        agent_name=None,
        agent_id=None,
        review_comment=None,
        reviewed_at=None,
        archived_at=None,
        extra_metadata={},
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 5, 0),
        patient=None,
        conversation=None,
    )

    medical_records_api.MedicalRecordService.get_medical_record_by_id = staticmethod(lambda record_id, db: record)

    with pytest.raises(HTTPException) as exc_info:
        await medical_records_api.update_medical_record_status(
            record_id=14,
            status_data=SimpleNamespace(status=MedicalRecordStatus.CONFIRMED.value),
            db=FakeDB(),
        )

    assert exc_info.value.status_code == 400
