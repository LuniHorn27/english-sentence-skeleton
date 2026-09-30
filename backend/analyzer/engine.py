"""分析引擎：英文句子 → 分析結果（符合 schema.py 的格式）。

流程
1. spaCy（大型模型）分析句子，得到每個字的詞性和「依附關係」。
2. 找出每個子句的主要動詞，替動詞底下的成分分配角色（S、O、SC…、修飾語）。
3. 名詞後面的介系詞片語、形容詞子句另外切成「形容詞・修飾 X」。
4. 每個字歸給離它最近、有角色的祖先 → 組成片段。
5. 推出句型、核心字、文法重點卡、說明文字。

規則依據：docs/標籤規則.md。沒有把握的部分標成 unknown（未分析）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from . import lexicon as L
from .notes import chunk_note
from .phrases import find_phrases, phrasal_object
from .schema import CardRef, Chunk, Clause, SentenceResult, Span
from .verb_check import check as verb_check

NOMINAL = {"S", "O", "IO", "DO", "SC", "OC", "RS", "RO"}
VERB_ROLE = "VERB"  # 動詞種類（Vt／Vi／V）等句型決定後再填

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        import warnings

        import spacy

        warnings.filterwarnings("ignore")
        _nlp = spacy.load("en_core_web_trf")
        # 名詞後面的 'll 也要拆開（this rain'll last → rain ＋ 'll）
        from spacy.util import compile_suffix_regex

        suffixes = list(_nlp.Defaults.suffixes) + [r"(?<=[A-Za-z])['’]ll$"]
        _nlp.tokenizer.suffix_search = compile_suffix_regex(suffixes).search
    return _nlp


@dataclass
class Spec:
    """一個片段的根（片段由這個字和它底下的字組成）"""

    role: str
    function: Optional[str] = None
    modifies: object = None  # spaCy Token
    clause: int = 0
    kind: str = ""  # 補充分類：npadv（名詞片語當副詞）、relcl、advcl…
    inner_verb: object = None  # 可展開的子句的動詞


@dataclass
class ClauseInfo:
    verb: object
    index: int
    passive: bool = False
    existential: bool = False
    imperative: bool = False
    question: bool = False
    pattern: int = 0
    flags: set = field(default_factory=set)
    verb_token: object = None  # 真正要標 Vt／Vi／V 的字
    elliptic: bool = False  # 省略句：I can't.、I will.（只有助動詞）
    lets: bool = False  # Let's ＋ 原形動詞（提議）：Let 標 aux.，'s（＝us）標 S


# ---------- 修飾語功能 ----------
def adverb_function(tok) -> str:
    """動詞底下的修飾語 → 副詞・表…"""
    lemma = tok.lemma_.lower()
    dep = tok.dep_
    if dep == "agent":
        return "副詞・表執行者"
    if dep in ("prep",) and lemma == "than":
        return "副詞・表比較"  # taller than her sister
    head = tok.head.lemma_.lower()
    if dep == "prep" and (head, lemma) == ("prefer", "to"):
        return "副詞・表比較"  # prefer tea to coffee
    if dep == "prep" and lemma == "for" and head in ("thank", "apologize", "blame", "praise", "punish", "forgive"):
        return "副詞・表原因"  # Thank you for your help.
    if dep == "prep" and lemma == "of" and any(c.lower_ == "instead" for c in tok.children):
        return "副詞・表方式"  # Instead of taking the bus（代替）
    if dep == "prep" and lemma == "because":
        return "副詞・表原因"  # because of the rain
    if dep == "prep" and any(c.dep_ == "pobj" and c.lemma_.lower() == "spite" for c in tok.children):
        return "副詞・表讓步"  # in spite of the rain
    if dep == "prep" and lemma == "of":
        return "副詞・表對象"  # reminded me of my mother、think of you
    if dep == "prep" and lemma == "with":
        pobj = next((c for c in tok.children if c.dep_ == "pobj"), None)
        small_clause = any(c.dep_ == "pcomp" and any(g.dep_ == "nsubj" for g in c.children) for c in tok.children)
        if small_clause or pobj is not None and any(
                c.i > pobj.i and (c.tag_ in ("VBN", "VBG") or c.dep_ in ("acl", "amod") and c.pos_ in ("ADJ", "VERB"))
                for c in pobj.children):
            return "副詞・表狀況"  # 附帶狀況：with his eyes closed、with the door open
    if dep == "advmod" and " ".join(t.lower_ for t in sorted(tok.subtree, key=lambda t: t.i)[:2]) == "no matter":
        return "副詞子句・表讓步"  # No matter what happens, …
    if dep in ("prep",):
        obj = next((c for c in tok.children if c.dep_ == "pobj"), None)
        olemma = obj.lemma_.lower() if obj is not None else ""
        if lemma in ("at", "to") and obj is not None and (obj.pos_ == "PRON" or olemma in L.PERSON_NOUNS or obj.ent_type_ == "PERSON"):
            return "副詞・表對象"  # shout at me、talk to the teacher
        if any(c.dep_ == "npadvmod" and c.lemma_ == "way" for c in tok.children):
            return "副詞・表路程"  # all the way to school
        if lemma in ("in", "from") and olemma in ("opinion", "view", "perspective", "experience"):
            return "副詞・表語氣"  # In my opinion,…（依我看）
        if lemma in L.TIME_PREPS:
            return "副詞・表時間"
        if obj is not None and (olemma in L.TIME_NOUNS or obj.ent_type_ in ("DATE", "TIME")):
            return "副詞・表時間"
        if (tok.head.lemma_.lower(), lemma) in L.VERB_PREP_OBJECT:
            return "副詞・表對象"  # look at the photo：介系詞後面是動作的對象
        if olemma in L.CONDITION_NOUNS:
            return "副詞・表狀況"
        if lemma == "for":
            return "副詞・表目的"
        if lemma == "with":
            if obj is not None and (obj.pos_ == "PRON" or olemma in L.PERSON_NOUNS or obj.ent_type_ == "PERSON"):
                return "副詞・表伴隨"
            return "副詞・表方式"
        if lemma in ("by", "like"):
            return "副詞・表方式"
        if lemma in L.PLACE_PREPS:
            return "副詞・表地點"
        return "副詞・表方式"
    if dep == "npadvmod":
        if lemma == "way":
            return "副詞・表路程"
        if lemma in L.TIME_NOUNS or tok.ent_type_ in ("DATE", "TIME"):
            return "副詞・表時間"
        return "副詞・表方式"
    # advmod、intj 等
    if lemma in ("hardly", "scarcely", "barely") or (lemma == "little" and tok.i == tok.sent.start):
        return "副詞・表否定"  # Hardly had he arrived…（幾乎不）
    if lemma == "how" or (tok.tag_ in ("JJ", "RB") and any(c.lower_ == "how" for c in tok.children)):
        nxt = tok if lemma != "how" else None
        word = nxt.lower_ if nxt is not None else ""
        if word in ("long", "often", "soon", "late", "early"):
            return "副詞・表時間"  # How long have you lived here?
        if word == "far":
            return "副詞・表路程"
    if tok.tag_ == "WRB" or lemma in ("where", "when", "why"):  # 疑問詞 Where did you…?、Why is…?
        return {"where": "副詞・表地點", "when": "副詞・表時間", "why": "副詞・表原因"}.get(lemma, "副詞・表方式")
    if lemma in L.TONE_ADVERBS or lemma == "please":
        return "副詞・表語氣"
    if lemma in L.TIME_ADVERBS:
        return "副詞・表時間"
    if lemma in L.PLACE_ADVERBS:
        return "副詞・表地點"
    return "副詞・表方式"


def clause_opener(tok):
    """副詞子句的連接詞：mark（because、if…）或句首的 when／where（WRB）"""
    mark = next((c for c in tok.children if c.dep_ == "mark"), None)
    if mark is None:
        first = min(tok.subtree, key=lambda t: t.i)
        if first.tag_ == "WRB" and first.head.i == tok.i:
            mark = first
    return mark


def opener_tokens(tok):
    """副詞子句開頭的連接詞（可以是多個字：as soon as、even though…），回傳 (字的清單, 功能)"""
    words = [t for t in sorted(tok.subtree, key=lambda t: t.i) if not t.is_punct][:3]
    for n in (3, 2):
        phrase = " ".join(t.lower_ for t in words[:n])
        if len(words) >= n and phrase in L.MULTI_SUBORDINATORS:
            return words[:n], L.MULTI_SUBORDINATORS[phrase]
    mark = clause_opener(tok)
    if mark is not None:
        return [mark], L.SUBORDINATORS.get(mark.lower_)
    return [], None


def adjective_pp_function(adj, prep):
    """形容詞後面的介系詞片語：固定搭配是「表對象」，時間、場所才標時間、地點"""
    pair = (adj.lower_, prep.lower_)
    if prep.lower_ == "than":
        return "副詞・表比較"  # taller than her sister、more interesting than that one
    if prep.lower_ == "as" and any(c.lower_ == "as" and c.i < adj.i for c in adj.children):
        return "副詞・表比較"  # as tall as her brother
    if pair in L.ADJ_PREPS or pair in L.STATIVE_PAIRS:
        return "副詞・表對象"
    obj = next((c for c in prep.children if c.dep_ == "pobj"), None)
    olemma = obj.lemma_.lower() if obj is not None else ""
    if prep.lower_ in L.TIME_PREPS or olemma in L.TIME_NOUNS:
        return "副詞・表時間"
    if olemma in L.PLACE_NOUNS:
        return "副詞・表地點"
    return "副詞・表對象"


def multi_opener_clause(adv):
    """As soon as I got home：分析程式把 as soon 當副詞、子句掛在它底下。回傳 (子句的動詞, 功能)"""
    words = [t for t in sorted(adv.subtree, key=lambda t: t.i) if not t.is_punct][:3]
    clause = next((t for t in adv.subtree if t.dep_ in ("advcl", "ccomp") and t.pos_ in ("VERB", "AUX")), None)
    if clause is None:
        return None
    for n in (3, 2):
        phrase = " ".join(t.lower_ for t in words[:n])
        if len(words) >= n and phrase in L.MULTI_SUBORDINATORS:
            return clause, L.MULTI_SUBORDINATORS[phrase]
    return None


def has_perfect(verb):
    return any(c.dep_ == "aux" and c.lemma_ == "have" for c in verb.children)


AS_MANNER_VERBS = {"do", "say", "tell", "show", "expect", "instruct", "please", "wish", "like", "want", "plan", "teach", "suggest", "direct"}
AS_CHANGE_VERBS = {"grow", "get", "increase", "decrease", "advance", "develop", "change", "rise", "fall", "age", "improve",
                   "progress", "go", "pass", "spread", "expand", "deepen", "become", "shrink", "mature"}
AS_STATIVE_VERBS = {"be", "have", "know", "need", "want", "seem", "like", "understand", "believe", "own", "live", "feel"}


def as_function(tok) -> str:
    """as 帶的副詞子句（使用者整理的五種意思，2026-10-01）：
    時間（當…時）、原因（因為）、比例（隨著）、方式（依照、如同）、讓步（Tired as Mom was，另外處理）。
    分析程式看不懂語意，用線索猜，猜不到就維持表時間；說明裡會教學生用換字法自己判斷。"""
    kids = list(tok.children)
    progressive = tok.tag_ == "VBG" and any(c.dep_ == "aux" and c.lemma_ == "be" for c in kids)
    if progressive:
        return "表時間"  # I saw Linda as I was getting off the bus.
    if tok.lemma_.lower() in AS_MANNER_VERBS and not any(c.dep_ in ("dobj", "ccomp", "xcomp") for c in kids):
        return "表方式"  # Do as I say.、as the Romans do
    main = tok.head
    comparative = any(t.tag_ in ("JJR", "RBR") for t in list(tok.subtree) + [c for c in main.children if c.dep_ in ("acomp", "advmod", "oprd", "attr")])
    if tok.lemma_.lower() in AS_CHANGE_VERBS or comparative:
        return "表比例"  # As technology advances, our lives get more convenient.、As she grew older…
    negative = any(c.dep_ == "neg" or c.tag_ == "MD" for c in kids)
    if tok.lemma_.lower() in AS_STATIVE_VERBS or negative:
        return "表原因"  # As the weather was bad, …、As he is my friend, …
    return "表時間"


def advcl_function(tok) -> Optional[str]:
    opener, f = opener_tokens(tok)
    if len(opener) == 1 and opener[0].lower_ == "as":
        f = as_function(tok)
    no_subject = not any(c.dep_ in ("nsubj", "nsubjpass", "expl") for c in tok.children)
    if opener and opener[0].lower_ == "since" and len(opener) == 1:
        f = "表時間" if has_perfect(tok.head) or has_perfect(tok) else "表原因"
    if opener:
        if not f:
            return None
        # 沒有主詞的（While walking to class）是縮減後的副詞片語，不是完整的子句（Azar 18-1）
        infinitive = any(c.dep_ == "aux" and c.lower_ == "to" for c in tok.children)  # so as to pass the exam
        return f"副詞・{f}" if no_subject and (tok.tag_ in ("VBG", "VBN") or infinitive) else f"副詞子句・{f}"
    first = min((t for t in tok.subtree if not t.is_punct), key=lambda t: t.i)
    if first.lower_ in ("had", "were", "should") and (first is tok or first.dep_ in ("aux", "auxpass")) \
            and any(c.dep_ in ("nsubj", "nsubjpass") and c.i > first.i for c in tok.children):
        return "副詞子句・表條件"  # 省略 if 的假設語氣：Had I known…、Were I you…、Should you need help…
    if any(c.dep_ == "aux" and c.lower_ == "to" for c in tok.children):
        return "副詞・表目的"  # 不定詞表目的：to buy milk
    if no_subject and tok.tag_ in ("VBG", "VBN"):
        return "副詞・分詞構句"  # Walking to school, I saw a cat.
    return None


# ---------- 子句 ----------
NOT_GERUNDS = {"morning", "evening", "thing", "nothing", "something", "anything", "everything",
               "king", "ring", "spring", "building", "ceiling", "wedding", "string", "wing", "sibling", "pudding"}


def is_gerund(tok):
    """Swimming is fun：分析程式有時把動名詞標成名詞"""
    if tok.tag_ == "VBG":
        return True
    return (tok.pos_ == "NOUN" and tok.lower_.endswith("ing") and len(tok.text) > 5
            and tok.lower_ not in NOT_GERUNDS and not any(c.dep_ in ("det", "poss") for c in tok.children))


def is_real_aux(tok):
    return tok.lemma_.lower() in L.AUX_LEMMAS or tok.lower_ in ("n't", "not", "'s", "'re", "'m", "'ve", "'ll", "'d", "ca", "wo")


def assign_clause(v, roots: dict, index: int, sent, shared_subject=False) -> ClauseInfo:
    info = ClauseInfo(verb=v, index=index, verb_token=v)
    children = [c for c in v.children]
    deps = {c.dep_ for c in children}
    info.passive = bool(deps & {"nsubjpass", "auxpass", "csubjpass"})
    if info.passive and v.lemma_ in ("become", "be") and "agent" not in deps:
        info.passive = False  # It's become popular.、It's been a long time：'s 是 has，不是被動
    info.existential = "expl" in deps and v.lemma_ == "be"

    # Let's go to the park.（使用者決定 2026-09-29）：祈使句，Let 表示提議、標 aux.（不算進公式），
    # 's（＝us）是主詞 S，句型看後面的動詞（go＝Vi → 句型一）。Let me／Let him 照使役動詞（句型四）
    after = sent.doc[v.i + 1] if v.i + 1 < len(sent.doc) else None
    if v.lemma_ == "let" and after is not None and after.lower_ in ("'s", "’s") and not shared_subject:
        main = next((c for c in children if c.dep_ in ("ccomp", "xcomp") and c.pos_ in ("VERB", "AUX")), None)
        if main is None and after.head.pos_ in ("VERB", "AUX") and after.head.i > v.i:
            main = after.head
        if main is not None:
            inner = assign_clause(main, roots, index, sent, shared_subject=True)
            roots[v.i] = Spec("aux", clause=index, kind="lets")
            roots[after.i] = Spec("S", clause=index, kind="lets_us")  # 's＝us，是主詞（使用者決定）
            for c in main.children:
                if c.dep_ == "neg" and c.i == after.i + 1:
                    roots[c.i] = Spec("aux", clause=index, kind="neg")  # Let's not argue.
            inner.lets = True
            inner.flags.add("imperative")
            inner.pattern = clause_pattern(roots, index, inner)
            return inner

    # 省略句：I can't.、Yes, I will.、I did.（只有助動詞，後面的動詞省略了）；So do I.、Neither can she.
    agree = sent[0].lower_ in ("so", "neither", "nor") and (v.lemma_ in ("do", "be", "have") or v.tag_ == "MD")
    if (v.tag_ == "MD" or (v.lemma_ == "do" and v.pos_ == "AUX") or agree) and not any(
            c.dep_ in ("xcomp", "ccomp", "acomp", "attr", "dobj", "oprd", "dative", "advcl", "prep") for c in children):
        info.elliptic = True
        info.pattern = 1
        roots[v.i] = Spec("aux", clause=index)
        for c in children:
            if c.dep_ in ("nsubj", "nsubjpass"):
                roots[c.i] = Spec("S", clause=index)
            elif c.dep_ == "neg" and c.lower_ in ("neither", "nor"):
                roots[c.i] = Spec("M", function="副詞・表否定", clause=index)  # Neither can she.（她也不行）
            elif c.dep_ == "neg":
                roots[c.i] = Spec("aux", clause=index, kind="neg")
            elif c.dep_ == "advmod" and c.lower_ == "so" and c.i == sent.start:
                roots[c.i] = Spec("M", function="副詞・表語氣", clause=index)  # So do I.（我也是）
            elif c.dep_ in ("advmod", "npadvmod", "intj"):
                roots[c.i] = Spec("M", function=adverb_function(c), clause=index)
        return info

    # 分析程式把 enjoy 之類的主要動詞誤判成助動詞：enjoy 才是動詞，後面的 playing 是受詞
    fake = [c for c in children if c.dep_ == "aux" and not is_real_aux(c) and c.pos_ in ("VERB", "AUX")]
    if fake:
        main = fake[0]
        roots[main.i] = Spec(VERB_ROLE, clause=index)
        roots[v.i] = Spec("O", clause=index)
        info.verb_token = main
        for c in children + list(main.children):
            if c.dep_ in ("nsubj", "nsubjpass"):
                roots[c.i] = Spec("S", clause=index)
            elif c.dep_ in ("aux", "auxpass", "neg") and c is not main:
                roots[c.i] = Spec("aux", clause=index)
        info.pattern = 2
        return info

    # have to／has to／had to ＋ 原形動詞：have to 當助動詞，後面的動詞才是主要動詞（It has to be done.）
    # be going to ＋ 原形動詞（未來式）也一樣：are going to 整組當助動詞（We are going to visit…）
    have_to = next((c for c in children if c.dep_ == "xcomp" and c.pos_ in ("VERB", "AUX") and any(
        g.dep_ == "aux" and g.lower_ == "to" and g.i == v.i + 1 for g in c.children)), None)
    going_to = v.lower_ == "going" and any(c.dep_ == "aux" and c.lemma_ == "be" for c in children)
    used_to = v.lower_ in ("used", "use") and v.lemma_ == "use"  # I used to play…（過去的習慣）
    supposed_to = v.lower_ == "supposed" and any(c.dep_ in ("aux", "auxpass") and c.lemma_ == "be" for c in children)  # 應該
    # be able to ＋ 原形動詞（能夠）：able 掛在 be 底下，後面的動詞掛在 able 底下
    able = next((c for c in children if c.dep_ == "acomp" and c.lower_ == "able"), None) if v.lemma_ == "be" else None
    able_to = next((g for g in able.children if g.dep_ == "xcomp" and g.pos_ in ("VERB", "AUX") and any(
        x.dep_ == "aux" and x.lower_ == "to" and x.i == able.i + 1 for x in g.children)), None) if able is not None else None
    if able_to is not None:
        roots[v.i] = Spec("aux", clause=index)
        roots[able.i] = Spec("aux", clause=index)
        inner = assign_clause(able_to, roots, index, sent, shared_subject=True)
        for c in children:
            if c is able or c.dep_ == "punct":
                continue
            if c.dep_ in ("nsubj", "nsubjpass", "csubj"):
                roots[c.i] = Spec("S", clause=index)
            elif c.dep_ in ("aux", "auxpass") or (c.dep_ == "neg" and c.lower_ in ("not", "n't")):
                roots[c.i] = Spec("aux", clause=index, kind="neg" if c.dep_ == "neg" else "")
            elif c.dep_ in ("advmod", "npadvmod", "prep", "neg"):
                roots[c.i] = Spec("M", function=adverb_function(c), clause=index)
        for t in able_to.children:
            if t.dep_ == "aux" and t.lower_ == "to":
                roots[t.i] = Spec("aux", clause=index)
        inner.pattern = clause_pattern(roots, index, inner)
        return inner
    if (v.lemma_ == "have" or going_to or used_to or supposed_to) and have_to is not None and not any(c.dep_ in ("dobj", "dative") for c in children):
        roots[v.i] = Spec("aux", clause=index)
        inner = assign_clause(have_to, roots, index, sent, shared_subject=True)
        for c in children:
            if c is have_to or c.dep_ == "punct":
                continue
            if c.dep_ in ("nsubj", "nsubjpass", "csubj"):
                roots[c.i] = Spec("S", clause=index)
            elif c.dep_ in ("aux", "auxpass") or (c.dep_ == "neg" and c.i < v.i):
                roots[c.i] = Spec("aux", clause=index, kind="neg" if c.dep_ == "neg" else "")
            elif c.dep_ in ("advmod", "npadvmod", "prep", "neg"):
                roots[c.i] = Spec("M", function=adverb_function(c), clause=index)
        for t in have_to.children:
            if t.dep_ == "aux" and t.lower_ == "to":
                roots[t.i] = Spec("aux", clause=index)
        expl = next((c for c in children if c.dep_ == "expl"), None)
        if expl is not None and have_to.lemma_ == "be":
            # There used to be a tree here.：There 標引導詞，a tree 是真正的主詞，be 是 Vi
            roots[expl.i] = Spec("M", function="引導詞", clause=index)
            roots[have_to.i] = Spec("Vi", clause=index)
            for g in have_to.children:
                if g.dep_ == "attr":
                    roots[g.i] = Spec("S", clause=index, kind="real_subject")
                elif g.dep_ == "prep":
                    roots[g.i] = Spec("M", function=adverb_function(g), clause=index)
            inner.existential = True
        inner.pattern = clause_pattern(roots, index, inner)
        inner.question = any(c.dep_ == "aux" and c.i < v.i for c in children) and any(
            c.dep_ == "nsubj" and c.i < v.i and any(a.dep_ == "aux" and a.i < c.i for a in children) for c in children) \
            and (sent.text.rstrip().endswith("?") or sent[0].pos_ == "AUX" or sent[0].tag_ == "MD")
        return inner

    be_aux = next((c for c in children if c.dep_ == "auxpass" and c.lemma_ == "be"), None)
    stative_pair = any(c.dep_ == "prep" and (v.lower_, c.lower_) in L.STATIVE_PAIRS for c in children)
    modal_before = any(c.dep_ == "aux" and (c.tag_ == "MD" or c.lower_ == "to") for c in children)
    if info.passive and be_aux is not None and (v.lower_ in L.ADJ_PARTICIPLES or stative_pair) and "agent" not in deps \
            and not (modal_before and not stative_pair):  # It has to be done、must be done 是被動
        # 其實是形容詞：The restaurant is crowded（句型二），不是被動語態
        info.passive = False
        roots[be_aux.i] = Spec(VERB_ROLE, clause=index)
        roots[v.i] = Spec("SC", clause=index)
        info.verb_token = be_aux
        for c in children:
            if c.i == be_aux.i or c.dep_ == "punct":
                continue
            if c.dep_ in ("nsubjpass", "nsubj"):
                roots[c.i] = Spec("S", clause=index)
            elif c.dep_ in ("aux", "auxpass", "neg"):
                roots[c.i] = Spec("aux", clause=index)
            elif c.dep_ in ("advmod", "npadvmod") and c.i < v.i:
                roots[c.i] = Spec("M", function=adverb_function(c), clause=index)
            elif c.dep_ == "prep" and (v.lower_, c.lower_) in L.STATIVE_PAIRS:
                roots[c.i] = Spec("M", function="副詞・表對象", clause=index)  # interested in art
            elif c.dep_ in ("prep", "advmod", "npadvmod") and adverb_function(c) in ("副詞・表時間", "副詞・表地點"):
                roots[c.i] = Spec("M", function=adverb_function(c), clause=index)
            elif c.dep_ == "prep" and c.i > v.i:
                roots[c.i] = Spec("M", function="副詞・表對象", clause=index)  # interested in art
        info.pattern = 3
        return info

    roots[v.i] = Spec(VERB_ROLE, clause=index)
    subjects = [c for c in children if c.dep_ in ("nsubj", "nsubjpass", "csubj", "csubjpass")]
    auxes = [c for c in children if c.dep_ in ("aux", "auxpass")]
    info.question = bool(subjects) and (
        any(a.i < subjects[0].i for a in auxes) or (v.i < subjects[0].i and v.lemma_ == "be" and not info.existential)
    ) and (sent.text.rstrip().endswith("?") or sent[0].pos_ == "AUX" or sent[0].tag_ == "MD")  # Never have I…、Only then did I… 是倒裝
    info.imperative = not shared_subject and not subjects and v.tag_ == "VB" and not info.existential and not any(
        a.lower_ in ("to",) for a in auxes
    )

    # 片語動詞：look after [her brother]、ran out of [milk] → 動詞＋介系詞整組當 Vt，介系詞的受詞當 O
    phrasal = None
    if v.pos_ == "VERB" and not any(c.dep_ in ("dobj", "dative") for c in children):
        phrasal = phrasal_object(v)
    phrasal_parts = {t.i for t in phrasal[0]} if phrasal else set()
    if phrasal and phrasal[1] is not None:
        roots[phrasal[1].i] = Spec("O", clause=index)
        info.flags.add("phrasal_verb")

    # 受詞候選（依位置排序），處理雙受詞
    objects = [c for c in children if c.dep_ in ("dobj", "dative")]
    nominal_after = sorted(
        [c for c in children if c.i > v.i and c.dep_ in ("dobj", "dative", "npadvmod", "attr", "oprd")
         and c.pos_ in ("NOUN", "PROPN", "PRON", "NUM")],
        key=lambda t: t.i,
    )
    dative_fix = None
    if (
        v.lemma_.lower() in L.DATIVE_VERBS
        and len(nominal_after) >= 2
        and not any(c.dep_ == "dative" for c in children)
        and nominal_after[0].dep_ in ("dobj", "npadvmod")
        and nominal_after[1].dep_ in ("dobj", "npadvmod", "attr", "oprd")
        and (nominal_after[1].lemma_.lower() not in L.TIME_NOUNS
             or (v.lemma_ in ("take", "cost") and nominal_after[0].pos_ in ("PRON", "PROPN")))  # took us a long time
    ):
        dative_fix = (nominal_after[0], nominal_after[1])

    if dative_fix is None and v.lemma_.lower() in L.DATIVE_VERBS:
        # 分析程式有時把 IO 看成 DO 的主詞：made [our whole family] [a cake]
        for c in children:
            g = next((x for x in c.children if x.dep_ == "nsubj"), None) if c.dep_ == "dobj" else None
            if g is not None and c.pos_ == "NOUN" and g.pos_ in ("NOUN", "PRON", "PROPN") and g.i < c.i:
                dative_fix = (g, c)

    that_clause = next((c for c in children if c.dep_ == "ccomp" and c.i > v.i and (
        clause_opener(c) is not None or any(g.dep_ in ("nsubj", "nsubjpass") for g in c.children))), None)
    dobj = next((c for c in children if c.dep_ == "dobj"), None)
    if dative_fix is None and dobj is not None and that_clause is not None and v.lemma_.lower() in L.DATIVE_VERBS | {"remind", "inform", "promise", "teach", "warn", "assure"}:
        dative_fix = (dobj, that_clause)  # told [everyone] [that the company would move]

    has_dative = any(c.dep_ == "dative" and c.pos_ != "ADP" for c in children) or dative_fix is not None
    has_obj = bool(objects) or dative_fix is not None or (phrasal is not None and phrasal[1] is not None)

    for c in children:
        d = c.dep_
        if c.i in phrasal_parts:
            continue  # 片語動詞的介系詞、副詞留在動詞裡（looks after、ran out of）
        if dative_fix and c is dative_fix[0]:
            roots[c.i] = Spec("IO", clause=index)
        elif dative_fix and c is dative_fix[1]:
            roots[c.i] = Spec("DO", clause=index)
        elif d in ("nsubj", "nsubjpass", "csubj", "csubjpass"):
            roots[c.i] = Spec("S", clause=index)
            if is_gerund(c):
                info.flags.add("gerund_subject")
        elif d == "expl":
            roots[c.i] = Spec("M", function="引導詞", clause=index)
        elif d in ("aux", "auxpass"):
            roots[c.i] = Spec("aux", clause=index)
        elif d == "advmod" and c.lower_ in ("better", "rather") and c.i < v.i and c.i > 0 \
                and sent.doc[c.i - 1].lower_ in ("had", "'d", "would"):
            roots[c.i] = Spec("aux", clause=index)  # had better、would rather 整組當助動詞
        elif d == "neg":
            prev = sent.doc[c.i - 1] if c.i > 0 else None
            if prev is not None and prev.i in roots and roots[prev.i].role == "aux" and c.lower_ in ("not", "n't"):
                roots[c.i] = Spec("aux", clause=index, kind="neg")
            else:
                roots[c.i] = Spec("M", function="副詞・表否定", clause=index)  # not、never（沒有跟在助動詞後面時）
        elif d == "dative":
            if c.pos_ == "ADP":  # to me、for me：介系詞片語
                roots[c.i] = Spec("M", function=adverb_function_prep_like(c), clause=index)
            else:
                roots[c.i] = Spec("IO", clause=index)
        elif d == "dobj":
            roots[c.i] = Spec("DO" if (has_dative or info.passive) else "O", clause=index)
        elif d == "attr":
            if info.existential:
                roots[c.i] = Spec("S", clause=index, kind="real_subject")
            else:
                roots[c.i] = Spec("OC" if info.passive else "SC", clause=index)
        elif d == "acomp":
            roots[c.i] = Spec("OC" if (info.passive or has_obj) else "SC", clause=index)
        elif d == "oprd":
            # He seems happy.、The door swung open.：沒有受詞時是主詞補語
            roots[c.i] = Spec("OC" if (has_obj or info.passive) else "SC", clause=index)
        elif d in ("xcomp", "ccomp"):
            assign_complement(c, v, roots, index, info, has_obj)
        elif d == "prep" and c.lower_ == "to" and any(
            o.dep_ == "dobj" and o.lemma_.lower() in L.NOUNS_TAKING_TO and c.i == max(t.i for t in o.subtree) + 1
            for o in children
        ):
            obj = next(o for o in children if o.dep_ == "dobj")
            roots[c.i] = Spec("M", function="形容詞・修飾", modifies=obj, clause=index)
        elif d == "advmod" and multi_opener_clause(c) is not None:
            clause_verb, f = multi_opener_clause(c)
            roots[c.i] = Spec("M", function=f"副詞子句・{f}", clause=index, kind="advcl", inner_verb=clause_verb)
            info.flags.add("subordinating_conj")
        elif d in ("prep", "agent", "advmod", "npadvmod", "intj"):
            roots[c.i] = Spec("M", function=adverb_function(c), clause=index,
                              kind="npadv" if d == "npadvmod" else "")
        elif d == "advcl" and c.pos_ in ("ADJ", "ADV") and c.i < v.i and any(
                g.dep_ == "advcl" and any(m.dep_ == "mark" and m.lower_ == "as" and m.i == c.i + 1 for m in g.children)
                for g in c.children):
            # Tired as Mom was, she still cooked dinner.（形容詞 ＋ as ＋ S ＋ V：雖然、儘管）
            inner = next(g for g in c.children if g.dep_ == "advcl")
            roots[c.i] = Spec("M", function="副詞子句・表讓步", clause=index, kind="advcl", inner_verb=inner)
            info.flags.add("subordinating_conj")
        elif d == "advcl" and c.pos_ == "ADJ" and c.i < v.i:
            roots[c.i] = Spec("M", function="副詞・分詞構句", clause=index)  # (Being) Tired after work, he went to bed.
            info.flags.add("participle_phrase")
        elif d == "advcl" and c.pos_ == "ADJ" and c.i == v.i + 1 and not has_obj and not list(c.children):
            if c.lower_ in L.ADVERBIAL_ADJS and v.lemma_.lower() not in L.LINKING_VERBS:
                roots[c.i] = Spec("M", function="副詞・表方式", clause=index)  # He lives alone.
            else:
                roots[c.i] = Spec("SC", clause=index)  # The door flew open.
        elif d == "advcl":
            f = advcl_function(c)
            if f:
                roots[c.i] = Spec("M", function=f, clause=index, kind="advcl", inner_verb=c if f.startswith("副詞子句") else None)
                if f.startswith("副詞子句"):
                    info.flags.add("subordinating_conj")
                elif f == "副詞・分詞構句" or (f != "副詞・表目的" and c.tag_ in ("VBG", "VBN")):
                    info.flags.add("participle_phrase")
            else:
                roots[c.i] = Spec("unknown", clause=index)
        elif d == "preconj":
            roots[c.i] = Spec("conj", clause=index)  # You can either stay here or go…
        elif d in ("punct", "prt", "cc", "conj", "mark"):
            continue  # 標點不分配；片語動詞的介副詞留在動詞裡；對等連接由外層處理
        else:
            roots[c.i] = Spec("unknown", clause=index)

    # 賴世雄：turned him into a good student、regard him as a genius → into／as 片語是受詞補語
    if has_obj or info.passive:
        for c in children:
            if c.dep_ == "prep" and (v.lemma_.lower(), c.lower_) in L.OC_PREP_VERBS \
                    and any(g.dep_ == "pobj" for g in c.children) \
                    and (info.passive or any(o.dep_ == "dobj" and o.i < c.i for o in children)):
                roots[c.i] = Spec("OC", clause=index)

    if dative_fix:
        roots[dative_fix[0].i] = Spec("IO", clause=index)
        do = dative_fix[1]
        roots[do.i] = Spec("DO", clause=index, inner_verb=do if do.pos_ in ("VERB", "AUX") else None)

    # so／such … that：that 子句是「表結果」的副詞子句（Azar 19-4）
    #   so excited that…、such good coffee that…、speaks so fast that…
    for g in v.subtree:
        if g.dep_ not in ("ccomp", "advcl") or g.i == v.i:
            continue
        if not any(m.dep_ == "mark" and m.lower_ == "that" for m in g.children):
            continue
        anchor = g.head
        while anchor.pos_ not in ("VERB", "AUX") and anchor.head.i != anchor.i:
            anchor = anchor.head
        if anchor.i != v.i:
            continue  # 屬於別的子句
        before = [t for t in g.head.subtree if t.i < g.i and t not in set(g.subtree)]
        if any(t.lower_ in ("so", "such") for t in before):
            roots[g.i] = Spec("M", function="副詞子句・表結果", clause=index, kind="advcl", inner_verb=g)
            info.flags.add("so_such_that")

    # 形容詞補語後面的介系詞片語另外切開：excited [about the trip]、popular [with tourists]
    for r in [c for c in children if c.i in roots and roots[c.i].role in ("SC", "OC") and c.pos_ == "ADJ"]:
        for g in r.children:
            if g.dep_ == "prep" and g.i > r.i and g.i not in roots:
                roots[g.i] = Spec("M", function=adjective_pp_function(r, g), clause=index)

    # 虛主詞 It：It is hard to learn English → to learn English 是真主詞
    subj = subjects[0] if subjects else None
    cleft = cleft_clause(v, subj, children)
    if cleft is not None:
        return cleft_analysis(v, subj, cleft, roots, index, sent)
    elif subj is not None and subj.lower_ == "it":
        for r in [v] + [c for c in children if c.i in roots and roots[c.i].role == "SC"]:
            for g in r.children:
                # It is hard for me to learn English：for me to learn English 整塊是真主詞（使用者決定 2026-09-29）
                for_to = g.dep_ == "advcl" and any(x.dep_ == "mark" and x.lower_ == "for" for x in g.children)
                if (g.dep_ in ("xcomp", "ccomp") or for_to) and (g.i not in roots or roots[g.i].role in ("O", "unknown")
                                                     or (roots[g.i].role == "OC" and v.lemma_ in ("take", "cost"))):
                    gerund = g.tag_ == "VBG" and g.dep_ == "xcomp" and v.lemma_ == "be"  # It is no use crying…
                    if gerund or any(x.lower_ == "to" or x.dep_ in ("mark", "nsubj", "nsubjpass") for x in g.children):
                        roots[g.i] = Spec("RS", clause=index)
                        info.flags.add("dummy_it")
                        info.flags.discard("to_v_or_ving_object")

    # 虛受詞 it：I find it hard to wake up early、made it a rule to exercise → 句尾的 to V／that 子句是真受詞
    granted = next((c for c in children if (c.dep_ == "prep" and c.lower_ == "for" and any(g.lower_ == "granted" for g in c.children))
                    or (c.lower_ == "granted" and any(g.lower_ == "for" for g in c.children))), None) if v.lemma_ == "take" else None
    if granted is not None:  # take it for granted that…：for granted 是受詞補語（視為理所當然）
        for c in children:
            if c.i in roots and roots[c.i].role in ("IO", "DO", "O") and c.i < granted.i:
                roots[c.i] = Spec("O", clause=index)
        roots[granted.i] = Spec("OC", clause=index)
        for g in children:
            if g.dep_ in ("ccomp", "advcl", "dep") and g.i > granted.i and g.pos_ in ("VERB", "AUX"):
                roots[g.i] = Spec("O", clause=index, inner_verb=g)
    it_obj = next((c for c in v.subtree if c.i in roots and roots[c.i].role == "O" and roots[c.i].clause == index
                   and c.lower_ == "it" and c.i > v.i), None)
    comp = next((c for c in v.subtree if c.i in roots and roots[c.i].role == "OC" and roots[c.i].clause == index), None)
    if it_obj is not None and comp is not None and it_obj.i < comp.i:
        for g in list(comp.children) + list(v.children):
            if g.i <= comp.i or g.pos_ not in ("VERB", "AUX") or g.dep_ not in ("xcomp", "ccomp", "advcl", "dep"):
                continue
            if g.i in roots and roots[g.i].role not in ("O", "unknown"):
                continue
            to_v = any(x.dep_ == "aux" and x.lower_ == "to" for x in g.children)
            that = any(x.dep_ == "mark" and x.lower_ == "that" for x in g.children)
            if to_v or that:
                roots[g.i] = Spec("RO", clause=index, inner_verb=g if that else None)
                info.flags.add("dummy_object")
                info.flags.discard("to_v_or_ving_object")

    # be ＋ 介系詞片語／地方副詞 → 主詞補語（使用者決定 2026-10-01，照課本與賴世雄）：
    #   Your book is on the shelf.、I am at school. → 句型二：S + Vi + SC
    if v.lemma_ == "be" and roots.get(v.i) is not None and roots[v.i].role == VERB_ROLE and not info.existential \
            and not info.passive and not any(roots.get(c.i) and roots[c.i].role in ("SC", "O", "RS") and roots[c.i].clause == index
                                             for c in children):
        place = next((c for c in sorted(children, key=lambda t: t.i) if c.i in roots and roots[c.i].role == "M"
                      and ((c.i > v.i and c.dep_ == "prep" and any(g.dep_ in ("pobj", "pcomp") for g in c.children)
                            and not (v.lower_ == "been" and c.lower_ == "to"))  # have been to Japan（去過）維持句型一
                           or (c.i > v.i and c.dep_ == "advmod" and c.lemma_.lower() in L.PLACE_ADVERBS)
                           or (c.dep_ == "advmod" and c.lower_ == "where"))), None)  # Where is your book?
        if place is not None:
            roots[place.i] = Spec("SC", clause=index)

    # There is 句型：掛在真正主詞底下的介系詞片語，當成表地點的副詞
    if info.existential:
        for c in children:
            if c.i in roots and roots[c.i].kind == "real_subject":
                for g in c.children:
                    if g.dep_ == "prep":
                        roots[g.i] = Spec("M", function=adverb_function(g), clause=index)

    info.pattern = clause_pattern(roots, index, info)
    return info


def cleft_clause(v, subj, children):
    """強調句 It is／was ＋ 被強調的部分 ＋ that／who ＋ 其餘 → 回傳 that／who 子句的動詞；不是就回傳 None。
    只認有把握的：被強調的是人名、代名詞、介系詞片語、副詞、副詞子句；普通名詞後面接 who／which
    或當關係代名詞的 that 也算（兩種讀法都不是真主詞）。形容詞（It is true that…）是虛主詞句。"""
    if subj is None or subj.lower_ != "it" or v.lemma_ != "be":
        return None
    for c in children:
        if c.dep_ not in ("ccomp", "relcl", "advcl") or c.i < v.i or c.pos_ not in ("VERB", "AUX"):
            continue
        opener = min(c.subtree, key=lambda t: t.i)
        if opener.lower_ not in ("that", "who", "whom", "which"):
            continue
        focus = [x for x in children if v.i < x.i < opener.i and x.dep_ not in ("neg", "punct", "nsubj", "expl")
                 and not (x.dep_ == "advmod" and x.lower_ in ("only", "just", "really", "also"))]
        if not focus or any(x.dep_ == "acomp" or x.pos_ == "ADJ" for x in focus):
            continue
        f = focus[0]
        relative = opener.lower_ != "that" or opener.dep_ != "mark"
        if f.pos_ in ("PROPN", "PRON") or f.dep_ in ("prep", "advmod", "npadvmod", "advcl"):
            return c
        if f.dep_ == "attr" and f.pos_ == "NOUN" and relative:
            return c
    return None


def cleft_analysis(v, subj, c, roots, index, sent):
    """強調句（使用者決定 2026-09-29）：照「還原句」標句型。
    It was John who broke the window → John broke the window → 句型三：S + Vt + O
    It、was、who／that 標「強調句框架」（EF，不算進公式）；被強調的部分標它在還原句裡的角色，說明寫「被強調的部分」。"""
    opener = min(c.subtree, key=lambda t: t.i)
    focus = next((x for x in v.children if v.i < x.i < opener.i and x.dep_ not in ("neg", "punct", "nsubj", "expl")
                  and not (x.dep_ == "advmod" and x.lower_ in ("only", "just", "really", "also"))), None)
    inner = assign_clause(c, roots, index, sent, shared_subject=True)
    inner.flags.add("cleft")
    gap = roots.get(opener.i).role if opener.i in roots else None  # who／that 在子句裡的角色，就是被強調部分的角色
    roots[subj.i] = Spec("EF", clause=index)
    roots[v.i] = Spec("EF", clause=index)
    roots[opener.i] = Spec("EF", clause=index)
    for x in v.children:
        if x.dep_ == "neg":
            roots[x.i] = Spec("M", function="副詞・表否定", clause=index)  # It was not until midnight that…
    if focus is not None:
        nominal = focus.pos_ in ("PROPN", "PRON", "NOUN", "NUM") and focus.dep_ in ("attr", "npadvmod", "nsubj", "dobj")
        if nominal and (focus.lemma_.lower() in L.TIME_NOUNS or focus.ent_type_ in ("DATE", "TIME")):
            roots[focus.i] = Spec("M", function="副詞・表時間", clause=index, kind="cleft_focus")  # It was yesterday that…
        elif nominal:
            if gap not in ("S", "O", "IO", "DO", "SC", "OC"):
                # that 是連接詞時（It was Mary that called），看子句缺什麼：沒有主詞就是主詞
                has_subj = any(g.dep_ in ("nsubj", "nsubjpass") and g.i != opener.i for g in c.children)
                has_obj = any(g.dep_ == "dobj" and g.i != opener.i for g in c.children)
                gap = "S" if not has_subj else ("O" if not has_obj else "unknown")
            roots[focus.i] = Spec(gap, clause=index, kind="cleft_focus")
        elif focus.i in roots:
            spec = roots[focus.i]
            roots[focus.i] = Spec(spec.role, function=spec.function or (adverb_function(focus) if spec.role == "M" else None),
                                  clause=index, kind="cleft_focus", inner_verb=spec.inner_verb)
        else:
            roots[focus.i] = Spec("M", function=adverb_function(focus), clause=index, kind="cleft_focus")
    inner.pattern = clause_pattern(roots, index, inner)
    return inner


def adverb_function_prep_like(tok):
    if tok.dep_ == "prep":
        return adverb_function(tok)
    if tok.lemma_ == "to":
        obj = next((c for c in tok.children if c.dep_ == "pobj"), None)
        if obj is not None and (obj.pos_ == "PRON" or obj.lemma_.lower() in L.PERSON_NOUNS or obj.ent_type_ == "PERSON"):
            return "副詞・表對象"  # A prize was given to him.、sent a letter to her mother
        return "副詞・表地點"
    return "副詞・表目的"


def assign_complement(c, v, roots, index, info, has_obj):
    small_subj = [g for g in c.children if g.dep_ == "nsubj"]
    has_mark = any(g.dep_ == "mark" for g in c.children)
    has_to = any(g.dep_ == "aux" and g.lower_ == "to" for g in c.children)
    has_helper = any(g.dep_ in ("aux", "auxpass") for g in c.children)
    subjunctive = v.lemma_.lower() in L.SUBJUNCTIVE_VERBS and c.tag_ == "VB" and c.dep_ == "ccomp"
    if small_subj and not has_mark and not has_to and not has_helper and small_subj[0].tag_ != "PRP$" and not subjunctive \
            and c.tag_ in ("VB", "JJ", "JJR", "JJS", "NN", "NNS", "NNP", "VBN", "VBG", "RB"):  # makes you happier
        # 有助動詞的是完整子句（She said she didn't know…），不是小子句
        # 小子句：made [us] [clean the classroom]、found [the game] [very fun]
        roots[small_subj[0].i] = Spec("O", clause=index)
        roots[c.i] = Spec("OC", clause=index)
        if c.tag_ == "VB" and v.lemma_.lower() in L.CAUSATIVE_PERCEPTION:
            info.flags.add("causative_perception")
    elif small_subj and has_to and c.dep_ == "ccomp" and v.lemma_.lower() in L.VERB_OBJ_TO_V \
            and all(g.lower_ == "to" for g in c.children if g.dep_ in ("aux", "auxpass")):
        # want [you] [to come]、would like [you] [to meet…]：分析程式把受詞看成不定詞的主詞
        roots[small_subj[0].i] = Spec("O", clause=index)
        roots[c.i] = Spec("OC", clause=index)
        info.flags.add("verb_obj_to_v")
    elif c.dep_ == "xcomp" and c.pos_ in ("ADJ", "NOUN", "PROPN", "NUM"):
        roots[c.i] = Spec("OC" if (has_obj or info.passive) else "SC", clause=index)
    elif c.dep_ == "xcomp" and (has_obj or info.passive) and c.tag_ == "VB" and has_to \
            and v.lemma_.lower() not in L.VERB_OBJ_TO_V | L.CAUSATIVE_PERCEPTION \
            and c.lemma_ != "be" and not any(g.dep_ in ("nsubj", "nsubjpass") and g.lower_ == "it" for g in v.children):
        # to be … 一律是補語（characterized him to be smart）；主詞是 It 的交給虛主詞規則（It took us a long time to decide）
        roots[c.i] = Spec("M", function="副詞・表目的", clause=index)  # used the cupboard to store food
    elif c.dep_ == "xcomp" and (has_obj or info.passive) and c.tag_ == "VB":
        # asked [the students] [to give…]、made [us] [clean…]、were allowed [to play…]
        roots[c.i] = Spec("OC", clause=index)
        if has_to:
            info.flags.add("verb_obj_to_v")
        if v.lemma_.lower() in L.CAUSATIVE_PERCEPTION:
            info.flags.add("causative_perception")
    elif c.dep_ == "xcomp" and has_to and not has_obj and v.lemma_.lower() in L.SEEM_VERBS:
        # 賴世雄：He seems to know it.、He seems to be a nice man. → 不定詞是主詞補語
        roots[c.i] = Spec("SC", clause=index)
    elif v.lemma_ == "be" and not has_obj and not info.passive and c.i > v.i and (c.dep_ == "ccomp" or has_to) \
            and not any(g.dep_ in ("nsubj", "nsubjpass") and g.lower_ == "it" for g in v.children):  # It is … to／that 交給虛主詞規則
        # The problem is [that we have no money]、My dream is [to become a doctor] → be 是連綴動詞，子句是主詞補語
        opener = clause_opener(c)
        roots[c.i] = Spec("SC", clause=index, inner_verb=c if opener is not None and c.dep_ == "ccomp" else None)
    else:
        opener = clause_opener(c)
        roots[c.i] = Spec("O", clause=index, inner_verb=c if opener is not None and c.dep_ == "ccomp" else None)
        if (c.tag_ == "VBG" and not small_subj) or has_to:
            info.flags.add("to_v_or_ving_object")


def clause_pattern(roots, index, info) -> int:
    found = {s.role for s in roots.values() if s.clause == index}
    if "OC" in found:
        return 5
    if "IO" in found or ("DO" in found and info.passive):
        return 4
    if info.passive:
        return 2
    if "SC" in found:
        return 3
    if "O" in found or "DO" in found:
        return 2
    return 1


# ---------- 名詞後面的修飾語 ----------
def expand_noun_modifiers(roots, tokens, owner_of):
    """名詞後面的介系詞片語、形容詞子句、分詞片語 → 形容詞・修飾 X（可以一層層往下找）"""
    changed = True
    while changed:
        changed = False
        for tok in tokens:
            if tok.pos_ not in ("NOUN", "PROPN", "PRON", "NUM"):
                continue
            own = owner_of(tok)
            if own is None:
                continue
            spec = roots[own.i]
            if spec.role not in NOMINAL | {"M"}:
                continue
            if spec.role in NOMINAL and own.pos_ in ("VERB", "AUX") and own.i != tok.i \
                    and any(c.dep_ in ("nsubj", "nsubjpass", "mark") for c in own.children):
                continue  # that people who sleep … are：子句裡的修飾語留在子句裡，不要把子句切成兩半
            if spec.role == "M" and spec.function and not spec.function.startswith(("副詞・表", "形容詞")):
                continue
            # a lot of homework to do：修飾的是 of 後面的 homework，不是數量詞 lot
            of = next((c for c in tok.children if c.dep_ == "prep" and c.lower_ == "of"), None)
            of_obj = next((c for c in of.children if c.dep_ == "pobj"), None) if of is not None else None
            target = of_obj if of_obj is not None and tok.lemma_.lower() in L.QUANTIFIERS | L.UNIT_NOUNS else tok
            for g in tok.children:
                if g.i in roots or g.i < tok.i:
                    continue
                if spec.kind == "npadv":
                    # Every morning before school：名詞片語當副詞時，後面的時間介系詞片語另外切開
                    if g.dep_ == "prep" and g.lemma_.lower() in L.TIME_PREPS:
                        roots[g.i] = Spec("M", function="副詞・表時間", clause=spec.clause)
                        changed = True
                    continue
                if g.dep_ == "prep" and g.lower_ != "of":
                    obj = next((x for x in g.children if x.dep_ == "pobj"), None)
                    olemma = obj.lemma_.lower() if obj is not None else ""
                    is_time = obj is not None and (olemma in L.TIME_NOUNS or obj.ent_type_ in ("DATE", "TIME"))
                    if is_time and (tok.pos_ == "NUM" or tok.lemma_.lower() in L.TIME_NOUNS):
                        continue  # at eight in the morning：整段都是時間，不拆開
                    if is_time and tok.lemma_.lower() not in L.TIME_NOUNS and spec.role in NOMINAL:
                        # on a busy day 掛在受詞上 → 其實是說明動作的時間
                        roots[g.i] = Spec("M", function="副詞・表時間", clause=spec.clause, kind="reattached")
                    elif (tok.dep_ == "dobj" and g.lemma_.lower() in ("in", "at", "on")
                          and olemma in L.PLACE_NOUNS and g.i == max(t.i for t in tok.subtree if not t.is_punct) - len(list(g.subtree)) + 1):
                        # water the flowers in the garden：句尾的「在某個場所」→ 表地點（說明裡會補充另一種理解）
                        roots[g.i] = Spec("M", function="副詞・表地點", clause=spec.clause, kind="reattached", modifies=None)
                        roots[g.i].kind = "ambiguous_place"
                    else:
                        roots[g.i] = Spec("M", function="形容詞・修飾", modifies=target, clause=spec.clause)
                    changed = True
                elif g.dep_ in ("relcl", "acl") and any(t.lower_ in ("so", "such") for t in tok.subtree if t.i < tok.i) \
                        and any(t.lower_ == "that" and t.i < g.i + 1 for t in g.subtree) \
                        and not any(t.lower_ == "that" and t.dep_ in ("nsubj", "dobj", "nsubjpass") for t in g.children):
                    # such good coffee that I had another cup：that 子句表結果（Azar 19-4）
                    roots[g.i] = Spec("M", function="副詞子句・表結果", clause=spec.clause, kind="advcl", inner_verb=g)
                    changed = True
                elif g.dep_ in ("relcl", "acl", "ccomp") and tok.lemma_.lower() in L.APPOSITIVE_NOUNS \
                        and any(t.lower_ == "that" and t.dep_ == "mark" for t in g.children):
                    # The fact that he lied：that 在子句裡不當主詞也不當受詞 → 同位語子句，說明 fact 的內容
                    roots[g.i] = Spec("M", function="同位語・說明", modifies=tok, clause=spec.clause, kind="appos", inner_verb=g)
                    changed = True
                elif g.dep_ == "relcl":
                    roots[g.i] = Spec("M", function="形容詞・修飾", modifies=target, clause=spec.clause, kind="relcl", inner_verb=g)
                    changed = True
                elif g.dep_ == "acl":
                    roots[g.i] = Spec("M", function="形容詞・修飾", modifies=target, clause=spec.clause, kind="acl")
                    changed = True
                elif g.dep_ == "appos":
                    # Paris, the capital of France：同位語（Azar 13-15）
                    roots[g.i] = Spec("M", function="同位語・說明", modifies=tok, clause=spec.clause, kind="appos")
                    changed = True
                elif g.dep_ == "amod" and len(list(g.subtree)) > 1:
                    # the woman responsible for the error：名詞後面的形容詞片語
                    roots[g.i] = Spec("M", function="形容詞・修飾", modifies=tok, clause=spec.clause, kind="post_adj")
                    changed = True


def make_owner_fn(roots, stop_at=None):
    def owner_of(tok):
        t = tok
        while True:
            if t.i in roots:
                return t
            if t.head.i == t.i or (stop_at is not None and t.i == stop_at.i):
                return None
            t = t.head
    return owner_of


# ---------- 片段 ----------
def build_chunks(sent, roots, tokens, text, offset=0):
    """把字分給片段，回傳 [(root_token, [tokens])]，依位置排序"""
    owner_of = make_owner_fn(roots)
    groups: dict[int, list] = {}
    for tok in tokens:
        own = owner_of(tok)
        if own is None:
            continue
        if tok.is_punct and tok.head.i == own.i and roots[own.i].role in (VERB_ROLE, "aux"):
            continue  # 句尾標點
        groups.setdefault(own.i, []).append(tok)
    return groups


def span_of(toks, text, base):
    """片段的字元範圍，去掉頭尾標點"""
    toks = sorted(toks, key=lambda t: t.i)
    while toks and toks[-1].is_punct:
        toks.pop()
    while toks and toks[0].is_punct:
        toks.pop(0)
    if not toks:
        return None
    start = toks[0].idx - base
    end = toks[-1].idx + len(toks[-1].text) - base
    last = toks[-1]
    if len(last.text) > 1 and last.text.endswith(".") and last.text[:-1].isalpha() and last.i == last.sent.end - 1:
        end -= 1  # So do I.：分析程式把「I.」當成一個字
    return start, end


def contiguous_runs(toks):
    toks = sorted(toks, key=lambda t: t.i)
    runs, cur = [], [toks[0]]
    for t in toks[1:]:
        if t.i == cur[-1].i + 1:
            cur.append(t)
        else:
            runs.append(cur)
            cur = [t]
    runs.append(cur)
    return runs


def heads_for(root, spec, toks, flags, vars_):
    if spec.role not in NOMINAL or len([t for t in toks if not t.is_punct]) < 2:
        return []
    lemma = root.lemma_.lower()
    of = next((c for c in root.children if c.dep_ == "prep" and c.lower_ == "of"), None)
    pobj = next((c for c in of.children if c.dep_ == "pobj"), None) if of is not None else None
    the_number = lemma == "number" and any(c.dep_ == "det" and c.lower_ == "the" for c in root.children)
    if of is not None and pobj is not None and lemma in L.QUANTIFIERS and not the_number:
        if spec.role == "S":  # 卡片講的是主詞和動詞的單複數，補語、受詞（is one of the biggest problems）不附
            flags.add("quantifier_of")
            vars_.setdefault("quantifier_of", {"noun": pobj.text})
        return []
    if of is not None and pobj is not None and lemma in L.UNIT_NOUNS:
        flags.add("unit_of")
        vars_.setdefault("unit_of", {"unit": root.text, "noun": pobj.text})
        return [pobj] + [c for c in pobj.children if c.dep_ == "conj"]
    if root.pos_ in ("NOUN",):
        return [root] + [c for c in root.children if c.dep_ == "conj" and c.pos_ == "NOUN"]
    if root.pos_ == "ADJ":
        return [root]
    return []


def structure_of(root, spec, toks):
    n = len([t for t in toks if not t.is_punct])
    d = root.dep_
    if spec.kind == "relcl":
        return "形容詞子句"
    if spec.kind == "advcl" and spec.function and spec.function.startswith("副詞子句"):
        return "副詞子句"
    if d in ("prep", "agent") or root.pos_ == "ADP":
        return "介系詞片語"
    if spec.kind == "acl":
        return "分詞片語"
    if any(c.dep_ == "mark" and c.lower_ in ("that", "whether", "if") for c in root.children) and root.pos_ in ("VERB", "AUX"):
        return "名詞子句"
    # 疑問詞開頭（why the TV stopped…）或省略 that（she said she was tired）的名詞子句：
    # 這一段裡面有自己的主詞。主詞在這一段外面的不算（made us clean the room 的 clean the room）
    inside = {t.i for t in toks}
    if root.pos_ in ("VERB", "AUX") and spec.role not in (VERB_ROLE, "aux") and any(
        c.dep_ in ("nsubj", "nsubjpass", "expl") and c.i in inside for c in root.children
    ):
        return "名詞子句"
    if root.pos_ in ("VERB", "AUX") and spec.role not in (VERB_ROLE, "aux"):
        if any(c.dep_ == "aux" and c.lower_ == "to" for c in root.children):
            return "不定詞片語"
        if root.tag_ == "VBG":
            return "動名詞片語" if n > 1 else "動名詞"
        return "原形動詞片語" if n > 1 else None
    if root.pos_ in ("NOUN", "PROPN"):
        return "名詞片語" if n > 1 else "名詞"
    if root.pos_ == "PRON":
        return "代名詞"
    if root.pos_ == "ADJ":
        return "形容詞片語" if n > 1 else "形容詞"
    if root.pos_ == "ADV":
        return "副詞片語" if n > 1 else "副詞"
    return None


VERB_LABEL = {1: "Vi", 2: "Vt", 3: "V", 4: "Vt", 5: "Vt"}


def to_chunks(sent, roots, clause_infos, text, base, flags, vars_, tokens=None, with_inner=True):
    """把片段根轉成 Chunk 物件"""
    tokens = tokens if tokens is not None else list(sent)
    groups = build_chunks(sent, roots, tokens, text)
    items = []
    for ri, toks in groups.items():
        root = sent.doc[ri]
        spec = roots[ri]
        role = spec.role
        info = clause_infos.get(spec.clause)
        if role == VERB_ROLE:
            role = "Vt" if info and info.passive else VERB_LABEL.get(info.pattern if info else 1, "Vi")
            if info and info.existential:
                role = "Vi"
        for run in contiguous_runs(toks):
            sp = span_of(run, text, base)
            if sp is None:
                continue
            items.append((sp, root, spec, role, run))
    items.sort(key=lambda x: x[0][0])

    chunks = []
    for cid, (sp, root, spec, role, toks) in enumerate(items):
        heads = heads_for(root, spec, toks, flags, vars_) if role in NOMINAL else []
        heads = [h for h in heads if sp[0] <= h.idx - base < sp[1]]
        inner = []
        if with_inner and spec.inner_verb is not None:
            inner = inner_chunks(sent, spec.inner_verb, text, base, top=root)
        modifies = None
        if spec.modifies is not None:
            m = spec.modifies
            modifies = Span(start=m.idx - base, end=m.idx - base + len(m.text), text=m.text)
        chunks.append(
            dict(
                id=cid, text=text[sp[0]:sp[1]], start=sp[0], end=sp[1], role=role,
                function=spec.function if role == "M" else None, modifies=modifies,
                heads=[Span(start=h.idx - base, end=h.idx - base + len(h.text), text=h.text) for h in heads],
                structure=structure_of(root, spec, toks), clause=spec.clause, inner=inner,
                _root=root, _spec=spec,
            )
        )
    return chunks


def inner_chunks(sent, verb, text, base, top=None):
    """可以展開的子句（形容詞子句、副詞子句）內部的拆解；top 是整個片段的根（連接詞可能掛在子句外面）"""
    roots = {}
    info = assign_clause(verb, roots, 0, sent)
    for t in opener_tokens(verb)[0]:
        roots[t.i] = Spec("conj")
    scope = set(verb.subtree)
    if top is not None and top.i != verb.i:
        for t in top.subtree:
            if t not in scope and not t.is_punct:
                roots[t.i] = Spec("conj")
                scope.add(t)
    roots = {i: s for i, s in roots.items() if sent.doc[i] in scope}
    sub = sorted(scope, key=lambda t: t.i)
    out = to_chunks(sent, roots, {0: info}, text, base, set(), {}, tokens=sub, with_inner=False)
    merged = []
    for c in out:
        if merged and merged[-1]["role"] == "conj" and c["role"] == "conj" and text[merged[-1]["end"]:c["start"]].strip() == "":
            prev = merged.pop()
            c = dict(prev, end=c["end"], text=text[prev["start"]:c["end"]])
        merged.append(c)
    result = []
    for c in merged:
        c.pop("_root"), c.pop("_spec")
        c["heads"], c["inner"], c["clause"] = [], [], 0
        if c["role"] == "M" and not c["function"]:
            c["function"] = "副詞・表方式"
        result.append(Chunk(**c))
    return result


# ---------- 文法重點卡 ----------
CARD_ORDER = [
    "passive", "present_perfect", "present_progressive", "there_be", "imperative",
    "yes_no_question", "dummy_it", "gerund_subject", "coordinating_conj",
    "subordinating_conj", "relative_pronoun", "causative_perception", "dative_verbs",
    "linking_verbs", "to_v_or_ving_object", "quantifier_of", "unit_of",
    "cleft", "verb_multiple_patterns", "parallel_structure", "participle_phrase", "appositive", "so_such_that", "modifier_position",
]
MAX_CARDS = 3


def comparative_correlative(sent, v, roots, info):
    """The more you practice, the better you get.（越…就越…）
    前半「the ＋ 比較級 …」整塊是副詞子句（表條件）；後半是主要子句，the ＋ 比較級是被移到前面的補語或受詞：
    the better you get → you get better（句型二：S + Vi + SC）。沒把握的部分留給「未分析」。"""
    toks = [t for t in sent if not t.is_space]
    if len(toks) < 4 or toks[0].lower_ != "the" or not (toks[1].tag_ in ("JJR", "RBR") or toks[1].lower_ in ("more", "less", "fewer")):
        return False
    comma = next((t for t in toks if t.lower_ == ","), None)
    if comma is None or comma.i >= v.i:
        return False
    first = next((c for c in v.children if c.i < comma.i and min(x.i for x in c.subtree) == toks[0].i), None)
    if first is None:
        return False
    for t in first.subtree:
        if t.i != first.i:
            roots.pop(t.i, None)
    roots[first.i] = Spec("M", function="副詞子句・表條件", clause=info.index)
    info.flags.discard("participle_phrase")
    info.flags.add("comparative_correlative")
    # 後半：the ＋ 比較級
    for c in v.children:
        if not (comma.i < c.i < v.i) or not any(g.lower_ == "the" for g in c.children):
            continue
        if c.tag_ in ("JJR", "JJ") and c.dep_ in ("amod", "acomp", "oprd", "advmod", "attr") and v.lemma_ in L.LINKING_VERBS:
            roots[c.i] = Spec("SC", clause=info.index)  # the better you get → you get better
        elif c.dep_ == "dobj":
            roots[c.i] = Spec("O", clause=info.index)  # the more you forget → you forget more
    info.pattern = clause_pattern(roots, info.index, info)
    return True


def tense_flags(info, roots, doc, flags):
    v = info.verb_token
    auxes = [doc[i] for i, s in roots.items() if s.role == "aux" and s.clause == info.index and s.kind != "neg"]
    lemmas = [a.lemma_.lower() for a in auxes]
    if info.passive:
        flags.add("passive")
    elif v.tag_ == "VBG" and "be" in lemmas:
        if any(a.lower_ in ("am", "is", "are", "'m", "'s", "'re") for a in auxes):
            flags.add("present_progressive")
    elif v.tag_ == "VBN" and any(a.lower_ in ("have", "has", "'ve") for a in auxes) \
            and not any(a.tag_ == "MD" or a.lower_ == "to" for a in auxes):
        flags.add("present_perfect")  # would／should／must have ＋ p.p. 不是現在完成式


def tag_question_main(root, sent):
    """句尾是「助動詞 ＋ 代名詞 ?」的附加問句時，回傳前面真正的主要動詞"""
    if not sent.text.rstrip().endswith("?") or root.lemma_.lower() not in L.AUX_LEMMAS:
        return None
    kids = [c for c in root.children if c.dep_ != "punct"]
    main = next((c for c in kids if c.dep_ == "ccomp" and c.i < root.i), None)
    subj = [c for c in kids if c.dep_ in ("nsubj", "expl") and c.i > root.i]
    rest = [c for c in kids if c is not main and c not in subj and c.dep_ != "neg"]
    if main is None or len(subj) != 1 or subj[0].pos_ != "PRON" or rest:
        return None
    return main


# ---------- 主程式 ----------
def clean_spaces(text: str) -> str:
    """從網頁複製的句子常夾著不斷行空白、全形空白、零寬字元或連續空白，
    分析程式會把它們當成一個字而看錯結構（畫面上也會空兩格）→ 統一成一個普通空白"""
    text = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def analyze_sentence(text: str) -> SentenceResult:
    text = clean_spaces(text)
    if not re.search(r"[A-Za-z]{2,}", text) or re.search(r"[\u3400-\u9fff]", text):
        return SentenceResult(text=text, status="failed", clauses=[], chunks=[],
                              message="請輸入英文句子（不能包含中文字）。")
    doc = get_nlp()(text)
    sents = list(doc.sents)
    if not sents:
        return SentenceResult(text=text, status="failed", message="沒有辦法分析這段文字，請輸入一個英文句子。", clauses=[], chunks=[])
    sent = sents[0]
    base = sent.start_char
    stext = sent.text
    message = None
    status = "ok"
    if len(sents) > 1:
        status = "partial"
        message = "目前一次只能分析一句，這裡只顯示第一句的分析。"

    root = sent.root
    if root.pos_ not in ("VERB", "AUX"):
        return SentenceResult(
            text=stext, status="failed", clauses=[], chunks=[],
            message="找不到句子的主要動詞，這可能不是一個完整的句子（例如只有片語），請再確認一次。",
        )

    roots: dict[int, Spec] = {}
    flags: set[str] = set()
    vars_: dict[str, dict] = {}
    kind = "simple"

    # 附加問句：She didn't do it, did she? 分析程式把句尾的 did she 當成主要動詞
    tag_main = tag_question_main(root, sent)
    if tag_main is not None:
        roots[root.i] = Spec("M", function="附加問句", clause=0)
        root = tag_main

    # so 連接的對等句，分析程式有時把前半句當成後半句動詞的 ccomp
    lead = next((c for c in root.children if c.dep_ == "ccomp" and c.i < root.i
                 and any(g.dep_ in ("nsubj", "nsubjpass", "expl") for g in c.children)), None)
    joiner = None
    if lead is not None:
        joiner = next((c for c in root.children if lead.i < c.i < root.i and c.lower_ in ("so", "and", "but", "or", "yet")), None)
    if lead is not None and joiner is not None:
        infos = {0: assign_clause(lead, roots, 0, sent), 1: assign_clause(root, roots, 1, sent)}
        roots[root.i] = Spec(VERB_ROLE, clause=1)
        roots[lead.i] = Spec(VERB_ROLE, clause=0)
        roots[joiner.i] = Spec("conj", clause=0)
        kind = "compound"
        flags.add("coordinating_conj")
    else:
        infos = {0: assign_clause(root, roots, 0, sent)}

    # 對等句：主要動詞底下還有另一個有自己主詞的動詞
    for c in (root.children if kind == "simple" else []):
        if c.dep_ == "conj" and c.pos_ in ("VERB", "AUX") and any(
            g.dep_ in ("nsubj", "nsubjpass", "expl") for g in c.children
        ):
            idx = len(infos)
            infos[idx] = assign_clause(c, roots, idx, sent)
            kind = "compound"
    if kind == "compound":
        for c in root.children:
            if c.dep_ == "cc":
                roots[c.i] = Spec("conj", clause=0)
        flags.add("coordinating_conj")
    elif lead is None or joiner is None:
        shared = [c for c in root.children if c.dep_ == "conj" and c.pos_ in ("VERB", "AUX")]
        if shared:
            # 動詞的對等連接：主詞只寫一次，兩個動詞各自有自己的受詞或補語
            for c in shared:
                idx = len(infos)
                infos[idx] = assign_clause(c, roots, idx, sent, shared_subject=True)
            for c in root.children:
                if c.dep_ == "cc":
                    roots[c.i] = Spec("conj", clause=0)
            # 動詞 ＋ and ＋ 動詞 是同一個句子裡的平行結構，不是兩個子句（Azar 16-1）
            flags.add("parallel_structure")
        else:
            for c in root.children:
                if c.dep_ in ("conj", "cc"):
                    roots[c.i] = Spec("unknown", clause=0)

    if kind == "simple":
        comparative_correlative(sent, root, roots, infos[0])
    owner_of = make_owner_fn(roots)
    expand_noun_modifiers(roots, list(sent), owner_of)

    # wh- 疑問句：簡單的（Where did you buy…?、Who broke…?）已經能正確分析；
    # 分析結果出現「未分析」的片段時，才提醒使用者結果僅供參考（見下方 raw 產生後的檢查）
    first = sent[0]
    wh_question = stext.endswith("?") and first.tag_ in ("WDT", "WP", "WP$", "WRB")
    if wh_question:
        for info in infos.values():
            info.question = False  # 不顯示 Yes／No 問句的文法重點卡

    for info in infos.values():
        tense_flags(info, roots, doc, flags)
        if info.existential:
            flags.add("there_be")
        if info.imperative:
            flags.add("imperative")
        if info.question:
            flags.add("yes_no_question")
        if info.pattern == 4:
            flags.add("dative_verbs")
        if info.pattern == 3 and info.verb_token.lemma_ != "be":
            flags.add("linking_verbs")
        if info.verb_token.lemma_.lower() in L.MULTI_PATTERN_VERBS:
            flags.add("verb_multiple_patterns")
            vars_.setdefault("verb_multiple_patterns", {"verb": info.verb_token.lemma_.lower()})
        flags |= info.flags

    raw = to_chunks(sent, roots, infos, stext, base, flags, vars_)
    if wh_question and status == "ok" and any(c["role"] == "unknown" for c in raw):
        status, message = "partial", "這種 wh- 疑問句（what、where、how…）目前還沒辦法完整分析，結果僅供參考。"
    # 不可能的結果：同一個子句有兩個主詞、兩個受詞或兩個補語 → 一定有地方分析錯了，提醒使用者
    #   （平行結構的兩組 Vt ＋ O 除外）
    if status == "ok" and "parallel_structure" not in flags:
        from collections import Counter
        counts = Counter((c["_spec"].clause, c["role"]) for c in raw if c["role"] in ("S", "O", "IO", "DO", "SC", "OC", "V"))
        # 連綴動詞 V 後面不會有受詞（It is no use crying… 的 crying 如果被標成 O，一定是看錯了）
        linking_obj = any(counts[(k, "V")] and counts[(k, "O")] for k, _ in list(counts))
        if linking_obj or any(n > 1 for (k, r), n in counts.items() if r != "V"):
            status, message = "partial", "這句的結構比較複雜，分析結果可能有錯，僅供參考。"

    # 修飾語位置：形容詞修飾語放在名詞後面
    if any(c["_spec"].modifies is not None and c["_spec"].modifies.i < c["_root"].i for c in raw):
        flags.add("modifier_position")
    if any(c["_spec"].function == "副詞子句・表結果" for c in raw):
        flags.add("so_such_that")
    if any(c["_spec"].kind == "appos" for c in raw):
        flags.add("appositive")
    if any(c["_spec"].kind == "relcl" and any(t.tag_ in ("WDT", "WP", "WP$") or t.lower_ == "that"
                                              for t in c["_root"].subtree) for c in raw):
        flags.add("relative_pronoun")

    # 沒有分配到的字 → 未分析
    covered = set()
    for c in raw:
        covered.update(range(c["start"], c["end"]))
    for tok in sent:
        s = tok.idx - base
        if not tok.is_punct and s not in covered and not tok.is_space:
            raw.append(dict(id=0, text=tok.text, start=s, end=s + len(tok.text), role="unknown",
                            function=None, modifies=None, heads=[], structure=None, clause=0, inner=[],
                            _root=tok, _spec=Spec("unknown")))
    if any(c["role"] == "unknown" for c in raw) and status == "ok":
        status = "partial"
        message = "這句比較複雜，灰色虛線的部分目前還沒辦法分析。"

    # 祈使句：補上省略的 (You)
    for info in infos.values():
        if info.imperative:
            vt = info.verb_token
            before = [c for c in raw if c["role"] == "aux" and c["clause"] == info.index and c["start"] < vt.idx - base]
            pos = min([c["start"] for c in before] + [vt.idx - base])
            raw.append(dict(id=0, text="(You)", start=pos, end=pos, role="S", implicit=True,
                            function=None, modifies=None, heads=[], structure=None, clause=info.index,
                            inner=[], _root=None, _spec=Spec("S", kind="implicit")))

    # 否定：Do ＋ n't、is ＋ not 合成一個 aux 片段；have ＋ to 合成 have to；be ＋ going ＋ to 合成 are going to
    raw.sort(key=lambda c: (c["start"], 0 if c.get("implicit") else 1))
    joined = []
    for c in raw:
        prev_text = joined[-1]["text"].lower() if joined else ""
        if joined and joined[-1]["role"] == "aux" and c["role"] == "aux" and stext[joined[-1]["end"]:c["start"]].strip() == "" \
                and (c["text"].lower() in ("n't", "not")
                     or (c["text"].lower() == "to" and (prev_text in ("have", "has", "had", "used", "use")
                                                         or prev_text.endswith(("going", "supposed", "able"))))
                     or c["text"].lower() in ("going", "supposed", "able")
                     or (c["text"].lower() in ("better", "rather") and prev_text in ("had", "'d", "would"))):
            prev = joined.pop()
            c = dict(prev, end=c["end"], text=stext[prev["start"]:c["end"]])
        joined.append(c)
    raw = joined

    # 把緊貼在介系詞片語前面、單獨的 even／only／just 併進去（Even in the heavy rain）
    raw.sort(key=lambda c: (c["start"], 0 if c.get("implicit") else 1))
    merged = []
    for c in raw:
        if merged and merged[-1]["role"] == "EF" and c["role"] == "EF" and stext[merged[-1]["end"]:c["start"]].strip() == "":
            prev = merged.pop()  # 強調句框架 It ＋ was 合成一塊
            c = dict(prev, end=c["end"], text=stext[prev["start"]:c["end"]])
        elif merged and merged[-1]["role"] == "M" and c["role"] == "M" and merged[-1]["text"].lower() in ("even", "only", "just", "right") \
                and stext[merged[-1]["end"]:c["start"]].strip() == "":
            prev = merged.pop()
            c = dict(c, start=prev["start"], text=stext[prev["start"]:c["end"]])
        elif merged and merged[-1]["role"] == "M" and c["role"] == "M" and merged[-1]["text"].lower() in ("in order", "so as") \
                and c["text"].lower().startswith("to ") and stext[merged[-1]["end"]:c["start"]].strip() == "":
            prev = merged.pop()  # in order to catch the first train：整組是表目的
            c = dict(prev, end=c["end"], text=stext[prev["start"]:c["end"]], function="副詞・表目的", modifies=None, structure="不定詞片語")
        merged.append(c)
    raw = merged

    # 對等句：以連接詞為界，前面屬於子句一、後面屬於子句二（分析程式有時把修飾語掛錯子句）
    if kind == "compound":
        seen = 0
        for c in raw:
            if c["role"] == "conj":
                c["clause"] = seen
                seen += 1
            else:
                c["clause"] = min(seen, len(infos) - 1)

    chunks = []
    for i, c in enumerate(raw):
        c["id"] = i
        c["note"] = chunk_note(c, infos, stext, compound=(kind == "compound"))
        if c.get("_spec") is not None and c["_spec"].kind == "lets_us":
            c["suffix"] = "（us）"  # 使用者要求：畫面上直接看得到 's 就是 us
        c.pop("_root", None)
        c.pop("_spec", None)
        chunks.append(Chunk(**c))

    if "parallel_structure" in flags and kind != "compound":
        clauses = parallel_clauses(infos, chunks)
    else:
        clauses = [
            Clause(index=i, pattern=info.pattern, passive=info.passive, formula=formula(info, chunks), elliptic=info.elliptic)
            for i, info in infos.items()
        ]
    for cl in clauses:
        info = infos.get(cl.index)
        if info is not None and info.verb_token is not None and not info.elliptic:
            cl.verb = info.verb_token.lemma_.lower()
            # 片語動詞（depend on、belong to）整組當 Vt，動詞本身在字典裡是 Vi 很正常，不提醒
            cl.doubt = None if "phrasal_verb" in info.flags else verb_check(cl.verb, cl.pattern)
    phrases = find_phrases(sent)
    if any(p.kind == "慣用語" and " of " in f" {p.words} " for p in phrases):
        flags = flags - {"unit_of", "quantifier_of"}  # a piece of cake 是慣用語，不是「一塊」蛋糕
    cards = [CardRef(id=f, vars=vars_.get(f, {})) for f in CARD_ORDER if f in flags][:MAX_CARDS]
    return SentenceResult(text=stext, status=status, message=message, kind=kind, clauses=clauses, chunks=chunks, cards=cards,
                          phrases=phrases)


MAX_SENTENCES = 30


def split_sentences(text: str) -> list[str]:
    """整段文章切成句子（用 spaCy 的斷句，縮寫如 Mr. 不會被誤切）"""
    doc = get_nlp()(clean_spaces(text))
    return [s.text.strip() for s in doc.sents if s.text.strip()]


def analyze_text(text: str) -> list[SentenceResult]:
    """整段文章：逐句分析；超過上限的句子不分析"""
    text = clean_spaces(text)
    if not re.search(r"[A-Za-z]{2,}", text) or re.search(r"[\u3400-\u9fff]", text):
        return [analyze_sentence(text)]
    parts = split_sentences(text)
    results = [analyze_sentence(p) for p in parts[:MAX_SENTENCES]]
    if len(parts) > MAX_SENTENCES:
        rest = " ".join(parts[MAX_SENTENCES:])
        results.append(SentenceResult(text=rest, status="failed", clauses=[], chunks=[],
                                      message=f"文章太長了，只分析前 {MAX_SENTENCES} 句，後面的 {len(parts) - MAX_SENTENCES} 句沒有分析。"))
    return results


COUNT = {2: "兩", 3: "三", 4: "四"}


def parallel_clauses(infos, chunks):
    """平行結構的標題：句型相同 → 句型三：S + Vt + O（兩組 Vt + O 並列）；不同 → 各自列出，後面的主詞加括號"""
    items = [infos[i] for i in sorted(infos)]
    first = items[0]
    if all(x.pattern == first.pattern and x.passive == first.passive for x in items):
        f = formula(first, chunks)
        rest = f.split("S + ", 1)[1]
        n = COUNT.get(len(items), str(len(items)))
        return [Clause(index=0, pattern=first.pattern, passive=first.passive, formula=f"{f}（{n}組 {rest} 並列）")]
    out = []
    for i, x in enumerate(items):
        f = formula(x, chunks)
        out.append(Clause(index=i, pattern=x.pattern, passive=x.passive, formula=f if i == 0 else f.replace("S + ", "（S）+ ", 1)))
    return out


FORMULA = {1: "S + Vi", 2: "S + Vt + O", 3: "S + Vi + SC", 4: "S + Vt + IO + DO", 5: "S + Vt + O + OC"}


def formula(info, chunks):
    if info.elliptic:
        return "S + 助動詞（後面的動詞省略了）"
    if not info.passive:
        return FORMULA[info.pattern]
    rest = {4: " + DO", 5: " + OC"}.get(info.pattern, "")
    return f"S + be + p.p.{rest}"
