"""分析結果與文法重點卡的資料格式（0-5）。

後端產生的分析結果、前端讀取的資料、文法重點卡檔案，都必須符合這裡的定義。
欄位的中文說明見 docs/資料格式.md。
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field, model_validator

# ---------- 分析結果 ----------

Role = Literal[
    "S", "Vt", "Vi", "V", "aux", "O", "IO", "DO", "SC", "OC",
    "RS",       # 真主詞（虛主詞 It 句型）
    "RO",       # 真受詞（虛受詞 it 句型）
    "EF",       # 強調句框架（It is／was … that／who），不算進公式
    "conj",     # 連接詞
    "M",        # 修飾語（含引導詞 There）
    "unknown",  # 未分析
]

CORE_ROLES = {"S", "Vt", "Vi", "V", "O", "IO", "DO", "SC", "OC"}  # 算進公式的角色

# 句型的「內部代號」→「顯示編號」（採賴世雄／常春藤的編號，2026-09-27 使用者決定）
#   內部代號：1 S+Vi、2 S+Vt+O、3 S+Vi+SC、4 S+Vt+IO+DO、5 S+Vt+O+OC（程式與題庫資料使用）
#   顯示編號：句型一 S+Vi、句型二 S+Vi+SC、句型三 S+Vt+O、句型四 S+Vt+O+OC、句型五 S+Vt+IO+DO
PATTERN_DISPLAY = {1: 1, 2: 3, 3: 2, 4: 5, 5: 4}


class Span(BaseModel):
    """句子中的一段文字，start／end 是字元位置（end 不含）"""

    start: int
    end: int
    text: str


class Restore(BaseModel):
    clause: str = Field(description="還原後的完整子句，例如 and the crew survived on penguins")
    steps: list[str] = Field(default_factory=list, description="從完整句子變成分詞構句的步驟")


class Chunk(BaseModel):
    id: int
    text: str
    start: int = Field(description="在句子中的起始字元位置；省略的主詞 (You) 為插入位置")
    end: int
    role: Role
    implicit: bool = Field(False, description="句子裡看不到的字，例如祈使句的 (You)")
    suffix: str = Field("", description="畫面上接在文字後面的補充，例如 Let's 的 's 顯示成 's（us）")
    restore: Optional[Restore] = Field(None, description="分詞構句還原成完整句子（點開說明時顯示）")
    function: Optional[str] = Field(None, description="修飾語的功能，例如「副詞・表地點」「形容詞・修飾」「引導詞」")
    modifies: Optional[Span] = Field(None, description="形容詞修飾的那個字")
    heads: list[Span] = Field(default_factory=list, description="核心字（粗體）")
    structure: Optional[str] = Field(None, description="結構，例如「介系詞片語」；只出現在說明裡")
    note: str = Field("", description="點片語時顯示的說明")
    clause: int = Field(0, description="屬於第幾個主要子句（對等句才會有 1 以上）")
    inner: list["Chunk"] = Field(default_factory=list, description="可以展開的子句內部拆解")

    @model_validator(mode="after")
    def _check(self):
        if self.role == "M" and not self.function:
            raise ValueError(f"修飾語必須有 function：{self.text}")
        if self.role != "M" and self.function:
            raise ValueError(f"只有修飾語可以有 function：{self.text}")
        if self.function == "形容詞・修飾" and not self.modifies:
            raise ValueError(f"形容詞修飾語必須標出修飾對象：{self.text}")
        return self


class Clause(BaseModel):
    """一個主要子句的句型"""

    index: int
    pattern: Literal[1, 2, 3, 4, 5]
    passive: bool = False
    formula: str = Field(description="例如 S + Vt + O；被動為 S + be + p.p. …")
    verb: Optional[str] = Field(None, description="主要動詞的原形")
    doubt: Optional[str] = Field(None, description="動詞句型字典檢查不通過時的原因（verb_check.py）")
    elliptic: bool = Field(False, description="省略句：只有助動詞，後面的動詞省略了（I can't.），沒有句型")

    @computed_field
    @property
    def label(self) -> str:
        if self.elliptic:
            return f"省略句：{self.formula}"
        num = "一二三四五"[PATTERN_DISPLAY[self.pattern] - 1]
        return f"句型{num}{'（被動語態）' if self.passive else ''}：{self.formula}"


class CardRef(BaseModel):
    """這一句要顯示的文法重點卡"""

    id: str
    vars: dict[str, str] = Field(default_factory=dict, description="填進卡片簡短說明的變數，例如 {noun: kids}")


class PhraseHit(BaseModel):
    """這一句出現的片語（清單在 analyzer/phrases.yaml）"""

    id: str
    phrase: str = Field(description="字典形式，例如 give up、rain cats and dogs")
    kind: Literal["動詞片語", "形容詞片語", "介系詞片語", "副詞片語", "慣用語", "諺語"]
    meaning: str
    literal: Optional[str] = Field(None, description="慣用語的字面意思")
    note: Optional[str] = None
    words: str = Field(description="句子裡實際出現的字，隔開的用「…」連接，例如 gave … up")
    start: int = Field(description="第一個字在句子中的字元位置")


class SentenceResult(BaseModel):
    text: str
    status: Literal["ok", "partial", "failed"]
    message: Optional[str] = Field(None, description="partial／failed 時顯示給使用者的提示")
    kind: Literal["simple", "compound"] = "simple"
    clauses: list[Clause]
    chunks: list[Chunk]
    cards: list[CardRef] = Field(default_factory=list)
    phrases: list[PhraseHit] = Field(default_factory=list)
    translation: Optional[str] = Field(None, description="分析時不翻譯；網頁另外呼叫 /api/translate 補上")

    @computed_field
    @property
    def header(self) -> str:
        return "　＆　".join(c.label for c in self.clauses)

    @model_validator(mode="after")
    def _check(self):
        for c in self.chunks:
            for part in [c, *c.inner, *c.heads, *([c.modifies] if c.modifies else [])]:
                if getattr(part, "implicit", False):
                    continue
                if self.text[part.start : part.end] != part.text:
                    raise ValueError(f"字元位置和文字對不上：{part.text!r}")
        if self.kind == "compound" and len(self.clauses) < 2:
            raise ValueError("對等句至少要有兩個子句")
        return self


class AnalysisResult(BaseModel):
    version: Literal["1"] = "1"
    input: str
    sentences: list[SentenceResult]


# ---------- 文法重點卡 ----------


class Example(BaseModel):
    en: str
    zh: str = ""
    mark: Literal["ok", "no", "none"] = "none"


class Block(BaseModel):
    type: Literal["formula", "tip", "warn", "info", "heading", "list", "examples"]
    text: str = ""
    items: list[str] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)


class Card(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    brief: str = Field(description="簡短說明，可以用 {變數}，例如「動詞單複數要看 of 後面的 {noun}」")
    trigger: str = Field(description="什麼情況要顯示這張卡（給人看的說明，實際判斷寫在程式裡）")
    blocks: list[Block]
    see_also: list[str] = Field(default_factory=list)
