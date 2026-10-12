"""片語：找出句子裡的片語（動詞片語、慣用語…），清單在 phrases.yaml。

兩種找法：
- head＋parts：用文法分析的依附關係找。parts 要「掛在」head 或前一個 part 底下，
  所以中間夾了受詞也找得到（give it up、turn the light off）。
- seq：照順序連在一起的字，比對原形或原字（rains、rained 都算 rain）。
"""
from functools import lru_cache
from pathlib import Path

import yaml

from . import lexicon as L
from .schema import PhraseHit

PHRASE_FILE = Path(__file__).with_name("phrases.yaml")
KINDS = {"動詞片語", "形容詞片語", "介系詞片語", "副詞片語", "慣用語", "諺語"}
POSSESSIVES = {"my", "your", "his", "her", "its", "our", "their"}
MAX_GAP = 6
FALLBACK_DEPS = {"prt", "prep", "advmod", "dative", "agent"}


@lru_cache(maxsize=1)
def load_phrases() -> tuple[dict, ...]:
    items = yaml.safe_load(PHRASE_FILE.read_text(encoding="utf-8"))
    seen = set()
    for p in items:
        if p["id"] in seen:
            raise ValueError(f"片語代號重複：{p['id']}")
        seen.add(p["id"])
        if p["kind"] not in KINDS:
            raise ValueError(f"片語種類不對：{p['id']} {p['kind']}")
        if ("seq" in p) == ("head" in p):
            raise ValueError(f"片語要有 seq 或 head＋parts 其中一種：{p['id']}")
        if not all(isinstance(x, str) for x in p.get("parts", [])):
            raise ValueError(f"parts 裡的 on／off 要加引號（\"on\"），不然會被讀成 true／false：{p['id']}")
        if "seq" in p:
            p["_seq"] = p["seq"].lower().split()
    return tuple(items)


def by_id(phrase_id: str):
    return next((p for p in load_phrases() if p["id"] == phrase_id), None)


def _word_ok(tok, word: str) -> bool:
    return tok.lower_ == word or tok.lemma_.lower() == word or tok.norm_ == word


# ---------- head＋parts ----------
def _close_enough(prev, tok) -> bool:
    """up、off 這類副詞可以和動詞分開（turn the light off）；
    但後面有受詞的介系詞要緊接在動詞後面（中間最多一個副詞），
    不然 put the book on the table 會被當成 put on（穿上）"""
    if tok.dep_ != "prep" or not any(c.dep_ in ("pobj", "pcomp") for c in tok.children):
        return True
    between = tok.doc[prev.i + 1 : tok.i]
    return len(between) <= 1 and all(t.pos_ == "ADV" for t in between)


def _match_head(sent, entry):
    head_word, parts = entry["head"], entry["parts"]
    verb_phrase = entry.get("kind") == "動詞片語"
    for tok in sent:
        if not _word_ok(tok, head_word):
            continue
        if verb_phrase and tok.pos_ not in ("VERB", "AUX"):
            continue  # put his hand over… 的 hand 是名詞，不是 hand over（交出）
        found = [tok]
        for part in parts:
            anchors = {t.i for t in found}
            nxt = next((c for c in sent[found[-1].i - sent.start + 1:]
                        if c.lower_ == part and c.head.i in anchors and _close_enough(found[-1], c)), None)
            if nxt is None:
                # 分析結果掛錯位置時的備用：緊接在前一個字後面
                after = found[-1].i + 1
                # （只限介系詞、副詞：I used to play 的 to 不算，免得被當成 be used to）
                if after < sent.end and sent.doc[after].lower_ == part and sent.doc[after].dep_ in FALLBACK_DEPS:
                    nxt = sent.doc[after]
            if nxt is None:
                break
            found.append(nxt)
        else:
            if not (verb_phrase and literal_motion(found)):
                yield found


# 方向介系詞：run out of the room、look into the box、come across the street 是字面上的動作
SPATIAL_PARTICLES = {"of", "into", "across", "through", "over", "onto"}


def literal_motion(found) -> bool:
    """動詞片語最後一個字是方向介系詞、後面接地點或容器（room、house、box…）→ 字面意思，不是片語
    （ran out of the room 是「跑出房間」，不是 run out of「用完」）"""
    last = found[-1]
    if last.lower_ in ("out", "off") and last.i + 1 < len(last.doc) and last.nbor().lower_ in ("of", "from"):
        last = last.nbor()  # ran out of the house：片語 run out 後面緊接 of ＋ 地點，也是字面的「跑出」
    elif last.lower_ not in SPATIAL_PARTICLES:
        return False
    pobj = next((c for c in last.children if c.dep_ == "pobj"), None)
    return pobj is not None and pobj.lemma_.lower() in L.PLACE_NOUNS


