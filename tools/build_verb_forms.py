"""產生動詞變化表 backend/analyzer/verb_forms.json：原形 → 過去式、過去分詞、第三人稱單數。

用途：分詞構句還原成完整句子時，把 surviving 改回 survived（照主要句子的時態）。
來源：ECDICT（MIT 授權）的 exchange 欄位；只收 backend/dictionary.json 裡有的字。
用法：.venv/bin/python tools/build_verb_forms.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ecdict" / "ecdict.csv"
OUT = ROOT / "backend" / "analyzer" / "verb_forms.json"


def main():
    known = set(json.loads((ROOT / "backend" / "dictionary.json").read_text(encoding="utf-8"))["words"])
    forms = {}
    with SRC.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = row["word"]
            if w not in known or not row["exchange"]:
                continue
            parts = dict(p.split(":", 1) for p in row["exchange"].split("/") if len(p) > 2 and p[1] == ":")
            entry = {k: parts[k] for k in ("p", "d", "3") if k in parts and parts[k].isalpha()}
            if "p" in entry:
                forms[w] = entry
    OUT.write_text(json.dumps(forms, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"{len(forms)} 個動詞 → {OUT}")


if __name__ == "__main__":
    main()
