"""
Unified replay and patient-simulator environment for policy testing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ACTION_TO_SLOT = {
    "ask_main_symptom": "main_symptom",
    "ask_duration": "duration",
    "ask_symptom_location": "pain_location",
    "ask_accompanying_symptoms": "accompanying_symptoms",
    "ask_past_history": "past_history",
    "ask_medication_history": "medications",
    "suggest_exam": "recommended_exams",
}


class PolicyTrainingEnv:
    """Replay historical transitions or simulate patient information release."""

    def __init__(
        self,
        mode: str = "simulator",
        replay_entries: Optional[List[Dict[str, Any]]] = None,
        medical_data_path: Optional[Path] = None,
    ):
        self.mode = mode
        self.replay_entries = replay_entries or []
        self._replay_index = 0
        backend_dir = Path(__file__).resolve().parents[3]
        self.medical_data_path = Path(medical_data_path or (backend_dir / "data" / "medical.json"))
        self._cases = self._load_cases() if mode == "simulator" else []
        self._active_case: Optional[Dict[str, Any]] = None
        self._revealed_slots: Dict[str, Any] = {}

    def reset(self, case_index: int = 0) -> Dict[str, Any]:
        if self.mode == "replay":
            self._replay_index = 0
            return (self.replay_entries[0] if self.replay_entries else {}).get("state", {})

        if not self._cases:
            self._active_case = {
                "hidden_truth": {},
                "initial_observation": {"chief_complaint": "", "revealed_slots": {}},
            }
        else:
            self._active_case = self._cases[case_index % len(self._cases)]
        self._revealed_slots = {}
        return dict(self._active_case["initial_observation"])

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        if self.mode == "replay":
            if not self.replay_entries:
                return {}, 0.0, True, {}
            current = self.replay_entries[min(self._replay_index, len(self.replay_entries) - 1)]
            self._replay_index += 1
            done = self._replay_index >= len(self.replay_entries)
            next_state = current.get("next_state") or {}
            return next_state, float(current.get("reward", 0.0)), done, {
                "policy_type": current.get("policy_type")
            }

        action_name = str(action.get("action") or "")
        if action_name == "finish_consultation":
            coverage = len(self._revealed_slots) / max(1, len(self._active_case["hidden_truth"]))
            reward = 0.2 + coverage
            return self._build_observation(), reward, True, {"revealed_slots": list(self._revealed_slots.keys())}

        slot = ACTION_TO_SLOT.get(action_name)
        reward = -0.05
        if slot and slot in self._active_case["hidden_truth"]:
            self._revealed_slots[slot] = self._active_case["hidden_truth"][slot]
            reward = 0.8
        observation = self._build_observation()
        return observation, reward, False, {"revealed_slots": list(self._revealed_slots.keys())}

    def _build_observation(self) -> Dict[str, Any]:
        return {
            "chief_complaint": self._active_case["initial_observation"].get("chief_complaint", ""),
            "revealed_slots": dict(self._revealed_slots),
        }

    def _load_cases(self) -> List[Dict[str, Any]]:
        cases: List[Dict[str, Any]] = []
        if not self.medical_data_path.exists():
            return cases
        with self.medical_data_path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cases.append(self._row_to_case(index, row))
                if len(cases) >= 256:
                    break
        return cases

    def _row_to_case(self, index: int, row: Dict[str, Any]) -> Dict[str, Any]:
        symptoms = row.get("symptom") or []
        main_symptom = symptoms[0] if symptoms else row.get("name", "")
        hidden_truth = {
            "main_symptom": main_symptom,
            "duration": "unknown",
            "accompanying_symptoms": symptoms[1:4] if len(symptoms) > 1 else symptoms,
            "recommended_exams": row.get("check") or [],
            "recommended_department": (row.get("cure_department") or ["全科"])[0],
            "standard_diagnosis": row.get("name"),
            "medications": row.get("common_drug") or [],
        }
        return {
            "case_id": index,
            "hidden_truth": hidden_truth,
            "initial_observation": {
                "chief_complaint": main_symptom,
                "revealed_slots": {},
            },
        }


__all__ = ["PolicyTrainingEnv"]
