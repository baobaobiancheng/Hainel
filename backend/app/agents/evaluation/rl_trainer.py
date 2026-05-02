"""
Lightweight offline trainer for discrete medical agent policies.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.agents.evaluation.policy_registry import PolicyRegistry


POLICY_FEATURE_KEYS = {
    "routing": ["chief_complaint", "main_symptom", "red_flag_count", "report_count"],
    "followup": ["chief_complaint", "main_symptom", "round_count", "previous_actions"],
    "triage": ["chief_complaint", "main_symptom", "red_flag_count", "requires_doctor"],
}


@dataclass
class TrainingResult:
    run_id: str
    policy_type: str
    policy_version: str
    snapshot: Dict[str, Any]
    metrics: Dict[str, Any]


class RLTrainer:
    """Frequency and reward-based offline trainer for discrete policy actions."""

    def __init__(self, agent_type: str, registry: Optional[PolicyRegistry] = None):
        self.agent_type = agent_type
        self.registry = registry or PolicyRegistry()

    def train(
        self,
        data: List[Dict[str, Any]],
        policy_type: str,
        batch_size: int = 32,
        learning_rate: float = 1e-5,
        max_epochs: int = 10,
        activate: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        run_params: Optional[Dict[str, Any]] = None,
    ) -> TrainingResult:
        metadata = metadata or {}
        run_params = run_params or {}
        if run_id is None:
            run_id = self.registry.start_run(
                policy_type,
                params={
                    "agent_type": self.agent_type,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate,
                    "max_epochs": max_epochs,
                    **run_params,
                },
            )
        else:
            existing_run = self.registry.get_run(run_id) or {}
            merged_params = {**(existing_run.get("params", {}) or {}), **run_params}
            self.registry.update_run(run_id, status="running", params=merged_params)

        feature_keys = POLICY_FEATURE_KEYS.get(policy_type, ["chief_complaint", "round_count"])
        state_action_values: Dict[str, Dict[str, Dict[str, Any]]] = {}
        global_counts: Dict[str, Dict[str, Any]] = {}

        for entry in data:
            signature = self._state_signature(entry.get("state", {}), feature_keys)
            action = entry.get("action") or {}
            action_key = self._action_key(action)
            reward = float(entry.get("reward", 0.0))

            global_counts.setdefault(action_key, {"count": 0, "reward": 0.0, "action": action})
            global_counts[action_key]["count"] += 1
            global_counts[action_key]["reward"] += reward

            state_action_values.setdefault(signature, {})
            bucket = state_action_values[signature].setdefault(
                action_key,
                {"count": 0, "reward": 0.0, "score": 0.0, "action": action},
            )
            bucket["count"] += 1
            bucket["reward"] += reward

        for state_bucket in state_action_values.values():
            for bucket in state_bucket.values():
                bucket["score"] = bucket["reward"] / max(1, bucket["count"])

        default_action = {}
        if global_counts:
            ranked = sorted(
                global_counts.values(),
                key=lambda item: (item["reward"] / max(1, item["count"]), item["count"]),
                reverse=True,
            )
            default_action = ranked[0]["action"]

        snapshot = {
            "policy_type": policy_type,
            "agent_type": self.agent_type,
            "trained_at": metadata.get("trained_at"),
            "feature_keys": feature_keys,
            "default_action": default_action,
            "policy": {"state_action_values": state_action_values},
            "training_params": {
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "max_epochs": max_epochs,
            },
        }
        metrics = self.evaluate_snapshot(snapshot, data)
        record = self.registry.register_policy(
            policy_type=policy_type,
            snapshot=snapshot,
            metrics=metrics,
            metadata=metadata,
            activate=activate,
            run_id=run_id,
        )
        metrics["policy_version"] = record["version"]
        self.registry.update_run(
            run_id,
            status="completed",
            metrics=metrics,
            version=record["version"],
            dataset_id=run_params.get("dataset_id"),
        )
        return TrainingResult(
            run_id=run_id,
            policy_type=policy_type,
            policy_version=record["version"],
            snapshot=snapshot,
            metrics=metrics,
        )

    def evaluate(
        self,
        policy_type: str,
        data: List[Dict[str, Any]],
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        policy = self.registry.get_policy_version(policy_type, version)
        if not policy or "snapshot" not in policy:
            return {"policy_type": policy_type, "sample_count": len(data), "available": False}
        metrics = self.evaluate_snapshot(policy["snapshot"], data)
        metrics["policy_version"] = policy["version"]
        return metrics

    def recommend(
        self,
        policy_type: str,
        state: Dict[str, Any],
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        policy = self.registry.get_policy_version(policy_type, version)
        if not policy or "snapshot" not in policy:
            return None
        return self._recommend_from_snapshot(policy["snapshot"], state)

    def evaluate_snapshot(self, snapshot: Dict[str, Any], data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not data:
            return {
                "policy_type": snapshot.get("policy_type"),
                "sample_count": 0,
                "action_match_rate": 0.0,
                "avg_reward": 0.0,
                "weighted_reward": 0.0,
            }

        matches = 0
        total_reward = 0.0
        selected_reward = 0.0
        for entry in data:
            actual_action = entry.get("action") or {}
            recommended_action = self._recommend_from_snapshot(snapshot, entry.get("state", {})) or {}
            if self._action_key(actual_action) == self._action_key(recommended_action):
                matches += 1
                selected_reward += float(entry.get("reward", 0.0))
            total_reward += float(entry.get("reward", 0.0))

        sample_count = len(data)
        return {
            "policy_type": snapshot.get("policy_type"),
            "sample_count": sample_count,
            "action_match_rate": round(matches / sample_count, 4),
            "avg_reward": round(total_reward / sample_count, 4),
            "weighted_reward": round(selected_reward / sample_count, 4),
            "baseline_reward": round(total_reward / sample_count, 4),
        }

    def _recommend_from_snapshot(self, snapshot: Dict[str, Any], state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        feature_keys = snapshot.get("feature_keys") or []
        signature = self._state_signature(state, feature_keys)
        candidates = snapshot.get("policy", {}).get("state_action_values", {}).get(signature)
        if not candidates:
            return snapshot.get("default_action")
        ranked = sorted(candidates.values(), key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return ranked[0].get("action") if ranked else snapshot.get("default_action")

    @staticmethod
    def _action_key(action: Dict[str, Any]) -> str:
        return json.dumps(action, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _state_signature(state: Dict[str, Any], feature_keys: List[str]) -> str:
        payload = {key: state.get(key) for key in feature_keys}
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


__all__ = ["RLTrainer", "TrainingResult", "POLICY_FEATURE_KEYS"]
