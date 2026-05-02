from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import func

from app.database.base import engine
from app.database.session import get_db_session
from app.models.token_usage_log import TokenUsageLog
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TokenUsageService:
    _table_ready = False

    def ensure_table(self) -> None:
      # Lazy create keeps the feature usable without a dedicated migration step.
        if self.__class__._table_ready:
            return
        TokenUsageLog.__table__.create(bind=engine, checkfirst=True)
        self.__class__._table_ready = True

    @staticmethod
    def normalize_usage(usage: Optional[Dict[str, Any]]) -> Dict[str, int]:
        usage = usage or {}
        prompt_tokens = int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or usage.get("prompt_token_count")
            or 0
        )
        completion_tokens = int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or usage.get("completion_token_count")
            or 0
        )
        total_tokens = int(
            usage.get("total_tokens")
            or usage.get("total_token_count")
            or (prompt_tokens + completion_tokens)
        )
        return {
            "prompt_tokens": max(prompt_tokens, 0),
            "completion_tokens": max(completion_tokens, 0),
            "total_tokens": max(total_tokens, 0),
        }

    def record_usage(
        self,
        *,
        provider: str,
        model_name: str,
        source_type: str,
        usage: Optional[Dict[str, Any]],
        success: bool = True,
    ) -> None:
        metrics = self.normalize_usage(usage)
        if metrics["total_tokens"] <= 0 and metrics["prompt_tokens"] <= 0 and metrics["completion_tokens"] <= 0:
            return

        try:
            self.ensure_table()
            db = get_db_session()
            try:
                db.add(
                    TokenUsageLog(
                        provider=provider or "unknown",
                        model_name=model_name or "unknown",
                        source_type=source_type or "unknown",
                        prompt_tokens=metrics["prompt_tokens"],
                        completion_tokens=metrics["completion_tokens"],
                        total_tokens=metrics["total_tokens"],
                        success=bool(success),
                    )
                )
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.warning(f"记录 token 使用统计失败: {exc}")

    def aggregate(
        self,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        group_by: str = "day",
    ) -> Dict[str, Any]:
        self.ensure_table()
        db = get_db_session()
        try:
            query = db.query(TokenUsageLog)
            if date_from:
                query = query.filter(TokenUsageLog.created_at >= date_from)
            if date_to:
                query = query.filter(TokenUsageLog.created_at <= date_to)
            rows: Iterable[TokenUsageLog] = query.order_by(TokenUsageLog.created_at.asc()).all()
        finally:
            db.close()

        return {
            "summary": self._build_summary(rows),
            "by_model": self._build_by_model(rows),
            "timeseries": self._build_timeseries(rows, group_by=group_by),
        }

    def _build_summary(self, rows: Iterable[TokenUsageLog]) -> Dict[str, Any]:
        rows = list(rows)
        total_prompt = sum(item.prompt_tokens for item in rows)
        total_completion = sum(item.completion_tokens for item in rows)
        total_tokens = sum(item.total_tokens for item in rows)
        request_count = len(rows)
        return {
            "request_count": request_count,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "success_count": sum(1 for item in rows if item.success),
            "last_called_at": rows[-1].created_at.isoformat() if rows else None,
        }

    def _build_by_model(self, rows: Iterable[TokenUsageLog]) -> list[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in rows:
            entry = grouped.setdefault(
                item.model_name,
                {
                    "provider": item.provider,
                    "model_name": item.model_name,
                    "request_count": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "last_called_at": None,
                },
            )
            entry["request_count"] += 1
            entry["prompt_tokens"] += item.prompt_tokens
            entry["completion_tokens"] += item.completion_tokens
            entry["total_tokens"] += item.total_tokens
            entry["last_called_at"] = item.created_at.isoformat()

        result = []
        for entry in grouped.values():
            entry["avg_tokens_per_request"] = round(
                entry["total_tokens"] / entry["request_count"], 2
            ) if entry["request_count"] else 0
            result.append(entry)
        result.sort(key=lambda item: item["total_tokens"], reverse=True)
        return result

    def _build_timeseries(self, rows: Iterable[TokenUsageLog], *, group_by: str) -> list[Dict[str, Any]]:
        buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "request_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        )
        for item in rows:
            key = item.created_at.strftime("%Y-%m-%d") if group_by == "day" else item.created_at.strftime("%Y-%m-%d %H:00")
            bucket = buckets[key]
            bucket["request_count"] += 1
            bucket["prompt_tokens"] += item.prompt_tokens
            bucket["completion_tokens"] += item.completion_tokens
            bucket["total_tokens"] += item.total_tokens

        return [
            {"bucket": key, **value}
            for key, value in sorted(buckets.items(), key=lambda kv: kv[0])
        ]


token_usage_service = TokenUsageService()


__all__ = ["TokenUsageService", "token_usage_service"]
