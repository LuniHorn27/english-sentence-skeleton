"""產生查單字用的小字典（backend/dictionary.json）。

來源：ECDICT（MIT 授權，授權條款見 backend/analyzer/LICENSE-ECDICT.txt），完整版放在 data/ecdict/ecdict.csv（不上傳）。
做法：
- 只收常用字：有詞頻排名（前 4 萬）或屬於國中、高中、大學考試字彙
- 中文意思轉成繁體（OpenCC s2tw：只轉字形、不改詞，避免「支持不住」被改成「支援不住」），
  去掉「[網路]」「[醫]」這類專業用法；每個字最多 3 種詞性、每種詞性最多 4 個意思
- 記下動詞、名詞的變化形（gave → give、boys → boy），查不到原字時改查原形；
  有自己意思的變化形兩個都列（saw：鋸子，也是 see 的過去式）

用法：.venv/bin/python tools/build_dictionary.py
"""
import csv
import json
import re
import sys
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ecdict" / "ecdict.csv"
OUT = ROOT / "backend" / "dictionary.json"
RANK_LIMIT = 40000
EXAM_TAGS = {"zk", "gk", "cet4", "cet6", "ky"}  # 中考、高考、大學四六級、考研
FORM_KEYS = "pdi3srt"  # 過去式、過去分詞、現在分詞、第三人稱、複數、比較級、最高級
ONLY_FORM = re.compile(r"(的過去式|的過去分詞|的現在分詞|的第三人稱|的複數|的比較級|的最高級)")

# 複數時意思和單數不一樣的常見字
SPECIAL_PLURALS = {
    "glasses", "clothes", "goods", "arms", "manners", "customs", "spectacles", "trousers", "jeans", "pants",
    "scissors", "savings", "earnings", "belongings", "surroundings", "directions", "remains", "contents",
    "stairs", "thanks", "headquarters", "looks", "papers", "works", "grounds", "letters", "airs", "spirits",
    "quarters", "sands", "waters", "shorts", "greens", "odds", "wages", "outskirts", "congratulations",
}
cc = OpenCC("s2tw")
csv.field_size_limit(sys.maxsize)


def short_meaning(translation: str) -> str:
    lines = []
    raw = [x.strip() for x in translation.replace("\\n", "\n").split("\n")]
    has_pos = any(re.match(r"^[a-z]+\.", x) and not x.startswith("abbr.") for x in raw)
    for line in raw:
        if not line or line.startswith("[") or line.startswith("abbr."):  # [网络]、[医]、縮寫
            continue
        if has_pos and not re.match(r"^[a-z]+\.", line):  # 沒有詞性的通常是縮寫或專業用語
            continue
        pos, _, rest = line.partition(" ") if re.match(r"^[a-z]+\.", line) else ("", "", line)
        senses = [x.strip() for x in re.split(r"[,，;；]", rest) if x.strip()][:4]
        lines.append((pos + " " if pos else "") + "、".join(senses))
        if len(lines) == 3:
            break
    return cc.convert("；".join(lines))


def main():
    words, forms = {}, {}
    with SRC.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = row["word"]
            if not re.fullmatch(r"[a-z][a-z'-]*", w) or not row["translation"]:
                continue
            ranks = [int(x) for x in (row["frq"], row["bnc"]) if x and x != "0"]
            tags = set(row["tag"].split())
            if not (tags & EXAM_TAGS or (ranks and min(ranks) <= RANK_LIMIT)):
                continue
            meaning = short_meaning(row["translation"])
            if not meaning:
                continue
            words[w] = {"p": row["phonetic"], "m": meaning}
            for part in row["exchange"].split("/"):
                if len(part) > 2 and part[1] == ":" and part[0] in FORM_KEYS:
                    forms.setdefault(part[2:], (w, part[0]))
    # 第二輪：複數時意思不一樣的字（人工列出），即使本身不常用也收進來（glasses：眼鏡，不是玻璃）
    # 其他不常用的變化形一律查原形；ECDICT 裡這些字常常只有縮寫或罕見意思（cats、dogs、books）
    with SRC.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = row["word"]
            if w in SPECIAL_PLURALS and w in forms and w not in words and row["translation"]:  # noqa: E501
                meaning = short_meaning(row["translation"])
                if meaning:
                    words[w] = {"p": row["phonetic"], "m": meaning}
    # 只是變化形的字（例如 gave：「give 的過去式」）改成指向原形；
    # 有自己意思的變化形（例如 glasses：眼鏡）保留自己的意思，只去掉「…的複數」這類說明
    base = {}
    for f, (b, kind) in forms.items():
        if b not in words:
            continue
        if f not in words or (kind == "s" and f not in SPECIAL_PLURALS):  # dogs、cats 一律查單數
            base[f] = b
            continue
        # 一個一個意思檢查，只去掉「…的複數」這類說明，其他意思保留
        lines = []
        for line in words[f]["m"].split("；"):
            pos, _, rest = line.partition(" ") if re.match(r"^[a-z]+\.", line) else ("", "", line)
            senses = [x for x in rest.split("、") if x and not ONLY_FORM.search(x)]
            if senses:
                lines.append((pos + " " if pos else "") + "、".join(senses))
        if lines:
            words[f]["m"] = "；".join(lines)
            words[f]["b"] = b  # 也是 b 的變化形（saw 也是 see 的過去式）
        else:
            base[f] = b
    for f in base:
        words.pop(f, None)
    OUT.write_text(json.dumps({"words": words, "forms": base}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(words)} 個字、{len(base)} 個變化形 → {OUT}（{OUT.stat().st_size / 1e6:.1f} MB）")


if __name__ == "__main__":
    main()
