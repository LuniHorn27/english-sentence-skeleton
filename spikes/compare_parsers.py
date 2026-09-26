"""0-4 實測比較：用練習題比較各分析程式。

這是「快速試做」的轉換程式，只轉主幹，目的是比較分析程式本身的好壞，
不是正式的分析引擎。每個分析程式都用同樣精簡的規則轉換，比較才公平。

比較項目：
  1. 主幹角色：每個標準答案的主幹片段（S、V、aux、O、IO、DO、SC、OC），程式有沒有標對
  2. 句型：整句的句型編號對不對
  3. 片語邊界（只有能做片語結構的程式）：標準答案的每個片段，是否剛好對應到一個完整片語
"""
import re
import sys
import time
import warnings
from collections import Counter, defaultdict

import yaml

warnings.filterwarnings("ignore")

GOLD = yaml.safe_load(open("tests/practice/gold.yaml", encoding="utf-8"))
V_ROLES = {"Vi", "Vt", "V"}


# ---------- 共用：由角色推出動詞種類與句型 ----------
def finish(roles, passive, has_expl):
    """roles：{token_index: role}，補上動詞種類並推出句型"""
    found = set(roles.values())
    if "OC" in found:
        pattern = 5
    elif "IO" in found or ("DO" in found and passive):
        pattern = 4
    elif "SC" in found:
        pattern = 3
    elif "O" in found or "DO" in found or passive:
        pattern = 2
    else:
        pattern = 1
    vlabel = {1: "Vi", 2: "Vt", 3: "V", 4: "Vt", 5: "Vt"}[pattern]
    for i, r in roles.items():
        if r == "VERB":
            roles[i] = vlabel
    return pattern


# ---------- spaCy 的轉換（ClearNLP 標籤） ----------
def spacy_roles(doc):
    root = next(t for t in doc if t.dep_ == "ROOT")
    roles, kids = {}, list(root.children)
    deps = {c.dep_ for c in kids}
    passive = "auxpass" in deps or "nsubjpass" in deps
    has_expl = "expl" in deps
    roles[root.i] = "VERB"
    for c in kids:
        d = c.dep_
        if d in ("nsubj", "nsubjpass", "csubj"):
            roles[c.i] = "S"
        elif d in ("aux", "auxpass") or (d == "neg" and c.i < root.i and roles.get(c.i - 1) == "aux"):
            roles[c.i] = "aux"
        elif d == "dative":
            roles[c.i] = "IO"
        elif d == "dobj":
            roles[c.i] = "DO" if ("dative" in deps or passive) else "O"
        elif d == "attr":
            roles[c.i] = "S" if has_expl else ("OC" if passive else "SC")
        elif d == "acomp":
            roles[c.i] = "OC" if passive else "SC"
        elif d == "oprd":
            roles[c.i] = "OC"
        elif d in ("ccomp", "xcomp"):
            subj = [g for g in c.children if g.dep_ == "nsubj"]
            if subj and c.tag_ in ("VB", "JJ", "NN", "NNP") and not any(g.dep_ == "mark" for g in c.children):
                roles[subj[0].i] = "O"  # 小子句：made [us] [clean …]
                roles[c.i] = "OC"
            elif c.pos_ in ("ADJ",) and d == "xcomp":
                roles[c.i] = "OC" if ("dobj" in deps or passive) else "SC"
            else:
                roles[c.i] = "O"
    if "S" not in roles.values() and root.tag_ == "VB":
        roles[-1] = "S"  # 祈使句：省略的 (You)
    return roles, passive, has_expl


# ---------- Stanza 的轉換（Universal Dependencies 標籤） ----------
def stanza_roles(sent):
    words = sent.words
    root = next(w for w in words if w.head == 0)
    kids = [w for w in words if w.head == root.id]
    deps = {w.deprel for w in kids}
    passive = "aux:pass" in deps or "nsubj:pass" in deps
    has_expl = "expl" in deps
    roles = {}
    cop = [w for w in kids if w.deprel == "cop"]
    if cop:  # She is a nurse：UD 以 nurse 為句子核心，be 是 cop
        roles[cop[0].id - 1] = "VERB"
        roles[root.id - 1] = "SC"
    else:
        roles[root.id - 1] = "VERB"
    for w in kids:
        d, i = w.deprel, w.id - 1
        if d in ("nsubj", "nsubj:pass", "csubj"):
            roles[i] = "S"
        elif d in ("aux", "aux:pass"):
            roles[i] = "aux"
        elif d == "advmod" and w.lemma == "not" and roles.get(i - 1) == "aux":
            roles[i] = "aux"
        elif d == "iobj":
            roles[i] = "IO"
        elif d == "obj":
            roles[i] = "DO" if ("iobj" in deps or passive) else "O"
        elif d == "xcomp":
            if "obj" in deps or passive:
                roles[i] = "OC"
            elif w.upos in ("ADJ", "NOUN", "PROPN"):
                roles[i] = "SC"
            else:
                roles[i] = "O"
        elif d == "ccomp":
            roles[i] = "O"
    verb = words[cop[0].id - 1] if cop else root
    if "S" not in roles.values() and verb.xpos == "VB":
        roles[-1] = "S"  # 祈使句：省略的 (You)
    return roles, passive, has_expl


# ---------- 比對 ----------
def chunk_spans(sentence, chunks):
    """找出每個標準答案片段在句子中的字元位置"""
    spans, pos = [], 0
    for c in chunks:
        if c["text"] == "(You)":
            spans.append(None)
            continue
        start = sentence.index(c["text"], pos)
        spans.append((start, start + len(c["text"])))
        pos = start + len(c["text"])
    return spans


