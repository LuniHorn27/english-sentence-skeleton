"""小模型跟大模型學（二）：用大型模型的分析結果，繼續訓練小型模型。

從 en_core_web_sm 現有的程度出發，只訓練「字的特徵」「詞性」「句子結構」三部分（tok2vec、tagger、parser）；
人名地名辨識（ner，有自己獨立的特徵）、詞性對照規則、原形規則都不動。
訓練出來的模型大小跟原本的小型模型一樣，一樣不需要 PyTorch。

用法（小型模型的環境即可，不需要 PyTorch）：
  python tools/distill_train.py [輪數] [學習速度]
輸入：data/distill/train*.spacy、dev.spacy（tools/distill_make_data.py 產生）
輸出：models/en_core_web_sm_distilled/（驗證分數最好的那一輪；models/ 不上傳）
"""
import random
import sys
import time
import warnings
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from spacy.training import Example
from spacy.util import compounding, minibatch

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "distill"
OUT = ROOT / "models" / "en_core_web_sm_distilled"
FROZEN = ["attribute_ruler", "lemmatizer", "ner"]  # 不訓練（存檔時仍保留，才不會少了原形、人名地名）


def load_examples(nlp, name):
    """name 是 train 時，所有 train*.spacy（加過的教材）都一起讀"""
    files = sorted(DATA.glob("train*.spacy")) if name == "train" else [DATA / f"{name}.spacy"]
    return [Example(nlp.make_doc(d.text), d) for f in files for d in DocBin().from_disk(f).get_docs(nlp.vocab)]


def scores(nlp, examples):
    s = nlp.evaluate(examples)
    return {"詞性": s["tag_acc"], "結構（連到哪個字）": s["dep_uas"], "結構（含關係名稱）": s["dep_las"]}


def show(label, s):
    print(f"{label}：" + "、".join(f"{k} {100 * v:.1f}%" for k, v in s.items()), flush=True)


def main():
    warnings.filterwarnings("ignore")
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    lr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0005
    nlp = spacy.load("en_core_web_sm")
    train, dev = load_examples(nlp, "train"), load_examples(nlp, "dev")
    print(f"訓練 {len(train):,} 句、驗證 {len(dev):,} 句；{epochs} 輪、學習速度 {lr}", flush=True)
    best = scores(nlp, dev)
    show("訓練前（原本的小型模型，跟大型模型比）", best)
    best_las = best["結構（含關係名稱）"]

    random.seed(0)
    optimizer = nlp.resume_training()
    optimizer.learn_rate = lr
    for epoch in range(1, epochs + 1):
        random.shuffle(train)
        losses, t0 = {}, time.time()
        for batch in minibatch(train, size=compounding(16.0, 128.0, 1.001)):
            nlp.update(batch, sgd=optimizer, drop=0.1, losses=losses, exclude=FROZEN)
        s = scores(nlp, dev)
        show(f"第 {epoch} 輪（{time.time() - t0:.0f} 秒）", s)
        if s["結構（含關係名稱）"] > best_las:
            best_las = s["結構（含關係名稱）"]
            nlp.to_disk(OUT)
            print(f"  → 目前最好，存到 {OUT.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
