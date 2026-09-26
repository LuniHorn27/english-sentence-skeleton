"""把題庫 Markdown（人看的版本）轉成 YAML（程式讀的版本）。

用法：python tests/md_to_yaml.py tests/practice/題庫草稿-v3.md tests/practice/gold.yaml

Markdown 每一列的格式：
| 編號 | 句子 | `[S The cat 核心:cat] [Vi sleeps] [M 副詞・表地點 on the sofa]` 其他說明 → 句型一 | 審核意見 |
"""
import re
import sys

import yaml

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
CORE_ROLES = {"S", "Vi", "Vt", "V", "aux.", "O", "IO", "DO", "SC", "OC"}


def parse_chunk(raw):
    """'M 形容詞・修飾tree behind our house' → dict"""
    head = None
    m = re.search(r"\s核心:(\S+(?:, \S+)*)$", raw)
    if m:
        head = [h.strip() for h in m.group(1).split(",")]
        raw = raw[: m.start()]
    role, _, rest = raw.partition(" ")
    if role == "M":
        func, _, text = rest.partition(" ")
        target = None
        if "・修飾" in func:
            func, target = func.split("・修飾")
            func += "・修飾"
        return {"role": "M", "function": func, "modifies": target, "text": text}
    if role not in CORE_ROLES:
        raise ValueError(f"不認得的角色：{role}（{raw}）")
    chunk = {"role": role.rstrip("."), "text": rest}
    if head:
        chunk["head"] = head
    return chunk


def convert(md_text):
    items, section_pattern = [], None
    for line in md_text.splitlines():
        sec = re.match(r"^## .*?句型([一二三四五])", line)
        if sec:
            section_pattern = CN_NUM[sec.group(1)]
        elif line.startswith("## "):
            section_pattern = None
        row = re.match(r"^\| (E?\d+) \| (.+?) \| `(.+?)`(.*?)\|", line)
        if not row:
            continue
        num, sentence, chunks_md, note = row.groups()
        explicit = re.search(r"句型([一二三四五])", note)
        pattern = CN_NUM[explicit.group(1)] if explicit else section_pattern
        items.append(
            {
                "id": num,
                "sentence": sentence.strip(),
                "pattern": pattern,
                "passive": "被動語態" in note,
                "chunks": [parse_chunk(c) for c in re.findall(r"\[([^\]]+)\]", chunks_md)],
            }
        )
    return items


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    data = convert(open(src, encoding="utf-8").read())
    with open(dst, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=200)
    print(f"轉換 {len(data)} 句 → {dst}")
