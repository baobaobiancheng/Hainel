import json

from app.services.doctor_service import Department
from app.services.triage_service import TriageService


class FakeTriageService(TriageService):
    def __init__(self, response):
        super().__init__()
        self.response = response
        self.called = False

    def _call_model(self, prompt: str) -> str:
        self.called = True
        return self.response


def test_triage_accepts_valid_department_json():
    service = FakeTriageService(json.dumps({
        "requires_doctor": True,
        "department_code": "cardiology",
        "department_name": "心内科",
        "urgency": "normal",
        "confidence": 0.91,
        "reason": "胸闷和心悸更符合心内科首诊范围",
    }, ensure_ascii=False))

    result = service.triage(symptoms="胸口不舒服，有时心跳加速")

    assert result.requires_doctor is True
    assert result.department == Department.CARDIOLOGY
    assert result.department_name == "心内科"
    assert result.confidence == 0.91


def test_triage_falls_back_to_general_for_invalid_department():
    service = FakeTriageService(json.dumps({
        "requires_doctor": True,
        "department_code": "unknown",
        "department_name": "未知科室",
        "urgency": "normal",
        "confidence": 0.95,
        "reason": "模型输出了不在白名单内的科室",
    }, ensure_ascii=False))

    result = service.triage(symptoms="身体不舒服")

    assert result.requires_doctor is True
    assert result.department == Department.GENERAL
    assert result.department_name == "全科"
    assert result.fallback_reason == "invalid_department"


def test_triage_routes_red_flags_to_emergency_without_model_call():
    service = FakeTriageService("{}")

    result = service.triage(symptoms="胸痛伴呼吸困难，快喘不上气")

    assert result.requires_doctor is True
    assert result.department == Department.EMERGENCY
    assert result.department_name == "急诊科"
    assert result.urgency == "emergency"
    assert service.called is False
