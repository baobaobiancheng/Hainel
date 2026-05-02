"""
Heuristic reward calculator for offline policy optimization.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.config import settings


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


class RewardCalculator:
    """Calculates multi-dimensional rewards from conversation outcomes."""

    def __init__(self):
        self.weights = {
            "accuracy": settings.REWARD_ACCURACY_WEIGHT,
            "efficiency": settings.REWARD_EFFICIENCY_WEIGHT,
            "collaboration": settings.REWARD_COLLABORATION_WEIGHT,
            "compliance": settings.REWARD_COMPLIANCE_WEIGHT,
        }

    def calculate_reward(
        self,
        conversation: Optional[Any] = None,
        latest_diagnosis: Optional[Dict[str, Any]] = None,
        triage: Optional[Dict[str, Any]] = None,
        medical_record: Optional[Any] = None,
        trajectory_stats: Optional[Dict[str, Any]] = None,
        outcome_labels: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        latest_diagnosis = latest_diagnosis or {}
        triage = triage or {}
        trajectory_stats = trajectory_stats or {}
        outcome_labels = outcome_labels or {}

        accuracy = self._calculate_accuracy(triage, medical_record, outcome_labels, latest_diagnosis)
        efficiency = self._calculate_efficiency(conversation, trajectory_stats, latest_diagnosis)
        collaboration = self._calculate_collaboration(conversation, latest_diagnosis)
        compliance = self._calculate_compliance(triage, latest_diagnosis, outcome_labels)

        total = (
            accuracy * self.weights["accuracy"]
            + efficiency * self.weights["efficiency"]
            + collaboration * self.weights["collaboration"]
            + compliance * self.weights["compliance"]
        )
        return {
            "accuracy": round(accuracy, 4),
            "efficiency": round(efficiency, 4),
            "collaboration": round(collaboration, 4),
            "compliance": round(compliance, 4),
            "total_reward": round(total, 4),
        }

    def build_outcome_labels(
        self,
        conversation: Optional[Any] = None,
        triage: Optional[Dict[str, Any]] = None,
        medical_record: Optional[Any] = None,
        latest_diagnosis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        triage = triage or {}
        latest_diagnosis = latest_diagnosis or {}
        red_flags = latest_diagnosis.get("red_flags") or []
        return {
            "doctor_review_status": _enum_value(getattr(medical_record, "status", None)),
            "triage_department": triage.get("department_name"),
            "triage_urgency": triage.get("urgency"),
            "red_flag_count": len(red_flags),
            "conversation_status": _enum_value(getattr(conversation, "status", None)),
            "record_adopted": bool(medical_record),
        }

    def _calculate_accuracy(
        self,
        triage: Dict[str, Any],
        medical_record: Optional[Any],
        outcome_labels: Dict[str, Any],
        latest_diagnosis: Dict[str, Any],
    ) -> float:
        score = 0.2 if latest_diagnosis.get("content") else 0.0
        review_status = _enum_value(getattr(medical_record, "status", None))
        if review_status == "reviewed":
            score += 0.5
        elif review_status == "confirmed":
            score += 0.35
        elif medical_record:
            score += 0.2

        if triage.get("confidence") is not None:
            score += min(max(float(triage.get("confidence", 0.0)), 0.0), 1.0) * 0.2

        if outcome_labels.get("triage_correct") is True:
            score += 0.2
        if outcome_labels.get("diagnosis_record_consistent") is True:
            score += 0.1
        return max(-1.0, min(score, 1.0))

    def _calculate_efficiency(
        self,
        conversation: Optional[Any],
        trajectory_stats: Dict[str, Any],
        latest_diagnosis: Dict[str, Any],
    ) -> float:
        round_count = getattr(conversation, "round_count", None)
        if round_count is None:
            round_count = trajectory_stats.get("round_count", 0)
        duplicate_followups = int(trajectory_stats.get("duplicate_followups", 0))
        agents_used = latest_diagnosis.get("agents_used") or getattr(conversation, "agent_count", 1) or 1
        try:
            agents_used_count = int(str(agents_used).split("_", 1)[0])
        except ValueError:
            agents_used_count = 1

        score = 1.0
        if round_count > 8:
            score -= 0.5
        elif round_count > 5:
            score -= 0.2
        score -= min(0.3, duplicate_followups * 0.1)
        if agents_used_count > 5:
            score -= 0.2
        return max(-1.0, min(score, 1.0))

    def _calculate_collaboration(
        self,
        conversation: Optional[Any],
        latest_diagnosis: Dict[str, Any],
    ) -> float:
        complexity_level = str(_enum_value(getattr(conversation, "complexity_level", None)) or "").lower()
        collaboration_mode = str(
            _enum_value(getattr(conversation, "collaboration_mode", None)) or ""
        ).lower()
        agents_used = latest_diagnosis.get("agents_used") or getattr(conversation, "agent_count", 1) or 1
        try:
            agents_used_count = int(str(agents_used).split("_", 1)[0])
        except ValueError:
            agents_used_count = 1

        score = 0.4
        if complexity_level in {"low", "basic"} and collaboration_mode == "pcc":
            score = 1.0
        elif complexity_level in {"medium", "intermediate"} and collaboration_mode in {"mdt", "pcc"}:
            score = 0.8
        elif complexity_level in {"high", "advanced", "urgent"} and collaboration_mode in {"ict", "mdt"}:
            score = 0.8

        if agents_used_count > 7:
            score -= 0.3
        return max(-1.0, min(score, 1.0))

    def _calculate_compliance(
        self,
        triage: Dict[str, Any],
        latest_diagnosis: Dict[str, Any],
        outcome_labels: Dict[str, Any],
    ) -> float:
        score = 0.6
        red_flags = latest_diagnosis.get("red_flags") or []
        diagnosis_text = str(latest_diagnosis.get("content") or "").lower()
        action_checklist = latest_diagnosis.get("action_checklist") or {}
        when_to_seek_care = action_checklist.get("when_to_seek_care") or []
        urgency = str(triage.get("urgency") or "").lower()
        department = str(triage.get("department_code") or "").lower()

        if red_flags:
            if urgency == "emergency" or department == "emergency":
                score = 1.0
            else:
                score = -0.8

        if "绝对诊断" in diagnosis_text:
            score -= 0.3
        if not when_to_seek_care:
            score -= 0.1
        if outcome_labels.get("red_flag_handled_correctly") is False:
            score = min(score, -0.8)
        return max(-1.0, min(score, 1.0))


__all__ = ["RewardCalculator"]
