"""
NLP 处理模块
"""
from app.nlp.ner import MedicalNER, Entity, NERResult, get_ner
from app.nlp.relation_extraction import (
    MedicalRelationExtractor,
    Relation,
    RelationExtractionResult,
    get_relation_extractor,
)
from app.nlp.cws import ChineseCWS, get_cws
from app.nlp.medical_record_parser import (
    MedicalRecordParser,
    StructuredMedicalRecord,
    get_medical_record_parser,
)

__all__ = [
    # NER
    "MedicalNER",
    "Entity",
    "NERResult",
    "get_ner",
    # 关系抽取
    "MedicalRelationExtractor",
    "Relation",
    "RelationExtractionResult",
    "get_relation_extractor",
    # 中文分词
    "ChineseCWS",
    "get_cws",
    # 病历解析
    "MedicalRecordParser",
    "StructuredMedicalRecord",
    "get_medical_record_parser",
]
