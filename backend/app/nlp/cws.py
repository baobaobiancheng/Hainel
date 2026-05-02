"""
中文分词（CWS）模块
基于 BERT 预训练模型的中文分词，字符级规则兜底
"""
from typing import List, Optional
from pathlib import Path

import torch
from transformers import BertTokenizer

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ───────────────────────────────────────────────
# 模型路径
# ───────────────────────────────────────────────
_CWS_MODEL_DIR = Path("nlp_models/cws")
_CWS_PKL       = _CWS_MODEL_DIR / "pytorch_model.pkl"
_CWS_VOCAB     = _CWS_MODEL_DIR / "vocab.txt"

# BIES 标签
_BIES_LABELS = ["B", "I", "E", "S"]
_ID2BIES     = {i: lbl for i, lbl in enumerate(_BIES_LABELS)}


class ChineseCWS:
    """中文分词器（BERT BIES 序列标注 + 字符兜底）"""

    def __init__(self):
        self._tokenizer: Optional[BertTokenizer] = None
        self._model = None
        self._use_model = False
        self._load_tokenizer()
        self._load_model()

    # ── 初始化 ────────────────────────────────────
    def _load_tokenizer(self):
        if _CWS_VOCAB.exists():
            try:
                self._tokenizer = BertTokenizer(vocab_file=str(_CWS_VOCAB))
                logger.info("CWS tokenizer 加载成功")
            except Exception as e:
                logger.warning(f"CWS tokenizer 加载失败: {e}")

    def _load_model(self):
        if not _CWS_PKL.exists():
            logger.info("CWS pytorch_model.pkl 不存在，使用字符级兜底")
            return
        try:
            self._model = torch.load(str(_CWS_PKL), map_location="cpu", weights_only=False)
            self._model.eval()
            self._use_model = True
            logger.info("CWS 模型加载成功")
        except Exception as e:
            logger.warning(f"CWS 模型加载失败，使用字符级兜底: {e}")

    # ── 主接口 ────────────────────────────────────
    def segment(self, text: str) -> List[str]:
        """
        对输入文本进行分词

        Args:
            text: 原始文本

        Returns:
            分词结果列表
        """
        if not text:
            return []
        if self._use_model and self._tokenizer:
            try:
                return self._model_segment(text)
            except Exception as e:
                logger.warning(f"CWS 模型推理失败，切换字符级: {e}")
        return self._fallback_segment(text)

    def segment_batch(self, texts: List[str]) -> List[List[str]]:
        """批量分词"""
        return [self.segment(t) for t in texts]

    # ── 模型推理路径 ──────────────────────────────
    def _model_segment(self, text: str) -> List[str]:
        chars = list(text)
        tokens = self._tokenizer.tokenize(text)
        input_ids = self._tokenizer.convert_tokens_to_ids(tokens)
        input_tensor = torch.tensor([input_ids])

        with torch.no_grad():
            outputs = self._model(input_tensor)

        logits = outputs.logits if hasattr(outputs, "logits") else outputs[0]
        preds  = torch.argmax(logits, dim=-1).squeeze().tolist()

        return self._bies_decode(chars, preds)

    def _bies_decode(self, chars: List[str], label_ids: List[int]) -> List[str]:
        """将 BIES 标签序列转为分词结果"""
        words: List[str] = []
        buf: List[str]   = []

        for char, lid in zip(chars, label_ids):
            tag = _ID2BIES.get(lid, "S")
            if tag == "B":
                buf = [char]
            elif tag == "I":
                buf.append(char)
            elif tag == "E":
                buf.append(char)
                words.append("".join(buf))
                buf = []
            else:  # S
                if buf:
                    words.append("".join(buf))
                    buf = []
                words.append(char)

        if buf:
            words.append("".join(buf))
        return words

    # ── 字符级兜底 ────────────────────────────────
    def _fallback_segment(self, text: str) -> List[str]:
        """
        不依赖外部库的纯字符级分词：
        中文字符单独成词，连续 ASCII 串归为一词
        """
        words: List[str] = []
        buf = ""
        for ch in text:
            if "\u4e00" <= ch <= "\u9fff":
                if buf:
                    words.append(buf)
                    buf = ""
                words.append(ch)
            elif ch.strip():
                buf += ch
            else:
                if buf:
                    words.append(buf)
                    buf = ""
        if buf:
            words.append(buf)
        return words


# ── 单例 ──────────────────────────────────────
_default_cws: Optional[ChineseCWS] = None


def get_cws() -> ChineseCWS:
    global _default_cws
    if _default_cws is None:
        _default_cws = ChineseCWS()
    return _default_cws
