"""0-1 冒煙測試：確認每個分析程式都能載入並分析句子，順便量載入與分析時間。"""
import time
import warnings

warnings.filterwarnings("ignore")

SENTENCE = "The teacher showed us a picture."


def timed(label, fn):
    t = time.perf_counter()
    try:
        result = fn()
        print(f"  {label}：{time.perf_counter() - t:.2f} 秒")
        return result
    except Exception as e:  # 冒煙測試：記錄失敗原因即可
        print(f"  {label}：失敗 → {type(e).__name__}: {e}")
        return None


def spacy_test(model, with_benepar=False):
    import spacy

    name = model + (" + benepar" if with_benepar else "")
    print(f"\n[{name}]")

    def load():
        nlp = spacy.load(model)
        if with_benepar:
            import benepar  # noqa: F401  註冊 spaCy 元件

            nlp.add_pipe("benepar", config={"model": "benepar_en3"})
        return nlp

    nlp = timed("載入", load)
    if nlp is None:
        return
    doc = timed("分析一句", lambda: nlp(SENTENCE))
    if doc is None:
        return
    print("  依附關係：", " ".join(f"{t.text}/{t.dep_}→{t.head.text}" for t in doc))
    if with_benepar:
        print("  片語結構：", list(doc.sents)[0]._.parse_string)


def stanza_test():
    import stanza

    print("\n[Stanza]")
    nlp = timed(
        "載入",
        lambda: stanza.Pipeline(
            "en",
            processors="tokenize,pos,lemma,depparse,constituency",
            verbose=False,
        ),
    )
    if nlp is None:
        return
    doc = timed("分析一句", lambda: nlp(SENTENCE))
    if doc is None:
        return
    s = doc.sentences[0]
    words = s.words
    print(
        "  依附關係：",
        " ".join(
            f"{w.text}/{w.deprel}→{words[w.head - 1].text if w.head else 'ROOT'}"
            for w in words
        ),
    )
    print("  片語結構：", s.constituency)


if __name__ == "__main__":
    spacy_test("en_core_web_sm")
    spacy_test("en_core_web_trf")
    spacy_test("en_core_web_sm", with_benepar=True)
    stanza_test()
