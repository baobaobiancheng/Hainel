"""
Agent management, RL training, model center, and runtime config APIs.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.evaluation.policy_registry import PolicyRegistry
from app.agents.evaluation.rl_trainer import RLTrainer
from app.ai.embeddings.embedding_service import EmbeddingService
from app.ai.llm.qwen import QwenLLMService
from app.ai.ocr.dashscope_ocr import DashScopeOCRService
from app.config import settings
from app.core.permissions import Role, get_current_user, require_role
from app.dependencies import get_db
from app.services.token_usage_service import token_usage_service
from app.tasks.training_tasks import build_training_dataset_bundle
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])
RL_EXPORT_DIR = Path(__file__).resolve().parents[3] / "data" / "rl_exports"


AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "moderator": {
        "name": "Moderator",
        "type": "moderator",
        "description": "Evaluate case complexity and choose PCC, MDT, or ICT collaboration mode.",
        "capabilities": ["complexity_evaluation", "routing_decision"],
    },
    "pcc": {
        "name": "PCC Agent",
        "type": "pcc",
        "description": "Single-agent consultation and reasoning.",
        "capabilities": ["chain_of_thought", "single_agent_reasoning"],
    },
    "mdt": {
        "name": "MDT Agent",
        "type": "mdt",
        "description": "Multi-agent discussion and consensus building for harder cases.",
        "capabilities": ["multi_agent_discussion", "consensus_building"],
    },
    "ict": {
        "name": "ICT Agent",
        "type": "ict",
        "description": "Cross-discipline collaboration and report synthesis for complex cases.",
        "capabilities": ["cross_discipline_collaboration", "report_synthesis"],
    },
    "reminder": {
        "name": "Reminder Agent",
        "type": "reminder",
        "description": "Medication and follow-up reminders.",
        "capabilities": ["medication_reminder", "scheduled_tasks"],
    },
    "patient_simulator": {
        "name": "Patient Simulator",
        "type": "patient_simulator",
        "description": "Synthetic patient simulator for offline replay and training.",
        "capabilities": ["case_generation", "symptom_simulation"],
    },
}


class AgentStatusResponse(BaseModel):
    agent_id: str
    name: str
    type: str
    description: str
    capabilities: List[str]
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None


class AgentConfigPatch(BaseModel):
    complexity_low_threshold: Optional[int] = Field(None, ge=0, le=100)
    complexity_medium_threshold: Optional[int] = Field(None, ge=0, le=100)
    pcc_max_rounds: Optional[int] = Field(None, ge=1, le=20)
    mdt_min_agents: Optional[int] = Field(None, ge=1, le=10)
    mdt_max_agents: Optional[int] = Field(None, ge=1, le=10)
    mdt_max_discussion_rounds: Optional[int] = Field(None, ge=1, le=10)
    mdt_consensus_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    ict_min_agents: Optional[int] = Field(None, ge=1, le=15)
    ict_max_agents: Optional[int] = Field(None, ge=1, le=15)
    ict_max_rounds: Optional[int] = Field(None, ge=1, le=30)
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llm_max_tokens: Optional[int] = Field(None, ge=128, le=8192)


class SystemConfigResponse(BaseModel):
    complexity_low_threshold: int
    complexity_medium_threshold: int
    pcc_agent_count: int
    pcc_max_rounds: int
    mdt_min_agents: int
    mdt_max_agents: int
    mdt_max_discussion_rounds: int
    mdt_consensus_threshold: float
    ict_min_agents: int
    ict_max_agents: int
    ict_max_rounds: int
    llm_provider: str
    llm_model_name: str
    llm_temperature: float
    llm_max_tokens: int


class TrainingDatasetBuildRequest(BaseModel):
    agent_type: str = Field(default="all")
    limit: Optional[int] = Field(None, ge=1)


class TrainingDatasetBuildResponse(BaseModel):
    success: bool = True
    dataset_id: str
    agent_type: str
    policy_types: List[str]
    dataset_size: int
    total_entries: int
    train_size: int
    val_size: int
    test_size: int
    export_file: Optional[str] = None
    export_files: Dict[str, str] = Field(default_factory=dict)
    export_artifacts: List[Dict[str, str]] = Field(default_factory=list)
    message: str = "Dataset build completed."


class TrainingRunRequest(BaseModel):
    agent_type: str = Field(default="all")
    dataset_id: Optional[str] = None
    activate: bool = Field(default=False)
    limit: Optional[int] = Field(None, ge=1)


class TrainingPolicyResult(BaseModel):
    policy_type: str
    run_id: str
    policy_version: str
    metrics: Dict[str, Any]


class TrainingRunResponse(BaseModel):
    success: bool = True
    agent_type: str
    dataset_id: Optional[str] = None
    run_id: Optional[str] = None
    policy_version: Optional[str] = None
    dataset_summary: Dict[str, Any]
    policy_results: List[TrainingPolicyResult]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    message: str = "Offline training completed."


class TrainingEvaluateRequest(BaseModel):
    agent_type: str = Field(default="all")
    dataset_id: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1)


class TrainingEvaluateResponse(BaseModel):
    success: bool = True
    agent_type: str
    dataset_id: Optional[str] = None
    dataset_summary: Dict[str, Any]
    policy_metrics: List[Dict[str, Any]]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    message: str = "Offline evaluation completed."


class TrainingRunStatusResponse(BaseModel):
    run_id: str
    dataset_id: Optional[str] = None
    policy_type: Optional[str] = None
    status: str
    version: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    updated_at: Optional[str] = None


class PolicyActivateRequest(BaseModel):
    policy_version: Optional[str] = None
    version: Optional[str] = None


class PolicyActivationResponse(BaseModel):
    success: bool = True
    policy_type: str
    version: str
    snapshot_path: str
    active_policy: Dict[str, Any]
    message: str = "Policy activated."


class TrainingDatasetRecordResponse(BaseModel):
    dataset_id: str
    agent_type: str
    policy_types: List[str]
    summary: Dict[str, Any]
    export_files: Dict[str, str] = Field(default_factory=dict)
    export_artifacts: List[Dict[str, str]] = Field(default_factory=list)
    created_at: Optional[str] = None
    created_by: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyVersionRecordResponse(BaseModel):
    policy_type: str
    version: str
    snapshot_path: str
    created_at: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class ModelConfigResponse(BaseModel):
    llm_provider: str
    llm_model_name: str
    llm_api_base: Optional[str] = None
    llm_temperature: float
    llm_max_tokens: int
    llm_api_key_configured: bool
    deepseek_base_url: str
    deepseek_model: str
    deepseek_api_key_configured: bool
    ocr_provider: str
    chroma_embedding_model: str
    chroma_model_cache_dir: str


class ModelConfigPatchRequest(BaseModel):
    llm_provider: Optional[str] = None
    llm_model_name: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llm_max_tokens: Optional[int] = Field(None, ge=128, le=8192)
    deepseek_base_url: Optional[str] = None
    deepseek_model: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    ocr_provider: Optional[str] = None
    chroma_embedding_model: Optional[str] = None
    chroma_model_cache_dir: Optional[str] = None


class ModelTestRequest(BaseModel):
    target: str = Field(..., pattern="^(llm|deepseek|ocr|embedding)$")
    model_name: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None


class ModelTestResponse(BaseModel):
    success: bool
    target: str
    model: Optional[str] = None
    latency_ms: int
    message: str
    error: Optional[str] = None


def _build_system_config() -> SystemConfigResponse:
    return SystemConfigResponse(
        complexity_low_threshold=settings.COMPLEXITY_LOW_THRESHOLD,
        complexity_medium_threshold=settings.COMPLEXITY_MEDIUM_THRESHOLD,
        pcc_agent_count=settings.PCC_AGENT_COUNT,
        pcc_max_rounds=settings.PCC_MAX_ROUNDS,
        mdt_min_agents=settings.MDT_MIN_AGENTS,
        mdt_max_agents=settings.MDT_MAX_AGENTS,
        mdt_max_discussion_rounds=settings.MDT_MAX_DISCUSSION_ROUNDS,
        mdt_consensus_threshold=settings.MDT_CONSENSUS_THRESHOLD,
        ict_min_agents=settings.ICT_MIN_AGENTS,
        ict_max_agents=settings.ICT_MAX_AGENTS,
        ict_max_rounds=settings.ICT_MAX_ROUNDS,
        llm_provider=settings.LLM_PROVIDER,
        llm_model_name=settings.LLM_MODEL_NAME,
        llm_temperature=settings.LLM_TEMPERATURE,
        llm_max_tokens=settings.LLM_MAX_TOKENS,
    )


def _build_model_config() -> ModelConfigResponse:
    return ModelConfigResponse(
        llm_provider=settings.LLM_PROVIDER,
        llm_model_name=settings.LLM_MODEL_NAME,
        llm_api_base=settings.LLM_API_BASE,
        llm_temperature=settings.LLM_TEMPERATURE,
        llm_max_tokens=settings.LLM_MAX_TOKENS,
        llm_api_key_configured=bool(settings.LLM_API_KEY),
        deepseek_base_url=settings.DEEPSEEK_BASE_URL,
        deepseek_model=settings.DEEPSEEK_MODEL,
        deepseek_api_key_configured=bool(settings.DEEPSEEK_API_KEY),
        ocr_provider=settings.OCR_PROVIDER,
        chroma_embedding_model=settings.CHROMA_EMBEDDING_MODEL,
        chroma_model_cache_dir=settings.CHROMA_MODEL_CACHE_DIR,
    )


def _apply_runtime_model_config(payload: ModelConfigPatchRequest) -> None:
    updates = payload.model_dump(exclude_unset=True)
    mapping = {
        "llm_provider": "LLM_PROVIDER",
        "llm_model_name": "LLM_MODEL_NAME",
        "llm_api_base": "LLM_API_BASE",
        "llm_api_key": "LLM_API_KEY",
        "llm_temperature": "LLM_TEMPERATURE",
        "llm_max_tokens": "LLM_MAX_TOKENS",
        "deepseek_base_url": "DEEPSEEK_BASE_URL",
        "deepseek_model": "DEEPSEEK_MODEL",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "ocr_provider": "OCR_PROVIDER",
        "chroma_embedding_model": "CHROMA_EMBEDDING_MODEL",
        "chroma_model_cache_dir": "CHROMA_MODEL_CACHE_DIR",
    }
    for key, value in updates.items():
        setattr(settings, mapping[key], value)


def _test_llm(model_name: Optional[str], api_base: Optional[str], api_key: Optional[str]) -> ModelTestResponse:
    started = perf_counter()
    try:
        llm = QwenLLMService()
        if model_name:
            llm.config.model_name = model_name
        if api_base:
            llm.config.api_base = api_base
        if api_key:
            llm.config.api_key = api_key
        response = llm.generate("Please reply with: connection ok", max_tokens=32, temperature=0)
        return ModelTestResponse(
            success=True,
            target="llm",
            model=response.model,
            latency_ms=int((perf_counter() - started) * 1000),
            message="Main LLM connection is healthy.",
        )
    except Exception as exc:
        return ModelTestResponse(
            success=False,
            target="llm",
            model=model_name or settings.LLM_MODEL_NAME,
            latency_ms=int((perf_counter() - started) * 1000),
            message="Main LLM connection failed.",
            error=str(exc),
        )


def _test_deepseek(model_name: Optional[str], api_base: Optional[str], api_key: Optional[str]) -> ModelTestResponse:
    started = perf_counter()
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key or settings.DEEPSEEK_API_KEY,
            base_url=api_base or settings.DEEPSEEK_BASE_URL,
        )
        model = model_name or settings.DEEPSEEK_MODEL
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Please reply with: connection ok"}],
            temperature=0,
        )
        return ModelTestResponse(
            success=True,
            target="deepseek",
            model=model,
            latency_ms=int((perf_counter() - started) * 1000),
            message=response.choices[0].message.content or "DeepSeek connection is healthy.",
        )
    except Exception as exc:
        return ModelTestResponse(
            success=False,
            target="deepseek",
            model=model_name or settings.DEEPSEEK_MODEL,
            latency_ms=int((perf_counter() - started) * 1000),
            message="DeepSeek connection failed.",
            error=str(exc),
        )


def _test_ocr() -> ModelTestResponse:
    started = perf_counter()
    try:
        from PIL import Image

        image = Image.new("RGB", (120, 40), color="white")
        service = DashScopeOCRService()
        service.recognize(image)
        return ModelTestResponse(
            success=True,
            target="ocr",
            model="qwen-vl-plus",
            latency_ms=int((perf_counter() - started) * 1000),
            message="OCR connection is healthy.",
        )
    except Exception as exc:
        return ModelTestResponse(
            success=False,
            target="ocr",
            model="qwen-vl-plus",
            latency_ms=int((perf_counter() - started) * 1000),
            message="OCR connection failed.",
            error=str(exc),
        )


def _test_embedding(model_name: Optional[str]) -> ModelTestResponse:
    started = perf_counter()
    try:
        service = EmbeddingService(
            model_name=model_name or settings.CHROMA_EMBEDDING_MODEL,
            provider="huggingface",
        )
        vector = service.embed_query("embedding health check")
        return ModelTestResponse(
            success=True,
            target="embedding",
            model=service.model_name,
            latency_ms=int((perf_counter() - started) * 1000),
            message=f"Embedding initialized successfully with dimension {len(vector)}.",
        )
    except Exception as exc:
        return ModelTestResponse(
            success=False,
            target="embedding",
            model=model_name or settings.CHROMA_EMBEDDING_MODEL,
            latency_ms=int((perf_counter() - started) * 1000),
            message="Embedding initialization failed.",
            error=str(exc),
        )


def _safe_average(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _summarize_policy_metrics(policy_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    reward_values: List[float] = []
    triage_values: List[float] = []
    red_flag_values: List[float] = []
    turns_values: List[float] = []
    adoption_values: List[float] = []

    for row in policy_metrics:
        reward = row.get("avg_reward", row.get("average_reward", row.get("reward")))
        triage = row.get("triage_accuracy")
        red_flag = row.get("red_flag_recall")
        avg_turns = row.get("avg_turns")
        adoption = row.get("record_adoption_rate")
        for bucket, value in (
            (reward_values, reward),
            (triage_values, triage),
            (red_flag_values, red_flag),
            (turns_values, avg_turns),
            (adoption_values, adoption),
        ):
            try:
                if value is not None:
                    bucket.append(float(value))
            except (TypeError, ValueError):
                continue

    return {
        "avg_reward": _safe_average(reward_values),
        "triage_accuracy": _safe_average(triage_values),
        "red_flag_recall": _safe_average(red_flag_values),
        "avg_turns": _safe_average(turns_values),
        "record_adoption_rate": _safe_average(adoption_values),
    }


def _build_export_artifacts(export_files: Dict[str, str]) -> List[Dict[str, str]]:
    artifacts: List[Dict[str, str]] = []
    for split, full_path in export_files.items():
        if split == "export_samples":
            continue
        file_name = Path(full_path).name
        artifacts.append(
            {
                "split": split,
                "file_name": file_name,
                "download_url": f"/api/v1/agents/training/exports/{file_name}",
            }
        )
    return artifacts


def _normalize_dataset_record(record: Dict[str, Any]) -> TrainingDatasetRecordResponse:
    return TrainingDatasetRecordResponse(
        dataset_id=record["dataset_id"],
        agent_type=record.get("agent_type", "all"),
        policy_types=record.get("policy_types", []) or [],
        summary=record.get("summary", {}) or {},
        export_files=record.get("export_files", {}) or {},
        export_artifacts=_build_export_artifacts(record.get("export_files", {}) or {}),
        created_at=record.get("created_at"),
        created_by=record.get("created_by"),
        metadata=record.get("metadata", {}) or {},
    )


def _resolve_dataset_bundle(
    *,
    db: Session,
    agent_type: str,
    limit: Optional[int],
    dataset_id: Optional[str],
) -> Dict[str, Any]:
    if not dataset_id:
        return build_training_dataset_bundle(db, agent_type, limit=limit)

    registry = PolicyRegistry()
    dataset_record = registry.get_dataset(dataset_id)
    if not dataset_record:
        raise HTTPException(status_code=404, detail=f"Training dataset not found: {dataset_id}")

    export_files = dataset_record.get("export_files", {}) or {}
    if not export_files:
        raise HTTPException(status_code=400, detail=f"Training dataset export files missing: {dataset_id}")

    splits: Dict[str, List[Dict[str, Any]]] = {}
    for split_name in ("train", "val", "test"):
        file_path = export_files.get(split_name)
        if not file_path:
            raise HTTPException(
                status_code=400,
                detail=f"Training dataset split missing: {dataset_id}/{split_name}",
            )
        split_path = Path(file_path)
        if not split_path.exists() or not split_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Training dataset file missing: {dataset_id}/{split_name}",
            )
        items: List[Dict[str, Any]] = []
        with split_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))
        splits[split_name] = items

    entries = splits["train"] + splits["val"] + splits["test"]
    return {
        "dataset_id": dataset_id,
        "agent_type": dataset_record.get("agent_type", agent_type),
        "policy_types": dataset_record.get("policy_types", []) or [],
        "entries": entries,
        "splits": splits,
        "summary": dataset_record.get("summary", {}) or {},
        "export_files": export_files,
        "dataset_record": dataset_record,
    }


@router.get("/", response_model=List[AgentStatusResponse])
async def list_agents(current_user: dict = Depends(get_current_user)):
    return [
        AgentStatusResponse(
            agent_id=agent_id,
            name=info["name"],
            type=info["type"],
            description=info["description"],
            capabilities=info["capabilities"],
            is_active=True,
        )
        for agent_id, info in AGENT_REGISTRY.items()
    ]


@router.post("/training/dataset/build", response_model=TrainingDatasetBuildResponse)
async def build_training_dataset(
    request: TrainingDatasetBuildRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
    db: Session = Depends(get_db),
):
    bundle = build_training_dataset_bundle(db, request.agent_type, limit=request.limit)
    registry = PolicyRegistry()
    summary = bundle["summary"]
    export_files = bundle.get("export_files", {})
    dataset_record = registry.register_dataset(
        agent_type=request.agent_type,
        policy_types=bundle["policy_types"],
        summary=summary,
        export_files=export_files,
        created_by=current_user.get("id"),
        metadata={"limit": request.limit},
    )
    primary_export = next(iter(export_files.values()), None)
    return TrainingDatasetBuildResponse(
        dataset_id=dataset_record["dataset_id"],
        agent_type=request.agent_type,
        policy_types=bundle["policy_types"],
        dataset_size=summary["total_entries"],
        total_entries=summary["total_entries"],
        train_size=summary["train_size"],
        val_size=summary["val_size"],
        test_size=summary["test_size"],
        export_file=primary_export,
        export_files=export_files,
        export_artifacts=_build_export_artifacts(export_files),
        message="Dataset build completed.",
    )


@router.get("/training/datasets", response_model=List[TrainingDatasetRecordResponse])
async def list_training_datasets(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    registry = PolicyRegistry()
    return [_normalize_dataset_record(record) for record in registry.list_datasets()]


@router.get("/training/datasets/{dataset_id}", response_model=TrainingDatasetRecordResponse)
async def get_training_dataset(
    dataset_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    registry = PolicyRegistry()
    record = registry.get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Training dataset not found: {dataset_id}")
    return _normalize_dataset_record(record)


@router.get("/training/exports/{file_name}")
async def download_training_export(
    file_name: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")

    candidate = (RL_EXPORT_DIR / safe_name).resolve()
    base_dir = RL_EXPORT_DIR.resolve()

    if candidate.parent != base_dir:
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=str(candidate),
        filename=safe_name,
        media_type="application/json",
    )


@router.post("/training/run", response_model=TrainingRunResponse)
async def run_training(
    request: TrainingRunRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
    db: Session = Depends(get_db),
):
    bundle = _resolve_dataset_bundle(
        db=db,
        agent_type=request.agent_type,
        limit=request.limit,
        dataset_id=request.dataset_id,
    )
    effective_agent_type = bundle.get("agent_type", request.agent_type)
    trainer = RLTrainer(effective_agent_type)
    policy_results: List[TrainingPolicyResult] = []
    for policy_type in bundle["policy_types"]:
        policy_data = [item for item in bundle["splits"]["train"] if item.get("policy_type") == policy_type]
        if not policy_data:
            continue
        result = trainer.train(
            data=policy_data,
            policy_type=policy_type,
            activate=request.activate,
            metadata={
                "requested_by": current_user.get("id"),
                "trained_at": datetime.utcnow().isoformat(),
                "dataset_id": bundle.get("dataset_id"),
            },
            run_params={"dataset_id": bundle.get("dataset_id")},
        )
        policy_results.append(
            TrainingPolicyResult(
                policy_type=policy_type,
                run_id=result.run_id,
                policy_version=result.policy_version,
                metrics=result.metrics,
            )
        )

    first_result = policy_results[0] if policy_results else None
    metrics = _summarize_policy_metrics([item.metrics for item in policy_results])
    return TrainingRunResponse(
        agent_type=effective_agent_type,
        dataset_id=bundle.get("dataset_id"),
        run_id=first_result.run_id if first_result else None,
        policy_version=first_result.policy_version if first_result else None,
        dataset_summary=bundle["summary"],
        policy_results=policy_results,
        metrics=metrics,
        message="Offline training completed.",
    )


@router.post("/training/evaluate", response_model=TrainingEvaluateResponse)
async def evaluate_training(
    request: TrainingEvaluateRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    bundle = _resolve_dataset_bundle(
        db=db,
        agent_type=request.agent_type,
        limit=request.limit,
        dataset_id=request.dataset_id,
    )
    effective_agent_type = bundle.get("agent_type", request.agent_type)
    trainer = RLTrainer(effective_agent_type)
    policy_metrics: List[Dict[str, Any]] = []
    for policy_type in bundle["policy_types"]:
        policy_data = [item for item in bundle["splits"]["test"] if item.get("policy_type") == policy_type]
        policy_metrics.append(trainer.evaluate(policy_type=policy_type, data=policy_data))
    return TrainingEvaluateResponse(
        agent_type=effective_agent_type,
        dataset_id=bundle.get("dataset_id"),
        dataset_summary=bundle["summary"],
        policy_metrics=policy_metrics,
        metrics=_summarize_policy_metrics(policy_metrics),
        message="Offline evaluation completed.",
    )


@router.get("/training/runs/{run_id}", response_model=TrainingRunStatusResponse)
async def get_training_run(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
):
    registry = PolicyRegistry()
    run = registry.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Training run not found: {run_id}")

    status_value = run.get("status", "unknown")
    return TrainingRunStatusResponse(
        run_id=run_id,
        dataset_id=run.get("dataset_id") or (run.get("params", {}) or {}).get("dataset_id"),
        policy_type=run.get("policy_type"),
        status=status_value,
        version=run.get("version"),
        result=run.get("result", {}) or {},
        metrics=run.get("metrics", {}) or {},
        params=run.get("params", {}) or {},
        error=run.get("error"),
        started_at=run.get("created_at"),
        finished_at=run.get("updated_at") if status_value in {"completed", "failed"} else None,
        updated_at=run.get("updated_at"),
    )


@router.post("/policies/{policy_type}/activate", response_model=PolicyActivationResponse)
async def activate_policy(
    policy_type: str,
    request: PolicyActivateRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    version = request.policy_version or request.version
    if not version:
        raise HTTPException(status_code=400, detail="policy_version is required")

    registry = PolicyRegistry()
    try:
        policy = registry.activate_policy(policy_type, version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PolicyActivationResponse(
        policy_type=policy_type,
        version=policy["version"],
        snapshot_path=policy["snapshot_path"],
        active_policy={
            "policy_type": policy_type,
            "version": policy["version"],
            "snapshot_path": policy["snapshot_path"],
            "metrics": policy.get("metrics", {}),
        },
        message="Policy activated.",
    )


@router.get("/policies/{policy_type}/versions", response_model=List[PolicyVersionRecordResponse])
async def list_policy_versions(
    policy_type: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    registry = PolicyRegistry()
    active = registry.get_active_policy(policy_type)
    active_version = active.get("version") if active else None
    return [
        PolicyVersionRecordResponse(
            policy_type=policy_type,
            version=item["version"],
            snapshot_path=item["snapshot_path"],
            created_at=item.get("created_at"),
            metrics=item.get("metrics", {}) or {},
            metadata=item.get("metadata", {}) or {},
            is_active=item.get("version") == active_version,
        )
        for item in registry.list_policy_versions(policy_type)
    ]


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
):
    return _build_system_config()


@router.patch("/config", response_model=SystemConfigResponse)
async def update_system_config(
    config_data: AgentConfigPatch,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    update_data = config_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No config fields provided.")

    for key, value in update_data.items():
        upper_key = key.upper()
        if hasattr(settings, upper_key):
            setattr(settings, upper_key, value)
        else:
            logger.warning("Attempted to update unknown config key: %s", key)
    return _build_system_config()


@router.get("/models/config", response_model=ModelConfigResponse)
async def get_model_config(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    return _build_model_config()


@router.patch("/models/config", response_model=ModelConfigResponse)
async def update_model_config(
    payload: ModelConfigPatchRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    if not payload.model_dump(exclude_unset=True):
        raise HTTPException(status_code=400, detail="No model config fields provided.")
    _apply_runtime_model_config(payload)
    return _build_model_config()


@router.post("/models/test", response_model=ModelTestResponse)
async def test_model_connection(
    payload: ModelTestRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    if payload.target == "llm":
        return _test_llm(payload.model_name, payload.api_base, payload.api_key)
    if payload.target == "deepseek":
        return _test_deepseek(payload.model_name, payload.api_base, payload.api_key)
    if payload.target == "ocr":
        return _test_ocr()
    return _test_embedding(payload.model_name)


@router.get("/models/token-usage")
async def get_model_token_usage(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    group_by: str = "day",
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.ADMIN])),
):
    return token_usage_service.aggregate(date_from=date_from, date_to=date_to, group_by=group_by)


@router.get("/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
):
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found. Available ids: {list(AGENT_REGISTRY.keys())}",
        )

    info = AGENT_REGISTRY[agent_id]
    config = None
    if current_user.get("role") == Role.ADMIN.value:
        config = {
            "moderator": {
                "complexity_low_threshold": settings.COMPLEXITY_LOW_THRESHOLD,
                "complexity_medium_threshold": settings.COMPLEXITY_MEDIUM_THRESHOLD,
            },
            "pcc": {
                "agent_count": settings.PCC_AGENT_COUNT,
                "max_rounds": settings.PCC_MAX_ROUNDS,
            },
            "mdt": {
                "min_agents": settings.MDT_MIN_AGENTS,
                "max_agents": settings.MDT_MAX_AGENTS,
                "max_discussion_rounds": settings.MDT_MAX_DISCUSSION_ROUNDS,
                "consensus_threshold": settings.MDT_CONSENSUS_THRESHOLD,
            },
            "ict": {
                "min_agents": settings.ICT_MIN_AGENTS,
                "max_agents": settings.ICT_MAX_AGENTS,
                "max_rounds": settings.ICT_MAX_ROUNDS,
            },
        }.get(agent_id)

    return AgentStatusResponse(
        agent_id=agent_id,
        name=info["name"],
        type=info["type"],
        description=info["description"],
        capabilities=info["capabilities"],
        is_active=True,
        config=config,
    )


__all__ = ["router"]
