"""穩定性測試：題庫以外的句子、奇怪的輸入，確認不會當掉，並印出簡要結果給人檢查。

用法：python tests/robustness.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.analyzer.engine import analyze_sentence  # noqa: E402

SENTENCES = [
    # 規格書有定義、但題庫沒有的句型
    "I like tea, but she likes coffee.",
    "She was tired, so she went to bed early.",
    "Because it was raining, we stayed at home.",
    "We stayed at home because it was raining.",
    "Although he was tired, he kept working.",
    "Swimming is fun.",
    "It is hard to learn English.",
    "There are many books on the shelf.",
    "Don't touch the hot stove.",
    "Are you ready?",
    "Does your brother play the piano?",
    "The book that I bought yesterday is interesting.",
    "My father has worked at this company for ten years.",
    "The letter was written by my grandmother.",
    "I went to the store to buy some milk.",
    # 還沒涵蓋（應該標未分析或提示）
    "What did you buy at the store?",
    "He gave up smoking last year.",
    "Walking to school, I saw a cat.",
    # 奇怪的輸入
    "Hello!",
    "a big red apple",
    "我喜歡你",
    "1234 5678",
    "<script>alert(1)</script>",
    "I like apples. She likes bananas.",
    "   run   ",
]


def show(res):
    parts = []
    for c in res.chunks:
        tag = c.function if c.role == "M" else c.role
        heads = f"＊{'、'.join(h.text for h in c.heads)}" if c.heads else ""
        parts.append(f"[{tag} {c.text}{heads}]")
    head = res.header if res.clauses else "（無句型）"
    cards = ", ".join(r.id for r in res.cards)
    return f"{head}｜{res.status}{'：' + res.message if res.message else ''}\n    {' '.join(parts)}\n    卡片：{cards or '無'}"


if __name__ == "__main__":
    ok = True
    for s in SENTENCES:
        t = time.perf_counter()
        try:
            res = analyze_sentence(s)
            print(f"\n{s}\n  {show(res)}　（{time.perf_counter() - t:.2f} 秒）")
        except Exception as e:  # 任何例外都算失敗
            ok = False
            print(f"\n{s}\n  ✗ 當掉：{type(e).__name__}: {e}")
    sys.exit(0 if ok else 1)
