"""
病历解析器
从非结构化文本中提取结构化病历信息
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.nlp.ner import get_ner
from app.nlp.relation_extraction import get_relation_extractor
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 用于单例模式
_default_parser = None


class StructuredMedicalRecord(BaseModel):
    """结构化病历模型"""
    # 基本信息
    chief_complaint: str = Field(default="", description="主诉")
    present_illness: str = Field(default="", description="现病史")
    past_history: str = Field(default="", description="既往史")
    family_history: str = Field(default="", description="家族史")
    
    # 结构化信息
    symptoms: List[Dict[str, Any]] = Field(default_factory=list, description="症状列表")
    diseases: List[str] = Field(default_factory=list, description="疾病列表")
    drugs: List[str] = Field(default_factory=list, description="药物列表")
    exams: List[str] = Field(default_factory=list, description="检查列表")
    
    # 时间信息
    duration: Optional[str] = Field(default=None, description="持续时间")
    onset_time: Optional[str] = Field(default=None, description="发病时间")
    
    # 元数据
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="实体列表")
    relations: List[Dict[str, Any]] = Field(default_factory=list, description="关系列表")
    raw_text: str = Field(default="", description="原始文本")


class MedicalRecordParser:
    """病历解析器"""
    
    def __init__(self):
        """初始化病历解析器"""
        self.ner = get_ner()
        self.relation_extractor = get_relation_extractor()
    
    def parse(self, text: str) -> StructuredMedicalRecord:
        """
        解析病历文本
        
        Args:
            text: 病历文本
            
        Returns:
            StructuredMedicalRecord: 结构化病历
        """
        try:
            # NER识别
            ner_result = self.ner.recognize(text)
            
            # 关系抽取
            relation_result = self.relation_extractor.extract(
                text,
                ner_result.entities
            )
            
            # 构建结构化病历
            structured_record = self._build_structured_record(
                text,
                ner_result,
                relation_result
            )
            
            return structured_record
        except Exception as e:
            logger.error(f"病历解析失败: {e}", exc_info=True)
            raise
    
    def _build_structured_record(
        self,
        text: str,
        ner_result,
        relation_result
    ) -> StructuredMedicalRecord:
        """构建结构化病历"""
        # 提取主诉（通常是第一句话或包含症状的第一段）
        chief_complaint = self._extract_chief_complaint(text, ner_result.entities)
        
        # 提取症状
        symptoms = self._extract_symptoms(ner_result.entities, relation_result.relations)
        
        # 提取疾病
        diseases = list(set([
            e.text for e in ner_result.entities
            if e.label == "DISEASE"
        ]))
        
        # 提取药物
        drugs = list(set([
            e.text for e in ner_result.entities
            if e.label == "DRUG"
        ]))
        
        # 提取检查
        exams = list(set([
            e.text for e in ner_result.entities
            if e.label == "EXAM"
        ]))
        
        # 提取时间信息
        time_entities = [e for e in ner_result.entities if e.label == "TIME"]
        duration = time_entities[0].text if time_entities else None
        
        # 转换实体和关系为字典格式
        entities_dict = [
            {
                "text": e.text,
                "label": e.label,
                "start": e.start,
                "end": e.end,
                "confidence": e.confidence,
            }
            for e in ner_result.entities
        ]
        
        relations_dict = [
            {
                "head": r.head,
                "relation": r.relation,
                "tail": r.tail,
                "confidence": r.confidence,
            }
            for r in relation_result.relations
        ]
        
        return StructuredMedicalRecord(
            chief_complaint=chief_complaint,
            present_illness=text,  # 暂时使用全文作为现病史
            symptoms=symptoms,
            diseases=diseases,
            drugs=drugs,
            exams=exams,
            duration=duration,
            entities=entities_dict,
            relations=relations_dict,
            raw_text=text,
        )
    
    def _extract_chief_complaint(
        self,
        text: str,
        entities: List
    ) -> str:
        """提取主诉"""
        # 找到第一个症状实体
        symptom_entities = [e for e in entities if e.label == "SYMPTOM"]
        if symptom_entities:
            first_symptom = min(symptom_entities, key=lambda x: x.start)
            # 提取包含该症状的句子
            start = max(0, first_symptom.start - 50)
            end = min(len(text), first_symptom.end + 50)
            return text[start:end].strip()
        return ""
    
    def _extract_symptoms(
        self,
        entities: List,
        relations: List
    ) -> List[Dict[str, Any]]:
        """提取症状信息"""
        symptoms = []
        
        symptom_entities = [e for e in entities if e.label == "SYMPTOM"]
        
        for symptom_entity in symptom_entities:
            symptom_info = {
                "name": symptom_entity.text,
                "confidence": symptom_entity.confidence,
            }
            
            # 查找相关关系
            for relation in relations:
                if relation.head == symptom_entity.text:
                    if relation.relation == "LOCATED_IN":
                        symptom_info["location"] = relation.tail
                    elif relation.relation == "OCCURS_AT":
                        symptom_info["time"] = relation.tail
            
            symptoms.append(symptom_info)
        
        return symptoms


# 创建默认解析器实例
_default_parser: Optional[MedicalRecordParser] = None


def get_medical_record_parser() -> MedicalRecordParser:
    """
    获取病历解析器实例（单例模式）
    
    Returns:
        MedicalRecordParser: 病历解析器实例
    """
    global _default_parser
    if _default_parser is None:
        _default_parser = MedicalRecordParser()
    return _default_parser

