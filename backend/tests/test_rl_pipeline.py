import shutil
from pathlib import Path
from types import SimpleNamespace

from app.agents.evaluation.offline_dataset import OfflineDatasetBuilder
from app.agents.evaluation.policy_env import PolicyTrainingEnv
from app.agents.evaluation.policy_registry import PolicyRegistry
from app.agents.evaluation.reward_calculator import RewardCalculator
from app.agents.evaluation.rl_trainer import RLTrainer
from app.agents.evaluation.trajectory_builder import TrajectoryBuilder


def _workspace_tmp(name: str) -> Path:
    path = Path(__file__).resolve().parents[1] / ".test_tmp" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_trajectory_builder_recovers_routing_followup_and_triage():
    conversation = SimpleNamespace(
        id=1,
        chief_complaint="胸闷两天",
        complexity_level=SimpleNamespace(value="medium"),
        collaboration_mode=SimpleNamespace(value="mdt"),
        round_count=4,
        message_count=6,
        extra_metadata={"structured_intake": {"main_symptom": "胸闷"}, "triage": {"urgency": "urgent"}},
    )
    patient = SimpleNamespace(health_profile={"gender": "female"})
    messages = [
        SimpleNamespace(
            id=10,
            role="ASSISTANT",
            message_type="text",
            content="请问症状持续多久了？",
            extra_metadata={},
        ),
        SimpleNamespace(
            id=11,
            role="ASSISTANT",
            message_type="text",
            content="建议心内科尽快就诊",
            extra_metadata={
                "analysis_type": "primary",
                "red_flags": [{"category": "胸痛"}],
                "action_checklist": {"when_to_seek_care": ["立即就医"]},
                "triage": {
                    "requires_doctor": True,
                    "department_code": "cardiology",
                    "department_name": "心内科",
                    "urgency": "urgent",
                    "confidence": 0.9,
                },
            },
        ),
    ]
    records = [SimpleNamespace(status=SimpleNamespace(value="reviewed"), extra_metadata={})]

    trajectory = TrajectoryBuilder().build_conversation_trajectory(
        conversation=conversation,
        patient=patient,
        messages=messages,
        medical_records=records,
    )

    policy_types = [item["policy_type"] for item in trajectory["transitions"]]
    assert "routing" in policy_types
    assert "followup" in policy_types
    assert "triage" in policy_types
    assert trajectory["reward_breakdown"]["total_reward"] != 0


def test_reward_calculator_penalizes_missed_red_flag():
    calculator = RewardCalculator()
    safe = calculator.calculate_reward(
        latest_diagnosis={
            "content": "建议急诊处理",
            "red_flags": [{"category": "胸痛"}],
            "action_checklist": {"when_to_seek_care": ["立即就医"]},
        },
        triage={"urgency": "emergency", "department_code": "emergency", "confidence": 1.0},
        medical_record=SimpleNamespace(status=SimpleNamespace(value="reviewed")),
    )
    risky = calculator.calculate_reward(
        latest_diagnosis={
            "content": "先观察",
            "red_flags": [{"category": "胸痛"}],
            "action_checklist": {"when_to_seek_care": ["必要时复诊"]},
        },
        triage={"urgency": "normal", "department_code": "general", "confidence": 0.3},
        medical_record=SimpleNamespace(status=SimpleNamespace(value="draft")),
    )

    assert safe["compliance"] > risky["compliance"]
    assert safe["total_reward"] > risky["total_reward"]


def test_policy_training_env_reveals_slots_only_after_matching_action():
    tmp_path = _workspace_tmp("policy_env")
    data_path = tmp_path / "medical.json"
    data_path.write_text(
        '{"name":"心绞痛","symptom":["胸痛","气短"],"check":["心电图"],"cure_department":["心内科"]}\n',
        encoding="utf-8",
    )
    env = PolicyTrainingEnv(mode="simulator", medical_data_path=data_path)
    state = env.reset()
    assert state["revealed_slots"] == {}

    next_state, reward, done, _ = env.step({"action": "ask_duration"})
    assert "duration" in next_state["revealed_slots"]
    assert reward > 0
    assert not done

    next_state, reward, done, _ = env.step({"action": "finish_consultation"})
    assert done
    assert reward > 0


def test_rl_trainer_and_registry_round_trip():
    tmp_path = _workspace_tmp("policy_registry")
    registry = PolicyRegistry(base_dir=tmp_path / "policy_registry")
    trainer = RLTrainer(agent_type="all", registry=registry)
    data = [
        {
            "policy_type": "triage",
            "state": {"chief_complaint": "胸痛", "main_symptom": "胸痛", "red_flag_count": 1, "requires_doctor": True},
            "action": {
                "action": "assign_department",
                "requires_doctor": True,
                "department_code": "emergency",
                "urgency": "emergency",
            },
            "reward": 5.0,
        },
        {
            "policy_type": "triage",
            "state": {"chief_complaint": "皮疹", "main_symptom": "皮疹", "red_flag_count": 0, "requires_doctor": False},
            "action": {
                "action": "assign_department",
                "requires_doctor": False,
                "department_code": "general",
                "urgency": "routine",
            },
            "reward": 1.0,
        },
    ]

    result = trainer.train(data=data, policy_type="triage", activate=True)
    assert result.policy_version
    recommendation = trainer.recommend(
        "triage",
        {"chief_complaint": "胸痛", "main_symptom": "胸痛", "red_flag_count": 1, "requires_doctor": True},
    )
    assert recommendation["department_code"] == "emergency"
    run = registry.get_run(result.run_id)
    assert run["status"] == "completed"


def test_offline_dataset_builder_exports_samples():
    tmp_path = _workspace_tmp("dataset_exports")
    builder = OfflineDatasetBuilder()
    builder.export_dir = tmp_path
    bundle = {
        "policy_type": "routing",
        "state": {"chief_complaint": "头痛"},
        "action": {"action": "route_to_pcc"},
        "reward": 1.0,
    }
    splits = builder._split_entries([bundle, bundle, bundle])
    export_samples = builder._build_export_samples([bundle])
    export_files = builder._write_exports("all", splits, export_samples)
    assert "train" in export_files
    assert Path(export_files["export_samples"]).exists()
