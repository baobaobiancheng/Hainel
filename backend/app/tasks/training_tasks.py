"""
训练任务模块
处理智能体训练相关的异步任务
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from celery import Task
from sqlalchemy.orm import Session

from app.agents.evaluation.offline_dataset import (
    AGENT_TYPE_TO_POLICY_TYPES,
    OfflineDatasetBuilder,
)
from app.agents.evaluation.policy_registry import PolicyRegistry
from app.agents.evaluation.reward_calculator import RewardCalculator
from app.agents.evaluation.rl_trainer import RLTrainer
from app.tasks.celery_app import celery_app
from app.database.session import get_db_session
from app.models.conversation import Conversation
from app.models.medical_record import MedicalRecord
from app.models.message import Message, MessageRole
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseTask(Task):
    """
    数据库任务基类
    自动管理数据库会话
    """
    
    def __call__(self, *args, **kwargs):
        """
        执行任务，自动管理数据库会话
        """
        with get_db_session() as db:
            return self.run(db, *args, **kwargs)
    
    def run(self, db: Session, *args, **kwargs):
        """
        子类需要实现此方法
        """
        raise NotImplementedError("子类必须实现run方法")


def _resolve_policy_types(agent_type: str) -> List[str]:
    return AGENT_TYPE_TO_POLICY_TYPES.get((agent_type or "all").lower(), ["routing", "followup", "triage"])


def build_training_dataset_bundle(
    db: Session,
    agent_type: str,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    builder = OfflineDatasetBuilder()
    return builder.build(db=db, agent_type=agent_type, limit=limit)


def _latest_diagnosis_message(conversation_id: int, db: Session) -> Optional[Message]:
    assistant_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
        )
        .order_by(Message.created_at.desc(), Message.id.desc())
        .all()
    )
    for message in assistant_messages:
        metadata = message.extra_metadata if isinstance(message.extra_metadata, dict) else {}
        if metadata.get("action_checklist") or metadata.get("analysis_type") or metadata.get("triage"):
            return message
    return assistant_messages[0] if assistant_messages else None


def compute_and_persist_rewards(
    db: Session,
    conversation_id: int,
    agent_performances: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise ValueError(f"Conversation not found: {conversation_id}")

    calculator = RewardCalculator()
    latest_message = _latest_diagnosis_message(conversation_id, db)
    latest_metadata = latest_message.extra_metadata if latest_message and isinstance(latest_message.extra_metadata, dict) else {}
    triage = (conversation.extra_metadata or {}).get("triage") or latest_metadata.get("triage") or {}
    medical_record = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.conversation_id == conversation_id)
        .order_by(MedicalRecord.updated_at.desc(), MedicalRecord.id.desc())
        .first()
    )

    latest_diagnosis = {
        "content": latest_message.content if latest_message else "",
        "red_flags": latest_metadata.get("red_flags") or [],
        "action_checklist": latest_metadata.get("action_checklist"),
        "agents_used": latest_metadata.get("agents_used"),
    }
    outcome_labels = calculator.build_outcome_labels(
        conversation=conversation,
        triage=triage,
        medical_record=medical_record,
        latest_diagnosis=latest_metadata,
    )
    reward_breakdown = calculator.calculate_reward(
        conversation=conversation,
        latest_diagnosis=latest_diagnosis,
        triage=triage,
        medical_record=medical_record,
        trajectory_stats={"round_count": conversation.round_count or 0},
        outcome_labels=outcome_labels,
    )
    feedback_source = "heuristic"
    policy_trace = {}
    if agent_performances:
        feedback_source = "doctor_review" if any(
            item.get("feedback_source") == "doctor_review" for item in agent_performances.values()
        ) else "replay"
        policy_trace = {
            policy_type: {
                "state_summary": item.get("state_summary"),
                "candidate_actions": item.get("candidate_actions"),
                "final_action": item.get("final_action"),
                "policy_version": item.get("policy_version"),
            }
            for policy_type, item in agent_performances.items()
        }

    conversation_metadata = dict(conversation.extra_metadata or {})
    conversation_metadata["reward_breakdown"] = reward_breakdown
    conversation_metadata["outcome_labels"] = outcome_labels
    conversation_metadata["feedback_source"] = feedback_source
    if policy_trace:
        conversation_metadata["policy_trace"] = policy_trace
    conversation.extra_metadata = conversation_metadata

    if latest_message:
        latest_message_metadata = dict(latest_metadata)
        latest_message_metadata["reward_breakdown"] = reward_breakdown
        latest_message_metadata["outcome_labels"] = outcome_labels
        latest_message_metadata["feedback_source"] = feedback_source
        if policy_trace:
            latest_message_metadata["policy_trace"] = policy_trace
        latest_message.extra_metadata = latest_message_metadata

    if medical_record:
        record_metadata = dict(medical_record.extra_metadata or {})
        record_metadata["reward_breakdown"] = reward_breakdown
        record_metadata["outcome_labels"] = outcome_labels
        record_metadata["feedback_source"] = feedback_source
        medical_record.extra_metadata = record_metadata

    db.commit()
    return {
        "conversation_id": conversation_id,
        "reward_breakdown": reward_breakdown,
        "outcome_labels": outcome_labels,
        "feedback_source": feedback_source,
    }


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.training_tasks.train_agent",
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,  # 1小时硬超时
    soft_time_limit=3300,  # 55分钟软超时
)
def train_agent(
    self,
    db: Session,
    agent_type: str,
    agent_id: Optional[int] = None,
    training_data: Optional[List[Dict[str, Any]]] = None,
):
    """
    训练单个智能体
    
    Args:
        db: 数据库会话
        agent_type: 智能体类型（pcc, mdt, ict等）
        agent_id: 智能体ID（可选）
        training_data: 训练数据（可选，如果不提供则从数据库获取）
    
    Returns:
        训练结果字典
    """
    try:
        logger.info(f"开始训练智能体 - 类型: {agent_type}, ID: {agent_id}")

        bundle = build_training_dataset_bundle(db, agent_type) if training_data is None else {
            "agent_type": agent_type,
            "policy_types": _resolve_policy_types(agent_type),
            "entries": training_data,
            "splits": {"train": training_data, "val": [], "test": []},
            "summary": {"total_entries": len(training_data)},
            "export_files": {},
        }
        trainer = RLTrainer(agent_type)

        policy_results = []
        for policy_type in bundle["policy_types"]:
            policy_train_data = [
                entry for entry in bundle["splits"]["train"] if entry.get("policy_type") == policy_type
            ]
            if not policy_train_data:
                continue
            result = trainer.train(
                data=policy_train_data,
                policy_type=policy_type,
                batch_size=settings.TRAINING_BATCH_SIZE,
                learning_rate=settings.TRAINING_LEARNING_RATE,
                max_epochs=settings.TRAINING_MAX_EPOCHS,
                metadata={"trained_at": datetime.utcnow().isoformat(), "agent_id": agent_id},
            )
            validation_data = [
                entry for entry in bundle["splits"]["val"] if entry.get("policy_type") == policy_type
            ]
            test_data = [
                entry for entry in bundle["splits"]["test"] if entry.get("policy_type") == policy_type
            ]
            policy_results.append(
                {
                    "policy_type": policy_type,
                    "run_id": result.run_id,
                    "policy_version": result.policy_version,
                    "metrics": result.metrics,
                    "validation": trainer.evaluate(policy_type, validation_data, result.policy_version),
                    "test": trainer.evaluate(policy_type, test_data, result.policy_version),
                }
            )

        logger.info(f"智能体训练完成 - 类型: {agent_type}, ID: {agent_id}")
        return {
            "status": "success",
            "agent_type": agent_type,
            "agent_id": agent_id,
            "dataset_summary": bundle["summary"],
            "export_files": bundle.get("export_files", {}),
            "policy_results": policy_results,
            "trained_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"智能体训练失败 - 类型: {agent_type}, ID: {agent_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.training_tasks.train_agents_batch",
    max_retries=1,
    default_retry_delay=600,
    time_limit=7200,  # 2小时硬超时
    soft_time_limit=6900,  # 1小时55分钟软超时
)
def train_agents_batch(
    self,
    db: Session,
    agent_types: Optional[List[str]] = None,
    batch_size: Optional[int] = None,
):
    """
    批量训练智能体
    
    训练多个智能体，通常用于定期批量更新
    
    Args:
        db: 数据库会话
        agent_types: 要训练的智能体类型列表（如果为None则训练所有类型）
        batch_size: 批次大小
    
    Returns:
        训练结果字典
    """
    try:
        logger.info(f"开始批量训练智能体 - 类型: {agent_types}")
        
        if agent_types is None:
            agent_types = ["pcc", "mdt", "ict"]
        
        batch_size = batch_size or settings.TRAINING_BATCH_SIZE
        
        results = []
        for agent_type in agent_types:
            try:
                result = train_agent.delay(agent_type)
                results.append({
                    "agent_type": agent_type,
                    "task_id": result.id,
                    "status": "queued",
                })
            except Exception as e:
                logger.error(f"排队训练任务失败 - 类型: {agent_type}: {e}")
                results.append({
                    "agent_type": agent_type,
                    "status": "failed",
                    "error": str(e),
                })
        
        logger.info(f"批量训练任务已排队 - 共 {len(results)} 个任务")
        return {
            "status": "success",
            "results": results,
            "queued_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"批量训练智能体失败: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.training_tasks.evaluate_agent_performance",
    max_retries=2,
    default_retry_delay=60,
    time_limit=1800,  # 30分钟硬超时
)
def evaluate_agent_performance(
    self,
    db: Session,
    agent_type: str,
    agent_id: Optional[int] = None,
    test_data: Optional[List[Dict[str, Any]]] = None,
):
    """
    评估智能体性能
    
    Args:
        db: 数据库会话
        agent_type: 智能体类型
        agent_id: 智能体ID（可选）
        test_data: 测试数据（可选）
    
    Returns:
        评估结果字典
    """
    try:
        logger.info(f"开始评估智能体性能 - 类型: {agent_type}, ID: {agent_id}")

        bundle = build_training_dataset_bundle(db, agent_type) if test_data is None else {
            "policy_types": _resolve_policy_types(agent_type),
            "entries": test_data,
            "splits": {"train": [], "val": [], "test": test_data},
            "summary": {"total_entries": len(test_data)},
        }
        trainer = RLTrainer(agent_type)
        policy_metrics = []
        for policy_type in bundle["policy_types"]:
            policy_test_data = [
                entry for entry in bundle["splits"]["test"] if entry.get("policy_type") == policy_type
            ]
            policy_metrics.append(trainer.evaluate(policy_type, policy_test_data))

        logger.info(f"智能体性能评估完成 - 类型: {agent_type}, ID: {agent_id}")
        return {
            "status": "success",
            "agent_type": agent_type,
            "agent_id": agent_id,
            "dataset_summary": bundle["summary"],
            "policy_metrics": policy_metrics,
            "evaluated_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"评估智能体性能失败 - 类型: {agent_type}, ID: {agent_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.training_tasks.update_agent_rewards",
    max_retries=3,
    default_retry_delay=60,
)
def update_agent_rewards(
    self,
    db: Session,
    conversation_id: int,
    agent_performances: Dict[str, Dict[str, Any]],
):
    """
    更新智能体奖励
    
    根据会话结果更新智能体的奖励值，用于强化学习
    
    Args:
        db: 数据库会话
        conversation_id: 会话ID
        agent_performances: 智能体性能字典 {agent_id: {metrics...}}
    
    Returns:
        更新结果字典
    """
    try:
        logger.info(f"更新智能体奖励 - 会话ID: {conversation_id}")

        reward_result = compute_and_persist_rewards(
            db=db,
            conversation_id=conversation_id,
            agent_performances=agent_performances,
        )
        logger.info(f"智能体奖励更新完成 - 会话ID: {conversation_id}")
        return {
            "status": "success",
            "conversation_id": conversation_id,
            **reward_result,
            "updated_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"更新智能体奖励失败 - 会话ID: {conversation_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


# 导出
__all__ = [
    "train_agent",
    "train_agents_batch",
    "evaluate_agent_performance",
    "update_agent_rewards",
    "build_training_dataset_bundle",
    "compute_and_persist_rewards",
]

