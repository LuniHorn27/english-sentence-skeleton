"""幫小遊戲的題目產生中文翻譯草稿（backend/quiz_zh.yaml）。

用法：.venv/bin/python tools/make_quiz_zh.py
- 只翻「還沒有翻譯」的題目，已經有的（包含人工修正過的）不會被覆蓋。
- 用和網站相同的翻譯模型（Qwen3-4B）；翻完要人工檢查，錯的直接改 quiz_zh.yaml。
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import translate  # noqa: E402
from backend.analyzer.engine import analyze_text  # noqa: E402
from backend.analyzer.phrases import translation_hints  # noqa: E402

GOLD = ROOT / "tests" / "practice" / "gold.yaml"
OUT = ROOT / "backend" / "quiz_zh.yaml"


def main():
    items = yaml.safe_load(GOLD.read_text(encoding="utf-8"))
    done = yaml.safe_load(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    done = done or {}
    todo = [x["sentence"] for x in items if x["sentence"] not in done]
    if not todo:
        print("全部都有翻譯了。")
        return
    translate.load()
    for i, s in enumerate(todo, 1):
        phrases = [p.id for r in analyze_text(s) for p in r.phrases]
        done[s] = translate.translate(s, translation_hints(phrases))
        print(f"{i}/{len(todo)}  {s}\n        {done[s]}", flush=True)
    header = "# 小遊戲題目的中文翻譯（英文句子: 中文）。由 tools/make_quiz_zh.py 產生草稿，人工檢查過；錯的直接改這裡。\n"
    OUT.write_text(header + yaml.safe_dump(done, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    print(f"完成 → {OUT}")


if __name__ == "__main__":
    main()