def strip_span(sentence, span):
    a, b = span
    while b > a and sentence[b - 1] in " .,?!":
        b -= 1
    return a, b


def evaluate(name, analyze):
    """analyze(sentence) → (tokens[(start,end,head_index)], roles, pattern, constituents or None)"""
    role_ok = role_total = pat_ok = 0
    bnd_ok = bnd_total = 0
    per_role = defaultdict(lambda: [0, 0])
    errors = []
    t0 = time.perf_counter()
    for item in GOLD:
        s = item["sentence"]
        tokens, roles, pattern, consts = analyze(s)
        spans = chunk_spans(s, item["chunks"])
        pat_ok += pattern == item["pattern"]
        if pattern != item["pattern"]:
            errors.append(f"  #{item['id']} 句型：答案 {item['pattern']}，程式 {pattern}　{s}")
        for c, sp in zip(item["chunks"], spans):
            if c["role"] == "M":
                pass
            else:
                role_total += 1
                per_role[c["role"]][1] += 1
                if sp is None:  # (You)：程式要自己發現「沒有主詞、動詞是原形」的祈使句
                    pred = roles.get(-1)
                else:
                    idx = [k for k, (a, b, h) in enumerate(tokens) if a >= sp[0] and b <= sp[1]]
                    heads = [k for k in idx if tokens[k][2] not in idx]
                    pred = roles.get(heads[0]) if heads else None
                if pred == c["role"]:
                    role_ok += 1
                    per_role[c["role"]][0] += 1
                else:
                    errors.append(f"  #{item['id']} 「{c['text']}」答案 {c['role']}，程式 {pred}")
            if consts is not None and sp is not None:
                bnd_total += 1
                bnd_ok += strip_span(s, sp) in consts
    secs = time.perf_counter() - t0
    return {
        "name": name,
        "role": (role_ok, role_total),
        "pattern": (pat_ok, len(GOLD)),
        "boundary": (bnd_ok, bnd_total) if bnd_total else None,
        "per_role": dict(per_role),
        "errors": errors,
        "secs": secs,
    }


def make_spacy(model, with_benepar):
    import spacy

    nlp = spacy.load(model)
    if with_benepar:
        import benepar  # noqa: F401

        nlp.add_pipe("benepar", config={"model": "benepar_en3"})

    def analyze(s):
        doc = nlp(s)
        tokens = [(t.idx, t.idx + len(t.text), t.head.i if t.head.i != t.i else -1) for t in doc]
        roles, passive, expl = spacy_roles(doc)
        pattern = finish(roles, passive, expl)
        consts = None
        if with_benepar:
            consts = {strip_span(s, (c.start_char, c.end_char)) for c in list(doc.sents)[0]._.constituents}
        return tokens, roles, pattern, consts

    return analyze


def make_stanza():
    import stanza

    nlp = stanza.Pipeline("en", processors="tokenize,pos,lemma,depparse,constituency", verbose=False)

    def analyze(s):
        sent = nlp(s).sentences[0]
        tokens = []
        for w in sent.words:
            tok = w.parent
            tokens.append((tok.start_char, tok.end_char, w.head - 1 if w.head else -1))
        roles, passive, expl = stanza_roles(sent)
        pattern = finish(roles, passive, expl)
        # 片語結構：算出每個片語的字元範圍
        consts, leaves = set(), [(t[0], t[1]) for t in tokens]
        counter = [0]

        def walk(node):
            if not node.children:
                i = counter[0]
                counter[0] += 1
                return leaves[i]
            spans = [walk(ch) for ch in node.children]
            span = (spans[0][0], spans[-1][1])
            consts.add(strip_span(s, span))
            return span

        walk(sent.constituency)
        return tokens, roles, pattern, consts

    return analyze


if __name__ == "__main__":
    runs = [
        ("spaCy 小型", lambda: make_spacy("en_core_web_sm", False)),
        ("spaCy 大型", lambda: make_spacy("en_core_web_trf", False)),
        ("spaCy 大型＋benepar", lambda: make_spacy("en_core_web_trf", True)),
        ("Stanza", make_stanza),
    ]
    results = []
    for name, factory in runs:
        results.append(evaluate(name, factory()))
    pct = lambda a, b: f"{a}/{b}（{100 * a / b:.0f}%）"
    print("\n## 總表\n")
    print("| 分析程式 | 主幹角色 | 句型 | 片語邊界 | 44 句總時間 |")
    print("|---|---|---|---|---|")
    for r in results:
        b = pct(*r["boundary"]) if r["boundary"] else "（不支援）"
        print(f"| {r['name']} | {pct(*r['role'])} | {pct(*r['pattern'])} | {b} | {r['secs']:.1f} 秒 |")
    print("\n## 各角色正確率\n")
    all_roles = ["S", "Vi", "Vt", "V", "aux", "O", "IO", "DO", "SC", "OC"]
    print("| 分析程式 | " + " | ".join(all_roles) + " |")
    print("|---" * (len(all_roles) + 1) + "|")
    for r in results:
        cells = [f"{r['per_role'].get(x, [0, 0])[0]}/{r['per_role'].get(x, [0, 0])[1]}" for x in all_roles]
        print(f"| {r['name']} | " + " | ".join(cells) + " |")
    for r in results:
        print(f"\n## 錯誤明細：{r['name']}（{len(r['errors'])} 項）\n")
        print("\n".join(r["errors"]) or "  （無）")
