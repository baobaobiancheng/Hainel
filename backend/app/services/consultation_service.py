import os
from typing import Any, Dict, List, Optional

from app.config import settings
from app.agents.mdagents import Agent, Group, parse_group_info
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConsultationService:
    """咨询服务类 - 调用 MDAgents 多智能体系统进行症状诊断"""

    def __init__(self):
        self._model = settings.DEEPSEEK_MODEL or "deepseek-v4-flash"
        self._red_flag_rules = {
            "胸痛": ["胸痛", "胸口痛", "胸闷", "胸口压榨", "心绞痛"],
            "呼吸困难": ["呼吸困难", "喘不上气", "气短", "憋气", "窒息感"],
            "意识异常": ["意识不清", "昏迷", "昏厥", "晕厥", "抽搐", "说话不清"],
            "剧烈头痛": ["剧烈头痛", "爆炸样头痛", "头痛欲裂"],
            "大出血": ["大出血", "止不住血", "咯血", "呕血", "黑便"],
            "高热": ["高烧不退", "持续高热", "体温40", "40度"],
            "严重过敏": ["喉头水肿", "全身皮疹", "过敏性休克"],
        }

    def _configure_mdagents_env(self) -> None:
        """把项目配置同步给 mdagents 中的 OpenAI 兼容客户端。"""
        api_key = settings.DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = settings.DEEPSEEK_BASE_URL or os.environ.get(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com",
        )
        if api_key:
            os.environ.setdefault("DEEPSEEK_API_KEY", api_key)
        if base_url:
            os.environ.setdefault("DEEPSEEK_BASE_URL", base_url)
        os.environ.setdefault("DEEPSEEK_MODEL", self._model)

    def _ensure_mdagents_available(self) -> None:
        self._configure_mdagents_env()
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise RuntimeError("MDAgents 未配置 DeepSeek API Key，无法调用真实多智能体诊断")

    def _format_dict(self, data: Optional[Dict[str, Any]]) -> str:
        if not data:
            return ""
        labels = {
            "birth_date": "出生日期",
            "age": "年龄",
            "gender": "性别",
            "height_cm": "身高(cm)",
            "weight_kg": "体重(kg)",
            "past_history": "既往病史",
            "allergies": "过敏史",
            "long_term_medications": "长期用药",
            "chronic_diseases": "慢性病",
            "family_history": "家族史",
            "surgery_history": "手术史",
            "pregnancy_status": "妊娠/哺乳状态",
            "main_symptom": "本次主要症状",
            "duration": "持续时间",
            "accompanying_symptoms": "伴随症状",
            "pain_location": "疼痛部位",
            "pain_level": "疼痛程度",
            "fever": "是否发热",
            "recent_medication": "近期用药",
            "red_flag_notes": "红旗症状补充",
        }
        lines = []
        for key, value in data.items():
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                value = "、".join(str(item) for item in value if item)
            elif isinstance(value, dict):
                value = "；".join(f"{k}: {v}" for k, v in value.items() if v)
            lines.append(f"- {labels.get(key, key)}: {value}")
        return "\n".join(lines)

    def _format_reports(self, linked_reports: Optional[List[Dict[str, Any]]]) -> str:
        if not linked_reports:
            return ""
        lines = []
        for index, report in enumerate(linked_reports[:3], start=1):
            text = (report.get("ocr_text") or "").strip()
            if len(text) > 1200:
                text = text[:1200] + "..."
            lines.append(
                f"[报告{index}] {report.get('file_name') or '未命名报告'}"
                f"（{report.get('report_type') or report.get('file_type') or '未知类型'}）\n{text or '未识别到文本'}"
            )
        return "\n\n".join(lines)

    def _get_kg_context(
        self,
        symptoms: str,
        structured_intake: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """查询知识图谱上下文，失败时降级为空上下文。"""
        query_text = symptoms or ""
        if structured_intake:
            query_text += "\n" + self._format_dict(structured_intake)
        if not query_text.strip():
            return {"entities": [], "knowledge": [], "summary": ""}
        try:
            from app.knowledge.kg_service import get_kg_query_service

            return get_kg_query_service().query_by_text(query_text, depth=2, limit=30)
        except Exception as e:
            logger.warning(f"知识图谱查询失败，跳过 KG 增强: {e}", exc_info=True)
            return {"entities": [], "knowledge": [], "summary": "", "error": str(e)}

    def _create_question(
        self,
        symptoms: str,
        medical_history: Optional[str] = None,
        health_profile: Optional[Dict[str, Any]] = None,
        structured_intake: Optional[Dict[str, Any]] = None,
        linked_reports: Optional[List[Dict[str, Any]]] = None,
        kg_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        context = f"患者主诉: {symptoms.strip()}"
        if medical_history:
            context += f"\n既往病史/会话背景: {medical_history.strip()}"
        profile_text = self._format_dict(health_profile)
        if profile_text:
            context += f"\n\n用户长期健康档案:\n{profile_text}"
        intake_text = self._format_dict(structured_intake)
        if intake_text:
            context += f"\n\n本次结构化问诊信息:\n{intake_text}"
        report_text = self._format_reports(linked_reports)
        if report_text:
            context += f"\n\n已上传报告OCR摘要:\n{report_text}"
        kg_summary = (kg_context or {}).get("summary")
        if kg_summary:
            context += f"\n\n知识图谱辅助信息:\n{kg_summary}"

        return f"""{context}

请基于以上患者信息进行中文辅助诊断分析。输出必须包含：
1. 初步判断与可能原因
2. 需要进一步确认的关键信息
3. 建议检查或观察项目
4. 处理建议与生活注意事项
5. 是否需要及时线下就医或急诊

注意：这是面向患者端的健康咨询回复，请表达清晰、谨慎，不要给出绝对诊断。"""

    def _detect_red_flags(
        self,
        symptoms: str,
        structured_intake: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        text = symptoms or ""
        if structured_intake:
            text += "\n" + self._format_dict(structured_intake)
        matches = []
        for category, keywords in self._red_flag_rules.items():
            hit_keywords = [keyword for keyword in keywords if keyword in text]
            if hit_keywords:
                matches.append({"category": category, "keywords": hit_keywords})
        return matches

    def _build_emergency_result(
        self,
        symptoms: str,
        red_flags: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        flag_names = "、".join(item["category"] for item in red_flags)
        diagnosis = f"""根据您描述的信息，系统识别到可能的红旗症状：{flag_names}。

这类情况可能存在急症风险。请优先考虑立即前往急诊或拨打当地急救电话，不建议仅依赖线上咨询继续等待。

在就医前请注意：
1. 避免独自行动，尽量由家人或朋友陪同。
2. 准备好既往病史、过敏史、长期用药和最近检查报告。
3. 若出现胸痛加重、呼吸困难、意识不清、持续出血或抽搐，请立即急救处理。"""
        return {
            "diagnosis": diagnosis,
            "difficulty": "urgent",
            "agents_used": 0,
            "red_flags": red_flags,
            "action_checklist": {
                "observe": ["记录症状开始时间、变化速度、伴随表现"],
                "exams": ["由急诊医生根据现场情况决定心电图、血压血氧、血常规、影像等检查"],
                "when_to_seek_care": ["现在就医或拨打急救电话"],
                "lifestyle": ["等待救援期间保持安静，避免进食饮酒和剧烈活动"],
            },
        }

    def _default_action_checklist(self, diagnosis: str) -> Dict[str, List[str]]:
        return {
            "observe": ["观察症状变化、持续时间、诱发或缓解因素", "记录体温、心率、血压等可测指标"],
            "exams": ["根据医生建议完善相关检查", "如已上传报告，请结合报告结果复诊确认"],
            "when_to_seek_care": ["症状加重、持续不缓解或出现红旗症状时及时线下就医"],
            "lifestyle": ["规律作息，清淡饮食，避免自行加减药物", "保持报告和用药记录，便于医生判断"],
        }

    def _new_agent(self, instruction: str, role: str) -> Agent:
        self._ensure_mdagents_available()
        agent = Agent(instruction=instruction, role=role, model_info=self._model)
        agent.chat(instruction)
        return agent

    def _determine_complexity(
        self,
        symptoms: str,
        medical_history: Optional[str] = None,
        health_profile: Optional[Dict[str, Any]] = None,
        structured_intake: Optional[Dict[str, Any]] = None,
        linked_reports: Optional[List[Dict[str, Any]]] = None,
        kg_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """使用 MDAgents 的医学智能体判断病例复杂度。"""
        question = self._create_question(
            symptoms,
            medical_history,
            health_profile,
            structured_intake,
            linked_reports,
            kg_context,
        )
        prompt = f"""请判断以下医疗咨询的复杂程度：

{question}

请从以下三个级别中选择最合适的：
1. basic（基础）: 症状简单，单个医生即可诊断
2. intermediate（中等）: 需要多个不同专科的医生讨论
3. advanced（复杂）: 需要多个医疗团队协作

请只返回 basic、intermediate 或 advanced 中的一个词，不要返回其他内容。"""

        triage_agent = self._new_agent(
            instruction="你是一位经验丰富的分诊医生，负责评估病例复杂程度。",
            role="triage doctor",
        )
        result = triage_agent.chat(prompt).lower().strip()

        if "basic" in result:
            return "basic"
        if "intermediate" in result:
            return "intermediate"
        if "advanced" in result:
            return "advanced"
        return "basic"

    def _process_basic(
        self,
        symptoms: str,
        medical_history: Optional[str] = None,
        health_profile: Optional[Dict[str, Any]] = None,
        structured_intake: Optional[Dict[str, Any]] = None,
        linked_reports: Optional[List[Dict[str, Any]]] = None,
        kg_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """基础级别：调用单个 MDAgents 医学智能体。"""
        medical_agent = self._new_agent(
            instruction="你是一位专业、严谨的全科医生，负责为患者提供中文健康咨询和辅助诊断建议。",
            role="general practitioner",
        )
        diagnosis = medical_agent.chat(
            self._create_question(
                symptoms,
                medical_history,
                health_profile,
                structured_intake,
                linked_reports,
                kg_context,
            )
        )

        return {
            "diagnosis": diagnosis,
            "difficulty": "basic",
            "agents_used": 1,
            "action_checklist": self._default_action_checklist(diagnosis),
        }

    def _parse_recruited_agents(self, recruited: str) -> List[Dict[str, str]]:
        agents: List[Dict[str, str]] = []
        for line in recruited.splitlines():
            line = line.strip()
            if not line or "." not in line or "-" not in line:
                continue
            try:
                role_part, description_part = line.split("-", 1)
                role = role_part.split(".", 1)[1].strip()
                description = description_part.split("Hierarchy:", 1)[0].strip(" -")
                if role and description:
                    agents.append({"role": role, "description": description})
            except (IndexError, ValueError):
                continue
        return agents[:5]

    def _process_intermediate(
        self,
        symptoms: str,
        medical_history: Optional[str] = None,
        health_profile: Optional[Dict[str, Any]] = None,
        structured_intake: Optional[Dict[str, Any]] = None,
        linked_reports: Optional[List[Dict[str, Any]]] = None,
        kg_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """中等复杂度：调用 MDAgents 多个专科智能体协同会诊。"""
        question = self._create_question(
            symptoms,
            medical_history,
            health_profile,
            structured_intake,
            linked_reports,
            kg_context,
        )
        recruiter = self._new_agent(
            instruction="你是一位医疗团队负责人，擅长根据病例招募不同专科医生进行会诊。",
            role="recruiter",
        )
        recruitment = recruiter.chat(f"""请为以下病例招募5位不同专科医生。

病例：
{question}

请严格按以下格式输出，不要添加额外解释：
1. 专科医生名称 - 专业职责描述 - Hierarchy: Independent
2. 专科医生名称 - 专业职责描述 - Hierarchy: Independent""")

        recruited_agents = self._parse_recruited_agents(recruitment)
        if not recruited_agents:
            recruited_agents = [
                {"role": "全科医生", "description": "负责整体病情评估"},
                {"role": "内科医生", "description": "负责常见内科疾病鉴别"},
                {"role": "急诊医生", "description": "负责识别危险信号"},
                {"role": "药师", "description": "负责用药风险和注意事项"},
                {"role": "健康管理师", "description": "负责生活方式和随访建议"},
            ]

        opinions = []
        for info in recruited_agents:
            agent = self._new_agent(
                instruction=f"你是一位{info['role']}，{info['description']}。你需要参与多智能体医疗会诊。",
                role=info["role"],
            )
            opinion = agent.chat(f"""请从你的专科角度分析以下病例，并给出关键判断、风险点和建议。

{question}""")
            opinions.append({"role": info["role"], "opinion": opinion})

        opinion_text = "\n\n".join(f"[{item['role']}]\n{item['opinion']}" for item in opinions)
        moderator = self._new_agent(
            instruction="你是多智能体会诊主持人，负责综合各专科医生意见并形成面向患者的中文最终建议。",
            role="moderator",
        )
        diagnosis = moderator.chat(f"""以下是多位医学智能体的会诊意见：

{opinion_text}

请综合各方意见，输出面向患者的最终辅助诊断建议。必须包含：
1. 综合判断
2. 主要依据
3. 需要补充询问的信息
4. 建议检查/处理
5. 就医紧急程度""")

        return {
            "diagnosis": diagnosis,
            "difficulty": "intermediate",
            "agents_used": len(recruited_agents),
            "team_recruitment": recruitment,
            "expert_opinions": opinions,
            "action_checklist": self._default_action_checklist(diagnosis),
        }

    def _process_advanced(
        self,
        symptoms: str,
        medical_history: Optional[str] = None,
        health_profile: Optional[Dict[str, Any]] = None,
        structured_intake: Optional[Dict[str, Any]] = None,
        linked_reports: Optional[List[Dict[str, Any]]] = None,
        kg_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """复杂病例：调用 MDAgents 的 Group 组织多学科团队协作。"""
        question = self._create_question(
            symptoms,
            medical_history,
            health_profile,
            structured_intake,
            linked_reports,
            kg_context,
        )
        organizer = self._new_agent(
            instruction="你是一位资深医疗专家，负责为复杂病例组织多学科诊疗团队。",
            role="MDT organizer",
        )
        mdt_plan = organizer.chat(f"""请为以下复杂病例组织3个多学科诊疗团队：

病例：
{question}

请严格按以下格式输出：
Group 1 - Initial Assessment Team
Member 1: 专科医生名称 (Lead) - 专业职责描述
Member 2: 专科医生名称 - 专业职责描述
Member 3: 专科医生名称 - 专业职责描述

Group 2 - Specialist Consultation Team
Member 1: 专科医生名称 (Lead) - 专业职责描述
Member 2: 专科医生名称 - 专业职责描述
Member 3: 专科医生名称 - 专业职责描述

Group 3 - Final Review and Decision Team
Member 1: 专科医生名称 (Lead) - 专业职责描述
Member 2: 专科医生名称 - 专业职责描述
Member 3: 专科医生名称 - 专业职责描述""")

        group_reports = []
        groups = [group.strip() for group in mdt_plan.split("Group") if group.strip()]
        for group_text in groups[:3]:
            group_info = parse_group_info("Group " + group_text)
            if not group_info["members"]:
                continue
            group = Group(
                goal=group_info["group_goal"],
                members=group_info["members"],
                question=question,
                model=self._model,
            )
            report = group.interact(comm_type="internal")
            group_reports.append({"group": group_info["group_goal"], "report": report})

        report_text = "\n\n".join(f"[{item['group']}]\n{item['report']}" for item in group_reports)
        decision_maker = self._new_agent(
            instruction="你是MDT最终决策者，负责综合多团队意见并形成谨慎、清晰的患者端中文建议。",
            role="MDT decision maker",
        )
        diagnosis = decision_maker.chat(f"""以下是多个医疗团队的分析报告：

{report_text or mdt_plan}

原始病例：
{question}

请输出最终辅助诊断建议，包含综合判断、风险分层、建议检查、处理方案、随访建议和急诊提醒。""")

        return {
            "diagnosis": diagnosis,
            "difficulty": "advanced",
            "agents_used": f"{len(group_reports) or 3}_teams",
            "mdt_plan": mdt_plan,
            "team_reports": group_reports,
            "action_checklist": self._default_action_checklist(diagnosis),
        }

    def diagnose(
        self,
        symptoms: str,
        medical_history: Optional[str] = None,
        difficulty: Optional[str] = None,
        health_profile: Optional[Dict[str, Any]] = None,
        structured_intake: Optional[Dict[str, Any]] = None,
        linked_reports: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        诊断接口

        Args:
            symptoms: 患者描述的症状
            medical_history: 既往病史（可选）
            difficulty: 难度级别，可选 basic/intermediate/advanced，默认自动判断

        Returns:
            诊断结果字典
        """
        logger.info(f"[MDAgents] 开始真实多智能体诊断 - 症状: {symptoms[:50]}...")

        kg_context = self._get_kg_context(symptoms, structured_intake)
        red_flags = self._detect_red_flags(symptoms, structured_intake)
        if red_flags:
            logger.warning(f"[MDAgents] 命中红旗症状，跳过模型诊断: {red_flags}")
            urgent_result = self._build_emergency_result(symptoms, red_flags)
            return {
                "success": True,
                "symptoms": symptoms,
                "medical_history": medical_history,
                "health_profile": health_profile,
                "structured_intake": structured_intake,
                "linked_reports": linked_reports,
                "kg_context": kg_context,
                "complexity": "urgent",
                **urgent_result,
            }

        self._ensure_mdagents_available()

        # 自动判断复杂度
        if difficulty is None:
            difficulty = self._determine_complexity(
                symptoms,
                medical_history,
                health_profile,
                structured_intake,
                linked_reports,
                kg_context,
            )
            logger.info(f"[MDAgents] 自动判断复杂度: {difficulty}")

        # 根据复杂度选择处理方式
        if difficulty == "basic":
            result = self._process_basic(
                symptoms,
                medical_history,
                health_profile,
                structured_intake,
                linked_reports,
                kg_context,
            )
        elif difficulty == "intermediate":
            result = self._process_intermediate(
                symptoms,
                medical_history,
                health_profile,
                structured_intake,
                linked_reports,
                kg_context,
            )
        else:  # advanced
            result = self._process_advanced(
                symptoms,
                medical_history,
                health_profile,
                structured_intake,
                linked_reports,
                kg_context,
            )

        logger.info(f"[MDAgents] 诊断完成 - 复杂度: {difficulty}")

        return {
            "success": True,
            "symptoms": symptoms,
            "medical_history": medical_history,
            "health_profile": health_profile,
            "structured_intake": structured_intake,
            "linked_reports": linked_reports,
            "kg_context": kg_context,
            "red_flags": [],
            "complexity": difficulty,
            **result,
        }


# 创建全局服务实例
consultation_service = ConsultationService()

__all__ = ["ConsultationService", "consultation_service"]
