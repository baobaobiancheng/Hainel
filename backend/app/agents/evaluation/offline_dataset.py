"""
Offline dataset builder for replay-based policy training.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.evaluation.trajectory_builder import TrajectoryBuilder


AGENT_TYPE_TO_POLICY_TYPES = {
    "all": ["routing", "followup", "triage"],
    "moderator": ["routing"],
    "pcc": ["routing", "followup"],
    "mdt": ["routing", "followup"],
    "ict": ["routing", "followup"],
    "triage": ["triage"],
    "routing": ["routing"],
    "followup": ["followup"],
}


class OfflineDatasetBuilder:
    """Builds train/val/test splits and future fine-tuning exports."""

    def __init__(self, trajectory_builder: Optional[TrajectoryBuilder] = None):
        self.trajectory_builder = trajectory_builder or TrajectoryBuilder()
        backend_dir = Path(__file__).resolve().parents[3]
        self.export_dir = backend_dir / "data" / "rl_exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        db: Session,
        agent_type: str = "all",
        limit: Optional[int] = None,
        policy_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        selected_policy_types = policy_types or AGENT_TYPE_TO_POLICY_TYPES.get(
            (agent_type or "all").lower(),
            ["routing", "followup", "triage"],
        )
        trajectories = self.trajectory_builder.build_all_trajectories(db, limit=limit)
        entries: List[Dict[str, Any]] = []
        for trajectory in trajectories:
            for transition in trajectory.get("transitions", []):
                if transition.get("policy_type") in selected_policy_types:
                    entries.append(transition)

        splits = self._split_entries(entries)
        export_samples = self._build_export_samples(entries)
        export_files = self._write_exports(agent_type, splits, export_samples)
        return {
            "agent_type": agent_type,
            "policy_types": selected_policy_types,
            "entries": entries,
            "splits": splits,
            "summary": {
                "total_entries": len(entries),
                "train_size": len(splits["train"]),
                "val_size": len(splits["val"]),
                "test_size": len(splits["test"]),
            },
            "export_samples": export_samples,
            "export_files": export_files,
        }

    @staticmethod
    def _split_entries(entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        if not entries:
            return {"train": [], "val": [], "test": []}
        total = len(entries)
        train_end = max(1, int(total * 0.7))
        val_end = max(train_end + 1, int(total * 0.85)) if total > 2 else total
        return {
            "train": entries[:train_end],
            "val": entries[train_end:val_end],
            "test": entries[val_end:],
        }

    @staticmethod
    def _build_export_samples(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        samples: List[Dict[str, Any]] = []
        for entry in entries:
            samples.append(
                {
                    "policy_type": entry.get("policy_type"),
                    "prompt": json.dumps(
                        {
                            "policy_type": entry.get("policy_type"),
                            "state": entry.get("state"),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "completion": json.dumps(entry.get("action"), ensure_ascii=False, sort_keys=True),
                    "reward": entry.get("reward", 0.0),
                }
            )
        return samples

    def _write_exports(
        self,
        agent_type: str,
        splits: Dict[str, List[Dict[str, Any]]],
        export_samples: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        stamp = agent_type.lower()
        export_files: Dict[str, str] = {}
        for split_name, items in splits.items():
            path = self.export_dir / f"{stamp}_{split_name}.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for item in items:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            export_files[split_name] = str(path)

        samples_path = self.export_dir / f"{stamp}_sft_samples.jsonl"
        with samples_path.open("w", encoding="utf-8") as handle:
            for item in export_samples:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        export_files["export_samples"] = str(samples_path)
        return export_files


__all__ = ["OfflineDatasetBuilder", "AGENT_TYPE_TO_POLICY_TYPES"]
