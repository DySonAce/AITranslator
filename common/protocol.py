"""
common/protocol.py ─ 資料結構 & 語言對應表
==========================================
定義 Worker 間傳遞的資料格式，
以及 UI 語言名稱 → PaddleOCR / NLLB 代碼的對應。
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np


# ═══════════════════════════════════════════════════════════════
# 資料結構
# ═══════════════════════════════════════════════════════════════

@dataclass
class TextBlock:
    """單一 OCR 辨識區塊"""
    box: List[List[float]]          # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    text: str                        # 辨識文字
    confidence: float = 1.0          # 信心度
    bg_color: Tuple[int,int,int] = (17, 22, 26)
    fg_color: Tuple[int,int,int] = (200, 200, 200)


@dataclass
class OCRResult:
    """OCR 辨識結果"""
    blocks: List[TextBlock] = field(default_factory=list)
    lang: str = "en"
    elapsed: float = 0.0


@dataclass
class TranslateResult:
    """翻譯結果"""
    originals: List[str] = field(default_factory=list)
    translated: List[str] = field(default_factory=list)
    src_lang: str = "eng_Latn"
    tgt_lang: str = "zho_Hant"
    elapsed: float = 0.0


# ═══════════════════════════════════════════════════════════════
# 語言對應表
# ═══════════════════════════════════════════════════════════════

@dataclass
class LangEntry:
    """語言條目"""
    display: str           # UI 顯示名稱
    paddle_ocr: str        # PaddleOCR 語言代碼
    google_code: str       # Google Translate 代碼


# 支援的語言列表
LANGUAGES: dict[str, LangEntry] = {
    "英文 [English]":     LangEntry("英文 [English]",     "en",          "en"),
    "繁體中文 [Traditional Chinese]": LangEntry("繁體中文 [Traditional Chinese]", "chinese_cht",  "zh-TW"),
    "简体中文 [Simplified Chinese]": LangEntry("简体中文 [Simplified Chinese]", "ch",           "zh-CN"),
    "日本語 [Japanese]":     LangEntry("日本語 [Japanese]",     "japan",        "ja"),
    "한국語 [Korean]":     LangEntry("한국語 [Korean]",     "korean",       "ko"),
    "法文 [French]":     LangEntry("法文 [French]",     "french",       "fr"),
    "德文 [German]":     LangEntry("德文 [German]",     "german",       "de"),
    "西班牙文 [Spanish]": LangEntry("西班牙文 [Spanish]", "es",           "es"),
    "葡萄牙文 [Portuguese]": LangEntry("葡萄牙文 [Portuguese]", "pt",           "pt"),
    "義大利文 [Italian]": LangEntry("義大利文 [Italian]", "it",           "it"),
    "俄文 [Russian]":     LangEntry("俄文 [Russian]",     "ru",           "ru"),
    "泰文 [Thai]":     LangEntry("泰文 [Thai]",     "en",           "th"),
    "越南文 [Vietnamese]":   LangEntry("越南文 [Vietnamese]",   "vi",           "vi"),
    "印尼文 [Indonesian]": LangEntry("印尼文 [Indonesian]", "en",           "id"),
    "土耳其文 [Turkish]": LangEntry("土耳其文 [Turkish]", "en",           "tr"),
}

# 方便查詢的輔助函式
def get_lang(display_name: str) -> Optional[LangEntry]:
    return LANGUAGES.get(display_name)

def get_ocr_lang(display_name: str) -> str:
    entry = LANGUAGES.get(display_name)
    return entry.paddle_ocr if entry else "en"

def get_google_code(display_name: str) -> str:
    entry = LANGUAGES.get(display_name)
    return entry.google_code if entry else "en"

def lang_display_names() -> list[str]:
    return list(LANGUAGES.keys())
