"""拼字檢查：找出可能打錯的字，提醒使用者（使用者要求，2026-10-01）。

例如 lthough → although。打錯字時分析程式常常會看錯整句的結構，與其顯示「這句比較複雜」，
不如直接提醒「是不是打錯字？」。字表由 tools/build_spell_words.py 從 ECDICT 產生：
- spell_known.txt.gz：認得的字（約 37 萬個，收得很寬，罕見字才不會被誤認成打錯）
- spell_rank.json：常用字 → 常用程度排名（挑「最可能想打的字」）
"""
import gzip
import json
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent
LETTERS = "abcdefghijklmnopqrstuvwxyz"
# 字典裡沒有、但大家常寫的字
EXTRA_OK = {"ok", "okay", "covid", "email", "emails", "online", "app", "apps", "selfie", "youtube", "instagram",
            "facebook", "google", "wifi", "smartphone", "smartphones", "iphone", "blog", "vlog", "esports", "tiktok"}
CONTRACTIONS = {"'s", "’s", "n't", "n’t", "'re", "'ll", "'d", "'ve", "'m", "ca", "wo", "sha", "gon", "na", "ta"}


@lru_cache(maxsize=1)
def _known():
    with gzip.open(HERE / "spell_known.txt.gz", "rt", encoding="utf-8") as f:
        return set(f.read().split()) | EXTRA_OK


@lru_cache(maxsize=1)
def _rank():
    return json.loads((HERE / "spell_rank.json").read_text(encoding="utf-8"))


def _edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits if b for c in LETTERS]
    inserts = [a + c + b for a, b in splits for c in LETTERS]
    return set(deletes + transposes + replaces + inserts)


def suggest(word: str):
    """最可能想打的字；找不到就回傳 None"""
    rank = _rank()
    cands = [w for w in _edits1(word) if w in rank]
    if not cands and len(word) >= 5:
        cands = [w for e in _edits1(word) for w in _edits1(e) if rank.get(w, 10 ** 9) <= 20000]
    if not cands:
        return None
    return min(cands, key=lambda w: (rank[w], w))


def find_typos(sent) -> list[dict]:
    """sent：spaCy 的句子。回傳 [{word, start, end, suggestion}]（start／end 是在句子中的字元位置）"""
    known, base, out = _known(), sent.start_char, []
    for tok in sent:
        w = tok.text
        low = w.lower()
        if (not tok.is_alpha or len(w) < 2 or tok.like_url or tok.like_email or low in CONTRACTIONS
                or low in known or tok.lemma_.lower() in known):
            continue
        first = tok.i == sent.start
        if w[0].isupper() and not first:
            continue  # 句子中間大寫開頭的多半是人名、地名（Shackleton）
        if w.isupper():
            continue  # 縮寫（NASA）
        fix = suggest(low)
        if first and w[0].isupper() and (fix is None or _rank().get(fix, 10 ** 9) > 5000):
            continue  # 句首大寫的生字：可能是名字，只有很像常用字時才提醒
        if fix is None and len(w) < 4:
            continue
        if fix is not None and w[0].isupper():
            fix = fix[0].upper() + fix[1:]
        out.append({"word": w, "start": tok.idx - base, "end": tok.idx - base + len(w), "suggestion": fix})
    return out
