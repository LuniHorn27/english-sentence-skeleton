"""檢查示範分析結果和文法重點卡是否符合資料格式（0-5）。

用法：python tests/validate_formats.py
"""
import json
import string
import sys
from pathlib import Path

import yaml

sys.path.insert(0, "backend")
from analyzer.schema import AnalysisResult, Card  # noqa: E402

ok = True
cards = {}
for path in sorted(Path("backend/cards").glob("*.yaml")):
    try:
        card = Card(**yaml.safe_load(path.read_text(encoding="utf-8")))
        if card.id != path.stem:
            raise ValueError(f"檔名 {path.stem} 和 id {card.id} 不一致")
        cards[card.id] = card
        print(f"✓ 卡片 {path.name}")
    except Exception as e:
        ok = False
        print(f"✗ 卡片 {path.name}：{e}")

missing = set()
for path in sorted(Path("backend/samples").glob("*.json")):
    try:
        result = AnalysisResult(**json.loads(path.read_text(encoding="utf-8")))
        for sent in result.sentences:
            for ref in sent.cards:
                card = cards.get(ref.id)
                if card is None:
                    missing.add(ref.id)
                    continue
                needed = {f for _, f, _, _ in string.Formatter().parse(card.brief) if f}
                if needed - ref.vars.keys():
                    raise ValueError(f"卡片 {ref.id} 缺少變數 {needed - ref.vars.keys()}")
        print(f"✓ 示範結果 {path.name}")
    except Exception as e:
        ok = False
        print(f"✗ 示範結果 {path.name}：{e}")

if missing:
    print(f"\n（提醒）示範結果用到、但還沒寫的卡片：{', '.join(sorted(missing))}")
sys.exit(0 if ok else 1)
