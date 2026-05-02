"""
Builds offline RL trajectories from conversations, messages, and records.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.evaluation.reward_calculator import RewardCalculator
from app.models.conversation import Conversation
from app.models.medical_record import MedicalRecord
from app.models.message import Message, MessageRole
from app.models.user import User


FOLLOWUP_ACTION_PATTERNS = [
    ("ask_duration", ["多久", "多长时间", "持续", "几天"]),
    ("ask_symptom_location", ["哪里", "部位", "位置", "哪一侧"]),
    ("ask_trigger", ["诱因", "原因", "什么时候开始", "什么情况下"]),
    ("ask_accompanying_symptoms", ["伴随", "还有没有", "是否有", "有没有"]),
    ("ask_medication_history", ["用药", "吃药", "服药"]),
    ("ask_past_history", ["既往", "病史", "慢性病", "过敏史"]),
    ("suggest_exam", ["检查", "化验", "复查", "检验"]),
]


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _metadata(value: Any) -> Dict[str, Any]:
    extra = getattr(value, "extra_metadata", None)
    if isinstance(extra, dict):
        return extra
    if isinstance(value, dict):
        return value
    return {}


class TrajectoryBuilder:
    """Reconstructs discrete decision trajectories from historical logs."""

    def __init__(self, reward_calculator: Optional[RewardCalculator] = None):
        self.reward_calculator = reward_calculator or RewardCalculator()

    def build_all_trajectories(
        self,
        db: Session,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = db.query(Conversation).order_by(Conversation.created_at.desc())
        if limit:
            query = query.limit(limit)
        conversations = query.all()
        trajectories: List[Dict[str, Any]] = []
        for conversation in conversations:
            patient = db.query(User).filter(User.id == conversation.patient_id).first()
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conversation.id)
                .order_by(Message.created_at, Message.id)
                .all()
            )
            records = (
                db.query(MedicalRecord)
                .filter(MedicalRecord.conversation_id == conversation.id)
                .order_by(MedicalRecord.updated_at.desc(), MedicalRecord.id.desc())
                .all()
            )
            trajectories.append(
                self.build_conversation_trajectory(
                    conversation=conversation,
                    patient=patient,
                    messages=messages,
                    medical_records=records,
                )
            )
        return trajectories

    def build_conversation_trajectory(
        self,
        conversation: Any,
        patient: Optional[Any],
        messages: List[Any],
        medical_records: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        medical_records = medical_records or []
        conv_meta = _metadata(conversation)
        health_profile = getattr(patient, "health_profile", None)
        if not isinstance(health_profile, dict):
            health_profile = {}

        linked_reports = self._extract_linked_reports(messages)
        assistant_messages = [m for m in messages if _enum_value(getattr(m, "role", None)) == MessageRole.ASSISTANT.value]
        latest_diagnosis_message = self._select_latest_diagnosis_message(assistant_messages)
        latest_diagnosis = _metadata(latest_diagnosis_message)
        triage = conv_meta.get("triage") or latest_diagnosis.get("triage") or {}
        medical_record = medical_records[0] if medical_records else None

        transitions: List[Dict[str, Any]] = []
        previous_actions: List[str] = []

        routing_action = self._infer_routing_action(conversation)
        if routing_action:
            state = self._build_state(
                conversation,
                health_profile,
                conv_meta,
                linked_reports,
                latest_diagnosis,
                previous_actions,
            )
            transitions.append(
                self._transition(
                    conversation_id=conversation.id,
                    policy_type="routing",
                    state=state,
                    action=routing_action,
                    done=False,
                    source_message_id=None,
                )
            )
            previous_actions.append(routing_action["action"])

        for message in assistant_messages:
            followup_action = self._infer_followup_action(message, latest_diagnosis_message)
            if not followup_action:
                continue
            state = self._build_state(
                conversation,
                health_profile,
                conv_meta,
                linked_reports,
                latest_diagnosis,
                previous_actions,
            )
            transitions.append(
                self._transition(
                    conversation_id=conversation.id,
                    policy_type="followup",
                    state=state,
                    action=followup_action,
                    done=False,
                    source_message_id=getattr(message, "id", None),
                )
            )
            previous_actions.append(followup_action["action"])

        if triage:
            state = self._build_state(
                conversation,
                health_profile,
                conv_meta,
                linked_reports,
                latest_diagnosis,
                previous_actions,
            )
            transitions.append(
                self._transition(
                    conversation_id=conversation.id,
                    policy_type="triage",
                    state=state,
                    action={
                        "action": "assign_department",
                        "requires_doctor": bool(triage.get("requires_doctor", True)),
                        "department_code": triage.get("department_code"),
                        "department_name": triage.get("department_name"),
                        "urgency": triage.get("urgency"),
                    },
                    done=True,
                    source_message_id=getattr(latest_diagnosis_message, "id", None),
                )
            )

        trajectory_stats = {
            "round_count": getattr(conversation, "round_count", 0) or 0,
            "duplicate_followups": self._count_duplicate_actions(previous_actions),
        }
        reward_breakdown = self.reward_calculator.calculate_reward(
            conversation=conversation,
            latest_diagnosis={
                "content": getattr(latest_diagnosis_message, "content", ""),
                "red_flags": latest_diagnosis.get("red_flags") or [],
                "action_checklist": latest_diagnosis.get("action_checklist"),
                "agents_used": latest_diagnosis.get("agents_used"),
            },
            triage=triage,
            medical_record=medical_record,
            trajectory_stats=trajectory_stats,
            outcome_labels=self.reward_calculator.build_outcome_labels(
                conversation=conversation,
                triage=triage,
                medical_record=medical_record,
                latest_diagnosis=latest_diagnosis,
            ),
        )
        for index, item in enumerate(transitions):
            item["reward"] = reward_breakdown["total_reward"]
            item["reward_breakdown"] = reward_breakdown
            item["next_state"] = {"step_index": index + 1, "transition_count": len(transitions)}

        return {
            "conversation_id": conversation.id,
            "transitions": transitions,
            "reward_breakdown": reward_breakdown,
            "outcome_labels": self.reward_calculator.build_outcome_labels(
                conversation=conversation,
                triage=triage,
                medical_record=medical_record,
                latest_diagnosis=latest_diagnosis,
            ),
        }

    def _build_state(
        self,
        conversation: Any,
        health_profile: Dict[str, Any],
        conv_meta: Dict[str, Any],
        linked_reports: List[Dict[str, Any]],
        latest_diagnosis: Dict[str, Any],
        previous_actions: List[str],
    ) -> Dict[str, Any]:
        kg_context = latest_diagnosis.get("kg_context") or {}
        kg_summary = ""
        if isinstance(kg_context, dict):
            kg_summary = str(kg_context.get("summary") or "")
        intake = conv_meta.get("structured_intake") or {}
        main_symptom = ""
        if isinstance(intake, dict):
            main_symptom = str(intake.get("main_symptom") or intake.get("chief_complaint") or "")

        return {
            "chief_complaint": getattr(conversation, "chief_complaint", None),
            "main_symptom": main_symptom,
            "complexity_level": str(_enum_value(getattr(conversation, "complexity_level", None)) or ""),
            "collaboration_mode": str(_enum_value(getattr(conversation, "collaboration_mode", None)) or ""),
            "round_count": getattr(conversation, "round_count", 0) or 0,
            "message_count": getattr(conversation, "message_count", 0) or 0,
            "report_count": len(linked_reports),
            "red_flag_count": len(latest_diagnosis.get("red_flags") or []),
            "kg_summary": kg_summary[:240],
            "has_health_profile": bool(health_profile),
            "previous_actions": list(previous_actions[-5:]),
            "requires_doctor": bool((conv_meta.get("triage") or {}).get("requires_doctor", False)),
        }

    def _transition(
        self,
        conversation_id: int,
        policy_type: str,
        state: Dict[str, Any],
        action: Dict[str, Any],
        done: bool,
        source_message_id: Optional[int],
    ) -> Dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "policy_type": policy_type,
            "state": state,
            "action": action,
            "reward": 0.0,
            "done": done,
            "source_message_id": source_message_id,
            "feedback_source": "replay",
        }

    def _infer_routing_action(self, conversation: Any) -> Optional[Dict[str, Any]]:
        complexity_level = str(_enum_value(getattr(conversation, "complexity_level", None)) or "").lower()
        collaboration_mode = str(_enum_value(getattr(conversation, "collaboration_mode", None)) or "").lower()
        if not complexity_level and not collaboration_mode:
            return None
        return {
            "action": f"route_to_{collaboration_mode or 'pcc'}",
            "complexity_level": complexity_level or "unknown",
            "collaboration_mode": collaboration_mode or "pcc",
        }

    def _infer_followup_action(
        self,
        message: Any,
        latest_diagnosis_message: Optional[Any],
    ) -> Optional[Dict[str, Any]]:
        content = str(getattr(message, "content", "") or "")
        if latest_diagnosis_message is not None and getattr(message, "id", None) == getattr(
            latest_diagnosis_message, "id", None
        ):
            return {"action": "finish_consultation", "source": "diagnosis_response"}

        lowered = content.lower()
        for action_name, patterns in FOLLOWUP_ACTION_PATTERNS:
            if any(pattern in lowered for pattern in patterns):
                return {"action": action_name, "source": "assistant_followup"}
        return None

    def _extract_linked_reports(self, messages: List[Any]) -> List[Dict[str, Any]]:
        reports: List[Dict[str, Any]] = []
        for message in messages:
            message_type = str(_enum_value(getattr(message, "message_type", None)) or "").lower()
            if message_type != "file":
                continue
            metadata = _metadata(message)
            ocr_result = metadata.get("ocr_result") or {}
            reports.append(
                {
                    "message_id": getattr(message, "id", None),
                    "file_name": getattr(message, "file_name", None),
                    "file_type": getattr(message, "file_type", None),
                    "report_type": metadata.get("report_type"),
                    "ocr_text": str(ocr_result.get("text") or ""),
                }
            )
        return reports[:3]

    def _select_latest_diagnosis_message(self, messages: List[Any]) -> Optional[Any]:
        if not messages:
            return None
        for message in reversed(messages):
            metadata = _metadata(message)
            if metadata.get("action_checklist") or metadata.get("analysis_type") or metadata.get("triage"):
                return message
        return messages[-1]

    @staticmethod
    def _count_duplicate_actions(actions: List[str]) -> int:
        seen = set()
        duplicates = 0
        for action in actions:
            if action in seen:
                duplicates += 1
            else:
                seen.add(action)
        return duplicates


__all__ = ["TrajectoryBuilder"]
