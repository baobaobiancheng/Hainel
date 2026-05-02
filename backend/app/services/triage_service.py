"""
智能分诊服务

使用 DeepSeek 在标准科室白名单内选择合适接诊科室，并对模型输出做强校验。
"""
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.token_usage_service import token_usage_service
from app.services.doctor_service import Department, DEPARTMENT_CHINESE
from app.utils.logger import get_logger

logger = get_logger(__name__)


ALLOWED_URGENCIES = {"routine", "normal", "urgent", "emergency"}
LOW_CONFIDENCE_THRESHOLD = 0.45


@dataclass
class TriageResult:
    """标准化分诊结果。"""

    requires_doctor: bool
    department: Department
    department_name: str
    urgency: str
    confidence: float
    reason: str
    fallback_reason: Optional[str] = None
    raw_response: Optional[str] = None

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "requires_doctor": self.requires_doctor,
            "department_code": self.department.value,
            "department_name": self.department_name,
            "urgency": self.urgency,
            "confidence": self.confidence,
            "reason": self.reason,
            "fallback_reason": self.fallback_reason,
        }


class TriageService:
    """DeepSeek 科室分诊服务。"""

    _red_flag_keywords = [
        "胸痛",
        "胸闷",
        "呼吸困难",
        "喘不上气",
        "意识不清",
        "昏厥",
        "晕厥",
        "抽搐",
        "大出血",
        "咯血",
        "呕血",
        "黑便",
    ]

    def __init__(self):
        self._model = settings.DEEPSEEK_MODEL or "deepseek-v4-flash"

    def triage(
        self,
        symptoms: str,
        medical_history: Optional[str] = None,
        health_profile: Optional[Dict[str, Any]] = None,
        structured_intake: Optional[Dict[str, Any]] = None,
        linked_reports: Optional[List[Dict[str, Any]]] = None,
        diagnosis_result: Optional[Dict[str, Any]] = None,
        kg_summary: Optional[str] = None,
    ) -> TriageResult:
        """返回经过白名单校验的科室分诊结果。"""
        if self._has_red_flag(symptoms, structured_intake):
            return self._emergency_result()

        prompt = self._build_prompt(
            symptoms=symptoms,
            medical_history=medical_history,
            health_profile=health_profile,
            structured_intake=structured_intake,
            linked_reports=linked_reports,
            diagnosis_result=diagnosis_result,
            kg_summary=kg_summary,
        )

        try:
            raw_response = self._call_model(prompt)
            data = self._extract_json(raw_response)
            return self._normalize_model_result(data, raw_response)
        except Exception as e:
            logger.warning(f"DeepSeek 分诊失败，回退全科: {e}", exc_info=True)
            return self._fallback_result("model_error", raw_response=None)

    def _call_model(self, prompt: str) -> str:
        """调用 OpenAI 兼容的 DeepSeek Chat Completions API。"""
        api_key = settings.DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY")

        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("缺少 openai 客户端依赖") from e

        base_url = settings.DEEPSEEK_BASE_URL or os.environ.get(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com",
        )
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "你是严谨的医疗预分诊助手，只能根据给定科室白名单输出 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        token_usage_service.record_usage(
            provider="deepseek",
            model_name=self._model,
            source_type="triage_service",
            usage=getattr(response, "usage", None).model_dump() if getattr(response, "usage", None) else None,
            success=True,
        )
        return response.choices[0].message.content or ""

    def _build_prompt(
        self,
        symptoms: str,
        medical_history: Optional[str],
        health_profile: Optional[Dict[str, Any]],
        structured_intake: Optional[Dict[str, Any]],
        linked_reports: Optional[List[Dict[str, Any]]],
        diagnosis_result: Optional[Dict[str, Any]],
        kg_summary: Optional[str],
    ) -> str:
        departments = "\n".join(
            f"- {department.value}: {DEPARTMENT_CHINESE[department]}"
            for department in Department
        )
        return f"""请根据患者信息判断是否需要医生介入，以及应由哪个科室优先对接。

【允许科室白名单】
{departments}

【患者主诉/症状】
{symptoms or "未提供"}

【会话背景】
{medical_history or "无"}

【健康档案】
{self._format_dict(health_profile)}

【本次结构化问诊】
{self._format_dict(structured_intake)}

【报告OCR摘要】
{self._format_reports(linked_reports)}

【知识图谱摘要】
{kg_summary or "无"}

【智能分析结果摘要】
{self._summarize_diagnosis(diagnosis_result)}

请只返回一个 JSON 对象，不要 Markdown，不要解释文字。格式必须为：
{{
  "requires_doctor": true,
  "department_code": "cardiology",
  "department_name": "心内科",
  "urgency": "normal",
  "confidence": 0.0,
  "reason": "选择该科室的简明理由"
}}

要求：
1. department_code 必须来自白名单中的代码。
2. department_name 必须与 department_code 对应。
3. urgency 只能是 routine、normal、urgent、emergency。
4. confidence 为 0 到 1 的数字。
5. 如果线上建议即可先处理，requires_doctor 可为 false，但仍要给出最合适科室。
6. 遇到明显急症风险优先选择 emergency/急诊科。"""

    def _normalize_model_result(self, data: Dict[str, Any], raw_response: str) -> TriageResult:
        department = self._parse_department(data)
        if department is None:
            return self._fallback_result("invalid_department", raw_response=raw_response)

        confidence = self._parse_confidence(data.get("confidence"))
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            return self._fallback_result("low_confidence", raw_response=raw_response)

        urgency = str(data.get("urgency") or "normal").strip().lower()
        if urgency not in ALLOWED_URGENCIES:
            urgency = "normal"

        return TriageResult(
            requires_doctor=bool(data.get("requires_doctor", True)),
            department=department,
            department_name=DEPARTMENT_CHINESE[department],
            urgency=urgency,
            confidence=confidence,
            reason=str(data.get("reason") or "模型建议该科室优先接诊").strip(),
            raw_response=raw_response,
        )

    def _parse_department(self, data: Dict[str, Any]) -> Optional[Department]:
        code = str(data.get("department_code") or "").strip().lower()
        name = str(data.get("department_name") or "").strip()
        for department, department_name in DEPARTMENT_CHINESE.items():
            if code == department.value or name == department_name:
                return department
        return None

    def _parse_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(confidence, 1.0))

    def _extract_json(self, response_text: str) -> Dict[str, Any]:
        text = (response_text or "").strip()
        if not text:
            raise ValueError("模型返回为空")
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("模型返回不包含 JSON 对象")
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            raise ValueError("模型返回 JSON 不是对象")
        return data

    def _has_red_flag(
        self,
        symptoms: str,
        structured_intake: Optional[Dict[str, Any]],
    ) -> bool:
        text = symptoms or ""
        if structured_intake:
            text += "\n" + " ".join(str(value) for value in structured_intake.values() if value)
        return any(keyword in text for keyword in self._red_flag_keywords)

    def _emergency_result(self) -> TriageResult:
        return TriageResult(
            requires_doctor=True,
            department=Department.EMERGENCY,
            department_name=DEPARTMENT_CHINESE[Department.EMERGENCY],
            urgency="emergency",
            confidence=1.0,
            reason="命中胸痛、呼吸困难、意识异常或出血等红旗症状，优先急诊处理",
            fallback_reason="red_flag",
        )

    def _fallback_result(self, fallback_reason: str, raw_response: Optional[str]) -> TriageResult:
        return TriageResult(
            requires_doctor=True,
            department=Department.GENERAL,
            department_name=DEPARTMENT_CHINESE[Department.GENERAL],
            urgency="normal",
            confidence=0.0,
            reason="分诊结果不可靠，回退全科医生先行评估",
            fallback_reason=fallback_reason,
            raw_response=raw_response,
        )

    def _format_dict(self, data: Optional[Dict[str, Any]]) -> str:
        if not data:
            return "无"
        lines = []
        for key, value in data.items():
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                value = "、".join(str(item) for item in value if item)
            elif isinstance(value, dict):
                value = "；".join(f"{k}: {v}" for k, v in value.items() if v)
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) or "无"

    def _format_reports(self, linked_reports: Optional[List[Dict[str, Any]]]) -> str:
        if not linked_reports:
            return "无"
        lines = []
        for index, report in enumerate(linked_reports[:3], start=1):
            text = (report.get("ocr_text") or "").strip()
            if len(text) > 800:
                text = text[:800] + "..."
            lines.append(f"[报告{index}] {report.get('file_name') or '未命名报告'}\n{text or '未识别到文本'}")
        return "\n\n".join(lines)

    def _summarize_diagnosis(self, diagnosis_result: Optional[Dict[str, Any]]) -> str:
        if not diagnosis_result:
            return "无"
        diagnosis = str(diagnosis_result.get("diagnosis") or "")
        if len(diagnosis) > 1200:
            diagnosis = diagnosis[:1200] + "..."
        return diagnosis or "无"


triage_service = TriageService()


__all__ = ["TriageResult", "TriageService", "triage_service"]
