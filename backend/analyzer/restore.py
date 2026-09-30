"""分詞構句還原成完整的句子（使用者要求，2026-10-01）。

分詞構句是把「兩個主詞相同的句子」精簡：省略連接詞、省略重複的主詞、動詞改成分詞。
這裡反過來做，讓學生看到原本的句子：
  surviving on penguins, seals, and seaweed
  → and the crew survived on penguins, seals, and seaweed
     ① 省略連接詞 and ② 省略重複的主詞 the crew ③ survived 改成現在分詞 surviving（主動）
動詞變化表 verb_forms.json 由 tools/build_verb_forms.py 從 ECDICT 產生。
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

FORMS_FILE = Path(__file__).with_name("verb_forms.json")
SINGULAR_PRONOUNS = {"he", "she", "it", "this", "that", "everyone", "someone", "nobody"}


@lru_cache(maxsize=1)
def _forms():
    return json.loads(FORMS_FILE.read_text(encoding="utf-8"))


def _clause_verb(tok):
    """往上找到主要句子的動詞"""
    t = tok.head
    while t.pos_ not in ("VERB", "AUX") and t.head.i != t.i:
        t = t.head
    return t


def _subject(verb):
    v = verb
    for _ in range(3):
        subj = next((c for c in v.children if c.dep_ in ("nsubj", "nsubjpass")), None)
        if subj is not None:
            return subj
        if v.dep_ != "conj" or v.head.i == v.i:
            return None
        v = v.head
    return None


def _span_text(toks):
    toks = [t for t in toks if not t.is_punct or t.i != max(x.i for x in toks)]
    if not toks:
        return ""
    doc = toks[0].doc
    return doc[min(t.i for t in toks): max(t.i for t in toks) + 1].text


def _past(verb) -> bool:
    return verb.tag_ == "VBD" or any(c.dep_ in ("aux", "auxpass") and c.lower_ in ("was", "were", "did", "had") for c in verb.children)


def _be(subj, past: bool) -> str:
    word = subj.lower_
    singular = word in SINGULAR_PRONOUNS or word == "i" or subj.tag_ in ("NN", "NNP")
    if past:
        return "was" if singular else "were"
    if word == "i":
        return "am"
    return "is" if singular else "are"


def _conjugate(lemma: str, subj, past: bool) -> str:
    entry = _forms().get(lemma, {})
    if past:
        return entry.get("p", lemma + "ed")
    third = subj.lower_ in SINGULAR_PRONOUNS or subj.tag_ in ("NN", "NNP")
    return entry.get("3", lemma + "s") if third else lemma


def participle_restore(root) -> Optional[dict]:
    """root：分詞構句片段的核心字（surviving、Having finished 的 finished、Seen、Tired）"""
    main = _clause_verb(root)
    subj = _subject(main)
    if subj is None:
        return None
    phrase = sorted((t for t in root.subtree), key=lambda t: t.i)
    having = next((c for c in root.children if c.dep_ == "aux" and c.lower_ == "having"), None)
    being = root if root.lower_ == "being" else next((c for c in root.children if c.lower_ == "being"), None)
    skip = {t.i for t in (having, being) if t is not None} | {root.i}
    rest = _span_text([t for t in phrase if t.i > root.i and t.i not in skip])
    past = _past(main)
    subj_text = _span_text(sorted(subj.subtree, key=lambda t: t.i))
    if subj_text[:1].isupper() and subj.pos_ != "PROPN" and subj.lower_ != "i":
        subj_text = subj_text[0].lower() + subj_text[1:]
    leading = root.i < main.i
    word = root.text if root.pos_ == "PROPN" else root.text.lower()  # 句首的 Tired、Seen 還原到句子中間要改小寫

    if having is not None:
        verb = f"{'had' if past else ('has' if _be(subj, False) == 'is' else 'have')} {word}"
        step3 = f"{verb} 改成 Having {word}（分詞的動作比主要句子早發生）"
        conj = "After"
    elif root.lower_ == "being":
        verb = _be(subj, past)
        step3 = f"{verb} 改成現在分詞 Being（Being 常常可以省略）"
        conj = "Because／When"
    elif root.pos_ == "ADJ" or (being is not None and being is not root):
        verb = f"{_be(subj, past)} {word}"
        step3 = f"{_be(subj, past)} 改成 Being，而且 Being 省略了，只留下 {word}"
        conj = "Because／When"
    elif root.tag_ == "VBN":
        verb = f"{_be(subj, past)} {word}"
        step3 = f"{verb} 去掉 be 動詞，只留過去分詞 {word}（主詞是被動的一方）"
        conj = "When／If"
    elif root.tag_ == "VBG":
        verb = _conjugate(root.lemma_.lower(), subj, past)
        step3 = f"{verb} 改成現在分詞 {word}（主詞是做動作的一方）"
        conj = "Because／When"
    else:
        return None
    if not leading:
        conj = "and"
    clause = " ".join(x for x in (conj, subj_text, verb, rest) if x)
    return {
        "clause": clause,
        "steps": [
            f"省略連接詞 {conj}" + ("（如果怕意思不清楚，也可以保留）" if leading else ""),
            f"省略和主要句子相同的主詞 {subj_text}",
            step3,
        ],
    }
