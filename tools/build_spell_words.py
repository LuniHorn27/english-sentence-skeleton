"""產生拼字檢查用的字表（分析時提醒「是不是打錯字？」）。

- backend/analyzer/spell_known.txt.gz：ECDICT 裡所有的英文字和變化形（約 37 萬個），用來判斷「這是不是一個真的字」，
  收得很寬，罕見字才不會被誤認成打錯。
- backend/analyzer/spell_rank.json：常用字和它們的變化形 → 常用程度排名，用來挑「最可能想打的字」。
來源：ECDICT（MIT 授權）。用法：.venv/bin/python tools/build_spell_words.py
"""
import csv
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ecdict" / "ecdict.csv"
KNOWN = ROOT / "backend" / "analyzer" / "spell_known.txt.gz"
RANK = ROOT / "backend" / "analyzer" / "spell_rank.json"
WORD = re.compile(r"[a-z][a-z'-]*")


def main():
    known, rank = set(), {}
    with SRC.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = row["word"]
            if not WORD.fullmatch(w):
                continue
            forms = [w] + [p[2:] for p in row["exchange"].split("/") if len(p) > 2 and p[1] == ":" and WORD.fullmatch(p[2:])]
            known.update(forms)
            ranks = [int(x) for x in (row["frq"], row["bnc"]) if x and x != "0"]
            if ranks or row["tag"]:
                r = min(ranks) if ranks else 60000
                for x in forms:
                    rank[x] = min(rank.get(x, r), r)
    with gzip.open(KNOWN, "wt", encoding="utf-8") as f:
        f.write("\n".join(sorted(known)))
    RANK.write_text(json.dumps(rank, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"認得的字 {len(known)} 個、常用字 {len(rank)} 個")


if __name__ == "__main__":
    main()
