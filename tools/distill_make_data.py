"""小模型跟大模型學（一）：用大型模型分析 Tatoeba 句子，當作訓練小型模型的教材。

做法：從 Tatoeba 英文句子隨機抽句子 → 大型模型（en_core_web_trf）分析詞性和句子結構 → 存成 spaCy 的訓練檔。
三套題庫（練習、考試、體檢）的句子一律排除，訓練時才不會「先看過考題」。
另外留一份從沒拿來訓練的句子（heldout.txt），最後用來比較新舊小模型和大模型差多少。

用法（要用有大型模型的環境）：
  .venv/bin/python tools/distill_make_data.py 60000
輸出：data/distill/train.spacy、dev.spacy、heldout.txt（data/ 不上傳）
Tatoeba 授權：CC BY 2.0 FR（https://tatoeba.org）
"""
import bz2
import random
import re
import sys
import warnings
from pathlib import Path

import spacy
import yaml
from spacy.tokens import DocBin

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "distill"
N_TRAIN = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
N_DEV, N_HELDOUT = 2000, 1000


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def main():
    warnings.filterwarnings("ignore")
    gold = {norm(i["sentence"]) for k in ("practice", "exam", "probe")
            for i in yaml.safe_load((ROOT / "tests" / k / "gold.yaml").read_text(encoding="utf-8"))}
    seen, pool = set(), []
    for line in bz2.open(ROOT / "data" / "tatoeba" / "eng_sentences.tsv.bz2", "rt", encoding="utf-8"):
        s = line.split("\t")[2].strip()
        key = norm(s)
        # 3～40 個字、完整句子（句號、問號、驚嘆號結尾）、不重複、不是題庫句子
        if 3 <= len(s.split()) <= 40 and s[-1:] in ".?!" and key not in seen and key not in gold:
            seen.add(key)
            pool.append(s)
    random.seed(20261006)
    picks = random.sample(pool, N_TRAIN + N_DEV + N_HELDOUT)
    heldout, dev, train = picks[:N_HELDOUT], picks[N_HELDOUT:N_HELDOUT + N_DEV], picks[N_HELDOUT + N_DEV:]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "heldout.txt").write_text("\n".join(heldout) + "\n", encoding="utf-8")
    print(f"可用句子 {len(pool):,}；訓練 {len(train):,}、驗證 {len(dev):,}、最後檢查 {len(heldout):,}")

    spacy.prefer_gpu()
    nlp = spacy.load("en_core_web_trf", disable=["ner", "lemmatizer"])
    for name, texts in (("dev", dev), ("train", train)):
        db = DocBin(attrs=["TAG", "POS", "HEAD", "DEP", "SENT_START"])
        for i, doc in enumerate(nlp.pipe(texts, batch_size=64)):
            db.add(doc)
            if (i + 1) % 5000 == 0:
                print(f"  {name}：{i + 1:,} 句", flush=True)
        db.to_disk(OUT / f"{name}.spacy")
        print(f"存好 {name}.spacy（{len(texts):,} 句）", flush=True)


if __name__ == "__main__":
    main()
