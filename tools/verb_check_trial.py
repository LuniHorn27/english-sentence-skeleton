"""動詞句型字典試跑：拿大量句子跑分析程式，看字典會標出多少「不確定」。

句子來源（都放在 data/，不進版本控制）：
  - VerbNet 3.4 附的例句（data/verbnet/）
  - Tatoeba 英文句子隨機抽樣（CC BY 2.0 FR，data/tatoeba/eng_sentences.tsv.bz2）
    https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2

用法：
  python tools/verb_check_trial.py [抽樣句數，預設 3000]
輸出：
  data/verb_check_trial.jsonl   每一句的結果（被標出來的才有 doubt）
"""
import bz2
import json
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.analyzer.engine import analyze_sentence  # noqa: E402

VERBNET_DIR = ROOT / "data/verbnet/verbnet3.4"
TATOEBA = ROOT / "data/tatoeba/eng_sentences.tsv.bz2"
OUT = ROOT / "data/verb_check_trial.jsonl"


def verbnet_examples():
    seen = set()
    for path in sorted(VERBNET_DIR.glob("*.xml")):
        for ex in ET.parse(path).getroot().iter("EXAMPLE"):
            s = " ".join((ex.text or "").split())
            if s and s not in seen and re.fullmatch(r"[A-Z][A-Za-z ,'\-]+[.!?]", s):
                seen.add(s)
                yield s


def tatoeba_sample(n, seed=20260927):
    pool = []
    with bz2.open(TATOEBA, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            s = parts[2]
            words = s.split()
            if 4 <= len(words) <= 15 and re.fullmatch(r"[A-Z][A-Za-z0-9 ,'\-]+[.!?]", s):
                pool.append(s)
    random.Random(seed).shuffle(pool)
    return pool[:n]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    items = [("verbnet", s) for s in verbnet_examples()] + [("tatoeba", s) for s in tatoeba_sample(n)]
    print(f"共 {len(items)} 句", flush=True)
    t0 = time.time()
    with OUT.open("w", encoding="utf-8") as out:
        for k, (src, s) in enumerate(items, 1):
            try:
                r = analyze_sentence(s)
            except Exception as e:  # 分析程式當掉也記下來
                out.write(json.dumps({"src": src, "text": s, "crash": repr(e)}, ensure_ascii=False) + "\n")
                continue
            clauses = [{"label": c.label, "verb": c.verb, "doubt": c.doubt} for c in r.clauses]
            chunks = " ".join(f"[{c.role} {c.text}]" for c in r.chunks)
            out.write(json.dumps({"src": src, "text": s, "status": r.status, "clauses": clauses, "chunks": chunks},
                                 ensure_ascii=False) + "\n")
            if k % 500 == 0:
                print(f"{k} 句，{time.time() - t0:.0f} 秒", flush=True)
    print("完成", flush=True)


if __name__ == "__main__":
    main()
