"""
命名实体识别（NER）模块
基于 BERT 预训练模型的医疗命名实体识别，规则系统兜底
"""
from typing import List, Dict, Optional
from pathlib import Path
import re

import torch
from pydantic import BaseModel, Field
from transformers import BertTokenizer

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ───────────────────────────────────────────────
# 模型路径
# ───────────────────────────────────────────────
_NER_MODEL_DIR = Path("nlp_models/ner")
_NER_PKL = _NER_MODEL_DIR / "model.pkl"
_NER_VOCAB = _NER_MODEL_DIR / "vocab.txt"

# ───────────────────────────────────────────────
# BIO 标签定义（中文医疗 NER 通用标准）
# ───────────────────────────────────────────────
BIO_LABELS = [
    "O",
    "B-DISEASE", "I-DISEASE",
    "B-SYMPTOM", "I-SYMPTOM",
    "B-DRUG",    "I-DRUG",
    "B-EXAM",    "I-EXAM",
    "B-BODY",    "I-BODY",
    "B-TREATMENT", "I-TREATMENT",
]
ID2LABEL = {i: lbl for i, lbl in enumerate(BIO_LABELS)}
# BIO 前缀 → 内部实体类型
_BIO_TO_TYPE = {
    "DISEASE":   "DISEASE",
    "SYMPTOM":   "SYMPTOM",
    "DRUG":      "DRUG",
    "EXAM":      "EXAM",
    "BODY":      "BODY_PART",
    "TREATMENT": "TREATMENT",
}


# ───────────────────────────────────────────────
# 数据模型（保持接口不变，供 medical_record_parser 使用）
# ───────────────────────────────────────────────
class Entity(BaseModel):
    text:       str   = Field(description="实体文本")
    label:      str   = Field(description="实体标签")
    start:      int   = Field(description="起始位置")
    end:        int   = Field(description="结束位置")
    confidence: float = Field(default=1.0, description="置信度")


class NERResult(BaseModel):
    entities: List[Entity] = Field(description="识别的实体列表")
    text:     str          = Field(description="原始文本")


