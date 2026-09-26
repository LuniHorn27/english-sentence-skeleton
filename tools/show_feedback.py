"""列出使用者回饋（data/feedback.jsonl）。

用法：.venv/bin/python tools/show_feedback.py
確認是分析錯誤後，把句子加進題庫（tests/practice/），修正規則，再跑測試。
"""
import json
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "data" / "feedback.jsonl"
if not path.exists():
    print("目前還沒有回饋。")
else:
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        r = json.loads(line)
        kind = "回報錯誤" if r["kind"] == "error" else "建議"
        print(f"\n#{i}　{r['time']}　{kind}")
        if r.get("sentence"):
            print(f"  句子：{r['sentence']}")
        if r.get("part"):
            print(f"  哪裡：{r['part']}（目前：{r.get('current') or '—'}）")
        print(f"  內容：{r['message']}")
