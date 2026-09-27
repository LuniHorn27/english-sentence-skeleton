"""列出使用者回饋。

本機的回饋：data/feedback.jsonl
網站上的回饋：存在 Hugging Face 的私人資料集，先下載到 data/feedback-online/ 再執行：
  .venv/bin/hf download <帳號>/english-sentence-skeleton-feedback --repo-type dataset --local-dir data/feedback-online

用法：.venv/bin/python tools/show_feedback.py
確認是分析錯誤後，把句子加進題庫（tests/practice/），修正規則，再跑測試。
"""
import json
from pathlib import Path

data = Path(__file__).resolve().parent.parent / "data"
files = [data / "feedback.jsonl", *sorted(data.glob("feedback/*.jsonl")), *sorted(data.glob("feedback-online/**/*.jsonl"))]
lines = [line for f in files if f.exists() for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
lines.sort(key=lambda line: json.loads(line)["time"])
if not lines:
    print("目前還沒有回饋。")
else:
    for i, line in enumerate(lines, 1):
        r = json.loads(line)
        kind = "回報錯誤" if r["kind"] == "error" else "建議"
        print(f"\n#{i}　{r['time']}　{kind}")
        if r.get("sentence"):
            print(f"  句子：{r['sentence']}")
        if r.get("part"):
            print(f"  哪裡：{r['part']}（目前：{r.get('current') or '—'}）")
        print(f"  內容：{r['message']}")
