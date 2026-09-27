"""第二道檢查：分析出來的句型，動詞句型字典裡有沒有這種用法。

字典（verb_patterns.yaml）列出每個動詞可以用的句型；分析結果不在字典裡，
代表分析程式可能看錯了（例如 He seems happy 被判成句型四）。
字典裡查不到的動詞不檢查。
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

DICT_PATH = Path(__file__).with_name("verb_patterns.yaml")

# 內部代號（schema.py 的 pattern）→ 字典的公式代號
CODE = {1: "SV", 2: "SVO", 3: "SVC", 4: "SVOO", 5: "SVOC"}
LABEL = {
    "SV": "句型一 S+Vi",
    "SVC": "句型二 S+V+SC",
    "SVO": "句型三 S+Vt+O",
    "SVOC": "句型四 S+Vt+O+OC",
    "SVOO": "句型五 S+Vt+IO+DO",
}


@lru_cache(maxsize=1)
def verb_patterns() -> dict[str, set[str]]:
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    entries = yaml.load(DICT_PATH.read_text(encoding="utf-8"), Loader=loader)
    return {e["verb"]: set(e["patterns"]) for e in entries}


def check(lemma: str, pattern: int) -> Optional[str]:
    """有疑問時回傳原因，沒問題回傳 None"""
    allowed = verb_patterns().get(lemma.lower())
    if not allowed:
        return None
    code = CODE[pattern]
    if code in allowed:
        return None
    usable = "、".join(LABEL[c] for c in LABEL if c in allowed)
    return f"動詞 {lemma} 通常不用在{LABEL[code]}（常見用法：{usable}），這句可能分析錯了。"
