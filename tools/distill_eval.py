"""小模型跟大模型學（三）：檢查訓練出來的小型模型。

1. 三套題庫（練習、考試、體檢）和標準答案比，看錯幾句
2. 從沒拿來訓練的 1,000 句 Tatoeba（heldout.txt），整套分析結果跟大型模型比，看有幾句不同
3. 記憶體最高用多少

用法：
  先產生大型模型的答案（一次就好，要有大型模型的環境）：
    .venv/bin/python tools/distill_eval.py --teacher
  再檢查任一個小型模型（模型名稱或資料夾）：
    python tools/distill_eval.py en_core_web_sm
    python tools/distill_eval.py models/en_core_web_sm_distilled
"""
import json
import os
import resource
import sys
import warnings
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "distill"
TEACHER = DATA / "heldout_trf.json"


def summary(res):
    """整套分析結果中，拿來比較的部分：句型、狀態、每個片段的位置和標籤"""
    return {"pat": [[c.pattern, c.passive] for c in res.clauses], "status": res.status,
            "chunks": [[c.start, c.end, c.role, c.function] for c in res.chunks if not c.implicit]}


def main():
    warnings.filterwarnings("ignore")
    teacher_mode = sys.argv[1] == "--teacher"
    os.environ["SPACY_MODEL"] = "en_core_web_trf" if teacher_mode else sys.argv[1]
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    from backend.analyzer.engine import analyze_sentence

    heldout = (DATA / "heldout.txt").read_text(encoding="utf-8").splitlines()
    if teacher_mode:
        TEACHER.write_text(json.dumps([summary(analyze_sentence(s)) for s in heldout], ensure_ascii=False), encoding="utf-8")
        print(f"存好大型模型的答案：{TEACHER.relative_to(ROOT)}")
        return

    import run_tests
    print(f"# {sys.argv[1]}")
    for name, label in (("practice", "練習題"), ("exam", "考試題"), ("probe", "體檢題")):
        items = yaml.safe_load((ROOT / "tests" / name / "gold.yaml").read_text(encoding="utf-8"))
        stats, _, lines, _ = run_tests.evaluate(items)
        bad = sum(1 for l in lines if l.startswith("\n"))
        a, b = stats["句型"]
        print(f"{label}：{len(items)} 句錯 {bad} 句；句型 {a}/{b}")

    teacher = json.loads(TEACHER.read_text(encoding="utf-8"))
    diff = pat = 0
    for s, t in zip(heldout, teacher):
        mine = summary(analyze_sentence(s))
        diff += mine != t
        pat += mine["pat"] != t["pat"] or mine["status"] != t["status"]
    n = len(heldout)
    print(f"沒看過的 {n} 句，跟大型模型比：有任何不同 {diff} 句（{100 * diff / n:.1f}%），句型或狀態不同 {pat} 句（{100 * pat / n:.1f}%）")
    print(f"記憶體最高：{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024:.0f} MB")


if __name__ == "__main__":
    main()