# ───────────────────────────────────────────────
# 医疗 NER 主类
# ───────────────────────────────────────────────
class MedicalNER:
    """医疗命名实体识别器（BERT 模型 + 规则增强）"""

    ENTITY_TYPES = {
        "SYMPTOM":   "症状",
        "DISEASE":   "疾病",
        "DRUG":      "药物",
        "EXAM":      "检查",
        "BODY_PART": "身体部位",
        "TIME":      "时间",
        "QUANTITY":  "数量",
        "TREATMENT": "治疗",
    }

    # ── 规则词典 ──────────────────────────────────
    _SYMPTOM_KW = [
        "疼痛","痛","疼","不适","难受","发热","发烧","体温升高",
        "咳嗽","咳","咳痰","胸闷","气短","呼吸困难","心悸","心慌",
        "心跳加速","头晕","头痛","眩晕","恶心","呕吐","反胃",
        "腹泻","便秘","便血","乏力","疲劳","无力","失眠","多梦",
        "水肿","浮肿","出血","皮疹","瘙痒","黄疸","发绀","抽搐",
        "晕厥","意识障碍","麻木","刺痛",
    ]
    _DISEASE_KW = [
        "高血压","低血压","糖尿病","高血糖","冠心病","心肌梗死","心梗",
        "心律失常","房颤","肺炎","支气管炎","哮喘","肺癌",
        "胃炎","胃溃疡","消化道出血","肝炎","肝硬化","肝癌",
        "肾炎","肾衰竭","尿毒症","脑梗死","脑出血","中风",
        "骨折","骨质疏松","关节炎","类风湿","红斑狼疮","甲亢","甲减",
        "贫血","白血病","淋巴瘤","阑尾炎","胆囊炎","胰腺炎",
    ]
    _DRUG_KW = [
        "阿司匹林","布洛芬","对乙酰氨基酚","头孢","青霉素","阿莫西林",
        "胰岛素","二甲双胍","美托洛尔","氨氯地平","地高辛","华法林",
        "氯吡格雷","他汀","辛伐他汀","阿托伐他汀","奥美拉唑","兰索拉唑",
        "甲硝唑","左氧氟沙星","阿奇霉素","利巴韦林","干扰素",
    ]
    _DRUG_SUFFIX = ["片","胶囊","丸","颗粒","口服液","注射液","针剂","散","膏","贴"]
    _EXAM_KW = [
        "血常规","尿常规","便常规","肝功能","肾功能","血脂","血糖",
        "心电图","ECG","CT","MRI","核磁","B超","彩超","超声",
        "X光","X线","胸片","内镜","胃镜","肠镜","支气管镜",
        "血压","心率","体温","呼吸频率","血氧","脉搏",
    ]
    _BODY_KW = [
        "头","头部","脑","颈","胸","胸部","心脏","心","肺","腹","腹部",
        "胃","肝","胆","脾","肾","膀胱","子宫","前列腺",
        "手","脚","腿","臂","膝","肩","腰","背","脊柱",
        "眼","耳","鼻","口","咽","喉","气管","食管",
    ]
    _TREATMENT_KW = [
        "手术","切除","化疗","放疗","介入","透析","输血","输液",
        "针灸","理疗","按摩","康复","移植","搭桥","支架",
    ]

    def __init__(self):
        self._tokenizer: Optional[BertTokenizer] = None
        self._model = None
        self._use_model = False
        self._build_patterns()
        self._load_tokenizer()
        self._load_model()

    # ── 初始化 ────────────────────────────────────
    def _build_patterns(self):
        self._time_re = re.compile(r'(\d+)\s*(天|日|周|个月|月|年|小时|分钟)')
        self._qty_re  = re.compile(r'(\d+\.?\d*)\s*(mg|g|kg|ml|μg|IU|次|片|粒|单位)', re.I)
        self._drug_suffix_re = re.compile(
            r'[\u4e00-\u9fff]{2,8}(' + '|'.join(self._DRUG_SUFFIX) + r')'
        )

    def _load_tokenizer(self):
        if _NER_VOCAB.exists():
            try:
                self._tokenizer = BertTokenizer(vocab_file=str(_NER_VOCAB))
                logger.info("NER tokenizer 加载成功")
            except Exception as e:
                logger.warning(f"NER tokenizer 加载失败: {e}")

    def _load_model(self):
        if not _NER_PKL.exists():
            logger.info("NER model.pkl 不存在，使用规则模式")
            return
        try:
            self._model = torch.load(str(_NER_PKL), map_location="cpu", weights_only=False)
            self._model.eval()
            self._use_model = True
            logger.info("NER 模型加载成功")
        except Exception as e:
            logger.warning(f"NER 模型加载失败，使用规则兜底: {e}")

    # ── 主接口 ────────────────────────────────────
    def recognize(self, text: str) -> NERResult:
        if self._use_model and self._tokenizer:
            try:
                return self._model_recognize(text)
            except Exception as e:
                logger.warning(f"NER 模型推理失败，切换规则: {e}")
        return self._rule_recognize(text)

    # ── 模型推理路径 ──────────────────────────────
    def _model_recognize(self, text: str) -> NERResult:
        tokens = self._tokenizer.tokenize(text)
        input_ids = self._tokenizer.convert_tokens_to_ids(tokens)
        input_tensor = torch.tensor([input_ids])

        with torch.no_grad():
            outputs = self._model(input_tensor)

        # 兼容不同输出格式
        logits = outputs.logits if hasattr(outputs, "logits") else outputs[0]
        predictions = torch.argmax(logits, dim=-1).squeeze().tolist()

        entities = self._bio_decode(tokens, predictions, text)
        return NERResult(entities=entities, text=text)

    def _bio_decode(
        self, tokens: List[str], label_ids: List[int], orig_text: str
    ) -> List[Entity]:
        entities: List[Entity] = []
        cur_type: Optional[str] = None
        cur_chars: List[str]   = []
        char_pos = 0

        for token, lid in zip(tokens, label_ids):
            label = ID2LABEL.get(lid, "O")
            clean = token.replace("##", "")

            if label.startswith("B-"):
                if cur_type and cur_chars:
                    entities.append(self._make_entity("".join(cur_chars), cur_type, orig_text))
                cur_type  = label[2:]
                cur_chars = [clean]
            elif label.startswith("I-") and cur_type == label[2:]:
                cur_chars.append(clean)
            else:
                if cur_type and cur_chars:
                    entities.append(self._make_entity("".join(cur_chars), cur_type, orig_text))
                cur_type  = None
                cur_chars = []

        if cur_type and cur_chars:
            entities.append(self._make_entity("".join(cur_chars), cur_type, orig_text))

        return [e for e in entities if e is not None]

    def _make_entity(self, text: str, bio_type: str, orig: str) -> Optional[Entity]:
        entity_type = _BIO_TO_TYPE.get(bio_type, bio_type)
        idx = orig.find(text)
        if idx == -1:
            return None
        return Entity(text=text, label=entity_type, start=idx, end=idx + len(text), confidence=0.88)

    # ── 规则识别路径 ──────────────────────────────
    def _rule_recognize(self, text: str) -> NERResult:
        entities: List[Entity] = []
        entities += self._match_keywords(text, self._SYMPTOM_KW,   "SYMPTOM",   0.90)
        entities += self._match_keywords(text, self._DISEASE_KW,   "DISEASE",   0.90)
        entities += self._match_keywords(text, self._DRUG_KW,      "DRUG",      0.88)
        entities += self._match_drug_suffix(text)
        entities += self._match_keywords(text, self._EXAM_KW,      "EXAM",      0.90)
        entities += self._match_keywords(text, self._BODY_KW,       "BODY_PART", 0.85)
        entities += self._match_keywords(text, self._TREATMENT_KW, "TREATMENT", 0.85)
        entities += self._match_pattern(text, self._time_re, "TIME",     0.80)
        entities += self._match_pattern(text, self._qty_re,  "QUANTITY", 0.80)
        entities = self._deduplicate(entities)
        entities.sort(key=lambda x: x.start)
        return NERResult(entities=entities, text=text)

    def _match_keywords(
        self, text: str, keywords: List[str], label: str, conf: float
    ) -> List[Entity]:
        result = []
        for kw in keywords:
            for m in re.finditer(re.escape(kw), text):
                result.append(Entity(text=kw, label=label, start=m.start(), end=m.end(), confidence=conf))
        return result

    def _match_drug_suffix(self, text: str) -> List[Entity]:
        result = []
        for m in self._drug_suffix_re.finditer(text):
            result.append(Entity(text=m.group(), label="DRUG", start=m.start(), end=m.end(), confidence=0.82))
        return result

    def _match_pattern(
        self, text: str, pattern: re.Pattern, label: str, conf: float
    ) -> List[Entity]:
        result = []
        for m in pattern.finditer(text):
            result.append(Entity(text=m.group(), label=label, start=m.start(), end=m.end(), confidence=conf))
        return result

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        seen: Dict[tuple, Entity] = {}
        for e in entities:
            key = (e.start, e.end, e.label)
            if key not in seen or seen[key].confidence < e.confidence:
                seen[key] = e
        return list(seen.values())


# ── 单例 ──────────────────────────────────────
_default_ner: Optional[MedicalNER] = None


def get_ner() -> MedicalNER:
    global _default_ner
    if _default_ner is None:
        _default_ner = MedicalNER()
    return _default_ner
