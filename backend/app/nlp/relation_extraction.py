"""
关系抽取（RE）模块
基于 BERT 预训练模型的医疗实体关系抽取，predicate.json 定义关系类型
"""
from typing import List, Dict, Optional
from pathlib import Path
import json

import torch
from pydantic import BaseModel, Field
from transformers import BertTokenizer

from app.nlp.ner import Entity
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ───────────────────────────────────────────────
# 模型路径
# ───────────────────────────────────────────────
_RE_MODEL_DIR  = Path("nlp_models/re")
_RE_PKL        = _RE_MODEL_DIR / "model_re.pkl"
_RE_VOCAB      = _RE_MODEL_DIR / "vocab.txt"
_RE_PREDICATE  = _RE_MODEL_DIR / "predicate.json"


# ───────────────────────────────────────────────
# 数据模型
# ───────────────────────────────────────────────
class Relation(BaseModel):
    head:       str   = Field(description="头实体")
    relation:   str   = Field(description="关系类型")
    tail:       str   = Field(description="尾实体")
    confidence: float = Field(default=1.0, description="置信度")


class RelationExtractionResult(BaseModel):
    relations: List[Relation] = Field(description="抽取的关系列表")
    entities:  List[Entity]   = Field(description="实体列表")


# ───────────────────────────────────────────────
# 关系抽取主类
# ───────────────────────────────────────────────
class MedicalRelationExtractor:
    """医疗关系抽取器（BERT 模型 + 规则增强）"""

    # 内部统一关系类型（对齐 predicate.json）
    RELATION_TYPES = {
        "相关疾病":     "RELATED_DISEASE",
        "相关症状":     "RELATED_SYMPTOM",
        "临床表现":     "CLINICAL_MANIFESTATION",
        "检查":         "EXAM",
        "用法用量":     "USAGE_DOSAGE",
        "禁忌":         "CONTRAINDICATION",
        "不良反应":     "ADVERSE_REACTION",
        "适应症":       "INDICATION",
        "成分":         "INGREDIENT",
        "病因":         "ETIOLOGY",
        "治疗":         "TREATS",
        "并发症":       "COMPLICATION",
        "药物相互作用": "DRUG_INTERACTION",
        "主治":         "MAIN_INDICATION",
        "功效":         "EFFICACY",
        "功能主治":     "FUNCTION_INDICATION",
    }

    # 规则触发词 → 关系类型
    _RULE_TRIGGERS: Dict[str, List[str]] = {
        "TREATS":               ["治疗", "用于", "服用", "口服", "注射", "外用"],
        "RELATED_SYMPTOM":      ["引起", "导致", "出现", "伴有", "伴随", "表现为"],
        "EXAM":                 ["检查", "诊断", "确诊", "显示", "提示"],
        "RELATED_DISEASE":      ["并发", "继发", "合并", "诱发"],
        "CONTRAINDICATION":     ["禁忌", "禁用", "不宜", "忌用"],
        "ADVERSE_REACTION":     ["不良反应", "副作用", "副反应"],
        "ETIOLOGY":             ["因", "由于", "原因", "诱因"],
        "CLINICAL_MANIFESTATION": ["表现为", "主要表现", "临床表现"],
    }

    def __init__(self):
        self._tokenizer: Optional[BertTokenizer] = None
        self._model = None
        self._use_model = False
        self._predicates: Dict[str, int] = {}
        self._id2predicate: Dict[int, str] = {}
        self._load_predicates()
        self._load_tokenizer()
        self._load_model()

    # ── 初始化 ────────────────────────────────────
    def _load_predicates(self):
        if _RE_PREDICATE.exists():
            try:
                with open(_RE_PREDICATE, "r", encoding="utf-8") as f:
                    self._predicates = json.load(f)
                self._id2predicate = {v: k for k, v in self._predicates.items()}
                logger.info(f"加载 {len(self._predicates)} 个关系谓词")
            except Exception as e:
                logger.warning(f"predicate.json 加载失败: {e}")

    def _load_tokenizer(self):
        if _RE_VOCAB.exists():
            try:
                self._tokenizer = BertTokenizer(vocab_file=str(_RE_VOCAB))
                logger.info("RE tokenizer 加载成功")
            except Exception as e:
                logger.warning(f"RE tokenizer 加载失败: {e}")

    def _load_model(self):
        if not _RE_PKL.exists():
            logger.info("RE model_re.pkl 不存在，使用规则模式")
            return
        try:
            self._model = torch.load(str(_RE_PKL), map_location="cpu", weights_only=False)
            self._model.eval()
            self._use_model = True
            logger.info("RE 模型加载成功")
        except Exception as e:
            logger.warning(f"RE 模型加载失败，使用规则兜底: {e}")

    # ── 主接口 ────────────────────────────────────
    def extract(
        self,
        text: str,
        entities: List[Entity],
        max_distance: int = 80,
    ) -> RelationExtractionResult:
        if self._use_model and self._tokenizer and len(entities) >= 2:
            try:
                return self._model_extract(text, entities)
            except Exception as e:
                logger.warning(f"RE 模型推理失败，切换规则: {e}")
        return self._rule_extract(text, entities, max_distance)

    # ── 模型推理路径 ──────────────────────────────
    def _model_extract(self, text: str, entities: List[Entity]) -> RelationExtractionResult:
        relations: List[Relation] = []
        entity_pairs = [
            (e1, e2) for i, e1 in enumerate(entities)
            for e2 in entities[i + 1:]
            if e1.label != e2.label
        ]
        for subj, obj in entity_pairs:
            rel = self._predict_relation(text, subj, obj)
            if rel:
                relations.append(rel)
        return RelationExtractionResult(relations=relations, entities=entities)

    def _predict_relation(
        self, text: str, subj: Entity, obj: Entity
    ) -> Optional[Relation]:
        # 构造 [CLS] 句子 [SEP] 主体 [SEP] 客体 [SEP] 输入格式
        encoded = self._tokenizer(
            text,
            f"{subj.text}[SEP]{obj.text}",
            max_length=128,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = self._model(**encoded)
        logits = outputs.logits if hasattr(outputs, "logits") else outputs[0]
        pred_id = int(torch.argmax(logits, dim=-1).item())
        predicate = self._id2predicate.get(pred_id)
        if predicate and predicate != "O":
            return Relation(
                head=subj.text,
                relation=predicate,
                tail=obj.text,
                confidence=float(torch.softmax(logits, dim=-1).max().item()),
            )
        return None

    # ── 规则抽取路径 ──────────────────────────────
    def _rule_extract(
        self, text: str, entities: List[Entity], max_distance: int
    ) -> RelationExtractionResult:
        relations: List[Relation] = []
        relations += self._extract_drug_disease(text, entities, max_distance)
        relations += self._extract_symptom_disease(text, entities, max_distance)
        relations += self._extract_exam_disease(text, entities, max_distance)
        relations += self._extract_symptom_body(text, entities, max_distance)
        relations += self._extract_time_event(text, entities, max_distance)
        return RelationExtractionResult(relations=relations, entities=entities)

    def _pair_in_range(
        self, e1: Entity, e2: Entity, text: str, max_dist: int
    ) -> Optional[str]:
        """返回两实体之间的上下文片段，超出距离返回 None"""
        dist = abs(e1.start - e2.start)
        if dist > max_dist:
            return None
        s, e = sorted([e1.start, e2.start]), sorted([e1.end, e2.end])
        return text[s[0]:e[-1]]

    def _has_trigger(self, context: str, triggers: List[str]) -> bool:
        return any(t in context for t in triggers)

    def _extract_drug_disease(
        self, text: str, entities: List[Entity], max_dist: int
    ) -> List[Relation]:
        result = []
        drugs    = [e for e in entities if e.label == "DRUG"]
        diseases = [e for e in entities if e.label == "DISEASE"]
        for drug in drugs:
            for dis in diseases:
                ctx = self._pair_in_range(drug, dis, text, max_dist)
                if ctx and self._has_trigger(ctx, self._RULE_TRIGGERS["TREATS"]):
                    result.append(Relation(head=drug.text, relation="治疗", tail=dis.text, confidence=0.82))
        return result

    def _extract_symptom_disease(
        self, text: str, entities: List[Entity], max_dist: int
    ) -> List[Relation]:
        result = []
        symptoms = [e for e in entities if e.label == "SYMPTOM"]
        diseases = [e for e in entities if e.label == "DISEASE"]
        for sym in symptoms:
            for dis in diseases:
                ctx = self._pair_in_range(sym, dis, text, max_dist)
                if ctx and self._has_trigger(ctx, self._RULE_TRIGGERS["RELATED_SYMPTOM"]):
                    result.append(Relation(head=dis.text, relation="相关症状", tail=sym.text, confidence=0.78))
        return result

    def _extract_exam_disease(
        self, text: str, entities: List[Entity], max_dist: int
    ) -> List[Relation]:
        result = []
        exams    = [e for e in entities if e.label == "EXAM"]
        diseases = [e for e in entities if e.label == "DISEASE"]
        for exam in exams:
            for dis in diseases:
                ctx = self._pair_in_range(exam, dis, text, max_dist)
                if ctx and self._has_trigger(ctx, self._RULE_TRIGGERS["EXAM"]):
                    result.append(Relation(head=dis.text, relation="检查", tail=exam.text, confidence=0.78))
        return result

    def _extract_symptom_body(
        self, text: str, entities: List[Entity], max_dist: int
    ) -> List[Relation]:
        result = []
        symptoms   = [e for e in entities if e.label == "SYMPTOM"]
        body_parts = [e for e in entities if e.label == "BODY_PART"]
        for sym in symptoms:
            for bp in body_parts:
                ctx = self._pair_in_range(sym, bp, text, max_dist)
                if ctx and self._has_trigger(ctx, ["的", "在", "位于", "部位"]):
                    result.append(Relation(head=sym.text, relation="临床表现", tail=bp.text, confidence=0.72))
        return result

    def _extract_time_event(
        self, text: str, entities: List[Entity], max_dist: int
    ) -> List[Relation]:
        result = []
        times    = [e for e in entities if e.label == "TIME"]
        events   = [e for e in entities if e.label in ("SYMPTOM", "DISEASE")]
        for t in times:
            for ev in events:
                if abs(t.start - ev.start) <= max_dist:
                    result.append(Relation(head=ev.text, relation="病程", tail=t.text, confidence=0.70))
        return result


# ── 单例 ──────────────────────────────────────
_default_extractor: Optional[MedicalRelationExtractor] = None


def get_relation_extractor() -> MedicalRelationExtractor:
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = MedicalRelationExtractor()
    return _default_extractor
