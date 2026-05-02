"""
Persistent registry for offline policy snapshots and training runs.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PolicyRegistry:
    """Stores policy versions, active versions, and training runs on disk."""

    def __init__(self, base_dir: Optional[Path] = None):
        backend_dir = Path(__file__).resolve().parents[3]
        self.base_dir = Path(base_dir or (backend_dir / "data" / "policy_registry"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.base_dir / "registry.json"

    def _load(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            return {"active": {}, "versions": {}, "runs": {}, "datasets": {}}
        with self.registry_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload.setdefault("active", {})
        payload.setdefault("versions", {})
        payload.setdefault("runs", {})
        payload.setdefault("datasets", {})
        return payload

    def _save(self, payload: Dict[str, Any]) -> None:
        with self.registry_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def start_run(
        self,
        policy_type: str,
        params: Optional[Dict[str, Any]] = None,
        status: str = "running",
    ) -> str:
        registry = self._load()
        run_id = uuid.uuid4().hex
        registry["runs"][run_id] = {
            "run_id": run_id,
            "policy_type": policy_type,
            "status": status,
            "params": params or {},
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        self._save(registry)
        return run_id

    def update_run(self, run_id: str, **updates: Any) -> Dict[str, Any]:
        registry = self._load()
        run = registry["runs"].setdefault(
            run_id,
            {
                "run_id": run_id,
                "status": "unknown",
                "created_at": _utc_now(),
            },
        )
        run.update(updates)
        run["updated_at"] = _utc_now()
        registry["runs"][run_id] = run
        self._save(registry)
        return run

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._load()["runs"].get(run_id)

    def register_dataset(
        self,
        *,
        agent_type: str,
        policy_types: List[str],
        summary: Dict[str, Any],
        export_files: Dict[str, str],
        created_by: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        registry = self._load()
        dataset_id = f"dataset-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        record = {
            "dataset_id": dataset_id,
            "agent_type": agent_type,
            "policy_types": list(policy_types),
            "summary": summary or {},
            "export_files": export_files or {},
            "created_at": _utc_now(),
            "created_by": created_by,
            "metadata": metadata or {},
        }
        registry["datasets"][dataset_id] = record
        self._save(registry)
        return record

    def list_datasets(self) -> List[Dict[str, Any]]:
        datasets = list(self._load()["datasets"].values())
        return sorted(datasets, key=lambda item: item.get("created_at", ""), reverse=True)

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        return self._load()["datasets"].get(dataset_id)

    def register_policy(
        self,
        policy_type: str,
        snapshot: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        activate: bool = False,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        registry = self._load()
        version = (
            f"{policy_type}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            f"-{uuid.uuid4().hex[:8]}"
        )
        policy_dir = self.base_dir / policy_type
        policy_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = policy_dir / f"{version}.json"
        with snapshot_path.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)

        record = {
            "policy_type": policy_type,
            "version": version,
            "snapshot_path": str(snapshot_path),
            "created_at": _utc_now(),
            "metrics": metrics or {},
            "metadata": metadata or {},
        }
        registry["versions"].setdefault(policy_type, []).append(record)
        if activate or policy_type not in registry["active"]:
            registry["active"][policy_type] = version

        if run_id:
            registry["runs"][run_id] = {
                **registry["runs"].get(run_id, {}),
                "run_id": run_id,
                "policy_type": policy_type,
                "status": "completed",
                "version": version,
                "metrics": metrics or {},
                "updated_at": _utc_now(),
            }

        self._save(registry)
        return record

    def list_policy_versions(self, policy_type: str) -> List[Dict[str, Any]]:
        versions = list(self._load()["versions"].get(policy_type, []))
        return sorted(versions, key=lambda item: item.get("created_at", ""), reverse=True)

    def get_policy_version(
        self,
        policy_type: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        registry = self._load()
        target_version = version or registry["active"].get(policy_type)
        if not target_version:
            return None
        for record in registry["versions"].get(policy_type, []):
            if record["version"] == target_version:
                snapshot_path = Path(record["snapshot_path"])
                if snapshot_path.exists():
                    with snapshot_path.open("r", encoding="utf-8") as handle:
                        snapshot = json.load(handle)
                    return {**record, "snapshot": snapshot}
                return record
        return None

    def get_active_policy(self, policy_type: str) -> Optional[Dict[str, Any]]:
        return self.get_policy_version(policy_type)

    def activate_policy(self, policy_type: str, version: str) -> Dict[str, Any]:
        registry = self._load()
        versions = registry["versions"].get(policy_type, [])
        if not any(item["version"] == version for item in versions):
            raise ValueError(f"Policy version not found: {policy_type}/{version}")
        registry["active"][policy_type] = version
        self._save(registry)
        policy = self.get_policy_version(policy_type, version)
        if not policy:
            raise ValueError(f"Policy snapshot missing: {policy_type}/{version}")
        return policy

    def recommend(self, policy_type: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        policy = self.get_active_policy(policy_type)
        if not policy or "snapshot" not in policy:
            return None

        snapshot = policy["snapshot"]
        feature_keys = snapshot.get("feature_keys") or []
        signature = self._build_signature(state, feature_keys)
        state_values = snapshot.get("policy", {}).get("state_action_values", {})
        recommended = state_values.get(signature)
        if recommended:
            ranked = sorted(
                recommended.items(),
                key=lambda item: float(item[1].get("score", 0.0)),
                reverse=True,
            )
            if ranked:
                action_payload = ranked[0][1].get("action")
                if isinstance(action_payload, dict):
                    return action_payload

        default_action = snapshot.get("default_action")
        return default_action if isinstance(default_action, dict) else None

    @staticmethod
    def _build_signature(state: Dict[str, Any], feature_keys: List[str]) -> str:
        payload = {key: state.get(key) for key in feature_keys}
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


__all__ = ["PolicyRegistry"]