def phrasal_object(verb):
    """動詞如果是片語清單上的「介系詞動詞」（look after、run out of、look forward to），
    而且最後一個字是後面接名詞的介系詞，回傳 (片語裡除了動詞以外的字, 介系詞的受詞)；不是就回傳 None。
    分析時把「動詞＋介系詞」整組當 Vt、介系詞的受詞當 O（台灣課本「片語動詞當及物動詞」的教法）。"""
    best = None
    for entry in load_phrases():
        if entry.get("kind") != "動詞片語" or entry.get("head") != verb.lemma_.lower():
            continue
        found = [verb]
        for part in entry["parts"]:
            anchors = {t.i for t in found}
            nxt = next((c for c in verb.sent[found[-1].i - verb.sent.start + 1:]
                        if c.lower_ == part and c.head.i in anchors and _close_enough(found[-1], c)), None)
            if nxt is None:
                break
            found.append(nxt)
        else:
            last = found[-1]
            pobj = next((c for c in last.children if c.dep_ in ("pobj", "pcomp")), None)
            passive = any(c.dep_ in ("auxpass", "nsubjpass") for c in verb.children)
            # 被動句的介系詞後面沒有名詞（The baby was looked after.）：介系詞一樣併進動詞，沒有受詞
            if literal_motion(found):
                continue  # ran out of the room：字面的「跑出」，out of the room 是表地點的修飾語
            if last.dep_ == "prep" and (pobj is not None or passive) and (best is None or len(found) > len(best[0]) + 1):
                best = (found[1:], pobj)
    return best


# ---------- seq ----------
def _is_possessive(tokens) -> bool:
    if len(tokens) == 1:
        return tokens[0].lower_ in POSSESSIVES
    return tokens[-1].lower_ in ("'s", "’s", "'") and all(t.is_alpha for t in tokens[:-1])


def _match_from(sent_toks, i, pattern, found):
    if not pattern:
        return found
    word, rest = pattern[0], pattern[1:]
    if word.startswith("(") and word.endswith(")"):
        inner = word[1:-1]
        if i < len(sent_toks) and _word_ok(sent_toks[i], inner):
            got = _match_from(sent_toks, i + 1, rest, found + [sent_toks[i]])
            if got:
                return got
        return _match_from(sent_toks, i, rest, found)
    if word.startswith("[") and word.endswith("]"):
        slot = word[1:-1]
        limit = 3 if slot == "one's" else MAX_GAP
        for n in range(1, limit + 1):
            gap = sent_toks[i : i + n]
            if len(gap) < n or any(t.is_punct for t in gap):
                break
            if slot == "one's" and not _is_possessive(gap):
                continue
            got = _match_from(sent_toks, i + n, rest, found + (gap if slot == "one's" else []))
            if got:
                return got
        return None
    if i < len(sent_toks) and _word_ok(sent_toks[i], word):
        return _match_from(sent_toks, i + 1, rest, found + [sent_toks[i]])
    return None


def _match_seq(sent, entry):
    toks = list(sent)
    for i in range(len(toks)):
        got = _match_from(toks, i, entry["_seq"], [])
        if got:
            yield got


# ---------- 主程式 ----------
def find_phrases(sent) -> list[PhraseHit]:
    """sent：spaCy 的一個句子（Span）。回傳這一句出現的片語，依出現位置排列。"""
    base = sent.start_char
    hits = []
    for entry in load_phrases():
        matcher = _match_seq if "seq" in entry else _match_head
        for toks in matcher(sent, entry):
            hits.append((entry, toks))
    # 同一段字被好幾個片語找到時，留字數多的（look forward to 勝過 look for……）
    hits.sort(key=lambda h: (-len(h[1]), h[1][0].i))
    kept, used = [], set()
    for entry, toks in hits:
        ids = {t.i for t in toks}
        if ids & used or any(e["phrase"] == entry["phrase"] for e, _ in kept):
            continue
        kept.append((entry, toks))
        used |= ids
    kept.sort(key=lambda h: h[1][0].i)
    out = []
    for entry, toks in kept:
        toks = sorted(toks, key=lambda t: t.i)
        out.append(PhraseHit(
            id=entry["id"],
            phrase=entry["phrase"],
            kind=entry["kind"],
            meaning=entry["meaning"],
            literal=entry.get("literal"),
            note=entry.get("note"),
            words=" … ".join(_runs(toks)),
            start=toks[0].idx - base,
        ))
    return out


def _runs(toks):
    """句子裡實際出現的字；中間隔開的用「…」連接，例如 give … up"""
    runs, cur = [], [toks[0]]
    for t in toks[1:]:
        if t.i == cur[-1].i + 1:
            cur.append(t)
        else:
            runs.append(cur)
            cur = [t]
    runs.append(cur)
    return [r[0].doc[r[0].i : r[-1].i + 1].text for r in runs]


def translation_hints(phrase_ids: list[str]) -> str:
    """給翻譯模型的提示：只給慣用語和諺語（模型最容易照字面翻錯的）"""
    lines = []
    for pid in phrase_ids[:10]:
        p = by_id(pid)
        if p and p["kind"] == "慣用語":
            lines.append(f"「{p['phrase']}」是慣用語，意思是「{p['meaning']}」，不是字面上的「{p['literal']}」。")
        elif p and p["kind"] == "諺語":
            lines.append(f"「{p['phrase']}」是諺語，意思是「{p['meaning']}」。")
    return "".join(lines)
