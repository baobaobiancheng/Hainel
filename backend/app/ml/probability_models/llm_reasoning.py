"""
基于大语言模型的概率推理
使用LLM进行疾病概率计算
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import re

from app.ai.llm.base import BaseLLMService
from app.ai.llm.qwen import get_qwen_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiseaseProbability(BaseModel):
    """疾病概率模型"""
    disease: str = Field(description="疾病名称")
    probability: float = Field(description="概率值（0-1）")
    confidence: float = Field(default=0.0, description="置信度")
    evidence: List[str] = Field(default_factory=list, description="支持证据")
    reasoning: Optional[str] = Field(default=None, description="推理过程")


class LLMProbabilityModel:
    """基于LLM的概率模型"""
    
    def __init__(self, llm_service: Optional[BaseLLMService] = None):
        """
        初始化LLM概率模型
        
        Args:
            llm_service: LLM服务实例
        """
        self.llm_service = llm_service or get_qwen_service()
        self._disease_list = []  # 可配置的疾病列表
    
    def predict(
        self,
        symptoms: List[str],
        patient_data: Dict[str, Any],
        top_k: int = 5
    ) -> List[DiseaseProbability]:
        """
        预测疾病概率
        
        Args:
            symptoms: 症状列表
            patient_data: 患者数据（年龄、性别、检查结果等）
            top_k: 返回前k个疾病
            
        Returns:
            List[DiseaseProbability]: 疾病概率列表
        """
        try:
            # 构建提示词
            prompt = self._build_prompt(symptoms, patient_data)
            
            # 调用LLM
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=self._get_system_prompt(),
                temperature=0.3,  # 降低温度以获得更稳定的结果
            )
            
            # 解析响应
            probabilities = self._parse_response(response.content)
            
            # 排序并返回top_k
            probabilities.sort(key=lambda x: x.probability, reverse=True)
            return probabilities[:top_k]
        except Exception as e:
            logger.error(f"LLM概率预测失败: {e}", exc_info=True)
            raise
    
    def _build_prompt(
        self,
        symptoms: List[str],
        patient_data: Dict[str, Any]
    ) -> str:
        """构建提示词"""
        prompt = f"""请根据以下患者信息，评估可能的疾病及其概率。

患者症状：
{', '.join(symptoms)}

患者信息：
- 年龄：{patient_data.get('age', '未知')}
- 性别：{patient_data.get('gender', '未知')}
- 检查结果：{json.dumps(patient_data.get('exam_results', {}), ensure_ascii=False)}

请以JSON格式返回结果，格式如下：
{{
    "diseases": [
        {{
            "disease": "疾病名称",
            "probability": 0.85,
            "confidence": 0.9,
            "evidence": ["证据1", "证据2"],
            "reasoning": "推理过程"
        }}
    ]
}}

只返回JSON，不要其他文字。"""
        return prompt
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位经验丰富的医生，擅长根据患者症状和检查结果进行疾病诊断。
请基于医学知识，客观评估各种疾病的可能性，并给出概率值（0-1之间）。
概率值应该反映该疾病的可能性，考虑症状的典型性、检查结果的符合度等因素。"""
    
    def _parse_response(self, response_text: str) -> List[DiseaseProbability]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                diseases = []
                for item in data.get("diseases", []):
                    diseases.append(DiseaseProbability(
                        disease=item.get("disease", ""),
                        probability=float(item.get("probability", 0.0)),
                        confidence=float(item.get("confidence", 0.0)),
                        evidence=item.get("evidence", []),
                        reasoning=item.get("reasoning"),
                    ))
                return diseases
            else:
                logger.warning("无法从响应中提取JSON")
                return []
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}", exc_info=True)
            return []


# 创建默认模型实例
_default_llm_model: Optional[LLMProbabilityModel] = None


def get_llm_probability_model(
    llm_service: Optional[BaseLLMService] = None
) -> LLMProbabilityModel:
    """
    获取LLM概率模型实例（单例模式）
    
    Args:
        llm_service: LLM服务实例
        
    Returns:
        LLMProbabilityModel: LLM概率模型实例
    """
    global _default_llm_model
    if _default_llm_model is None:
        _default_llm_model = LLMProbabilityModel(llm_service=llm_service)
    return _default_llm_model

