"""查單字：點句子裡的片段時，列出裡面重要單字的音標和中文意思。

字典是 backend/dictionary.json，由 tools/build_dictionary.py 從 ECDICT（MIT 授權）產生。
"""
import json
import re
from functools import lru_cache
from pathlib import Path

DICT_FILE = Path(__file__).with_name("dictionary.json")
MAX_WORDS = 12

# 冠詞、代名詞、be 動詞、助動詞、常見介系詞和連接詞：學生都認識，不列出來
SKIP = set("""
a an the i you he she it we they me him her us them my your his its our their mine yours hers ours theirs
this that these those am is are was were be been being do does did have has had will would can could
shall should may might must not no of to in on at for with by from as and or but so if than then there
here what who whom whose which when where why how all some any each every very too also just only
""".split())


@lru_cache(maxsize=1)
def _data():
    d = json.loads(DICT_FILE.read_text(encoding="utf-8"))
    return d["words"], d["forms"]


def lookup_word(word: str):
    words, forms = _data()
    w = word.lower().strip("'-")
    if w.endswith("'s"):
        w = w[:-2]
    if not w or w in SKIP:
        return None
    if w in words:
        entry = words[w]
        out = {"word": w, "phonetic": entry["p"], "meaning": entry["m"]}
        base = entry.get("b")
        if base in words and base != w:  # saw：鋸子，也是 see 的過去式
            out.update(base=base, base_meaning=words[base]["m"])
        return out
    if w in forms and forms[w] in words and forms[w] != w:  # gave → give
        base = forms[w]
        return {"word": w, "phonetic": words[base]["p"], "meaning": words[base]["m"], "base": base, "form_only": True}
    return None


def lookup_text(text: str) -> list[dict]:
    seen, out = set(), []
    for token in re.findall(r"[A-Za-z][A-Za-z'-]*", text):
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        entry = lookup_word(token)
        if entry:
            out.append(entry)
        if len(out) >= MAX_WORDS:
            break
    return out
