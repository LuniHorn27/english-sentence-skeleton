"""自動測試（1-3）：把題庫丟進分析引擎，和標準答案比對。

用法：
  python tests/run_tests.py            # 練習題
  python tests/run_tests.py --exam     # 考試題（1-9 才用）

報告同時存成 tests/report_practice.md（或 report_exam.md）。
"""
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.analyzer.engine import analyze_sentence  # noqa: E402

CORE = {"S", "Vt", "Vi", "V", "aux", "O", "IO", "DO", "SC", "OC"}


def norm_span(text, start, end):
    """去掉片段頭尾的空白和標點，方便比對範圍"""
    while end > start and text[end - 1] in " .,?!;:":
        end -= 1
    while start < end and text[start] in " ,":
        start += 1
    return start, end


def gold_spans(item):
    s, pos, out = item["sentence"], 0, []
    for c in item["chunks"]:
        if c["text"] == "(You)":
            out.append((c, None))
            continue
        start = s.index(c["text"], pos)
        pos = start + len(c["text"])
        out.append((c, norm_span(s, start, pos)))
    return out


def evaluate(items):
    stats = defaultdict(lambda: [0, 0])  # 項目 → [對, 總]
    per_role = defaultdict(lambda: [0, 0])
    lines = []
    t0 = time.perf_counter()
    for item in items:
        s = item["sentence"]
        res = analyze_sentence(s)
        pred = {}
        implicit = None
        for c in res.chunks:
            if c.implicit:
                implicit = c
            else:
                pred[norm_span(s, c.start, c.end)] = c
        errs = []

        # 句型
        ppat = res.clauses[0].pattern if res.clauses else None
        ppas = res.clauses[0].passive if res.clauses else None
        ok = ppat == item["pattern"] and bool(ppas) == bool(item["passive"])
        stats["句型"][0] += ok
        stats["句型"][1] += 1
        if not ok:
            errs.append(f"句型：答案 {item['pattern']}{'（被動）' if item['passive'] else ''}，程式 {ppat}{'（被動）' if ppas else ''}")

        for g, span in gold_spans(item):
            role = g["role"]
            if span is None:
                p = implicit
            else:
                p = pred.get(span)
            label = f"「{g['text']}」"
            # 片段範圍
            stats["片段範圍"][1] += 1
            if p is not None:
                stats["片段範圍"][0] += 1
            elif span is not None:
                cover = [c for sp, c in pred.items() if sp[0] < span[1] and sp[1] > span[0]]
                errs.append(f"{label} 範圍不同，程式切成：{' ／ '.join(c.text for c in cover) or '（沒有）'}")

            if role in CORE:
                stats["主幹角色"][1] += 1
                per_role[role][1] += 1
                got = p.role if p else None
                if got is None and span is not None:
                    # 範圍不同時，看包含這段文字核心的片段角色
                    cover = [c for sp, c in pred.items() if sp[0] <= span[0] < sp[1]]
                    got = cover[0].role if cover else None
                if got == role:
                    stats["主幹角色"][0] += 1
                    per_role[role][0] += 1
                elif p is not None or got is not None:
                    errs.append(f"{label} 角色：答案 {role}，程式 {got}")
            elif role in ("conj", "RS"):
                ok = p is not None and p.role == role
                stats["主幹角色"][1] += 1
                stats["主幹角色"][0] += ok
                if p is not None and not ok:
                    errs.append(f"{label} 角色：答案 {role}，程式 {p.role}")
            else:
                stats["修飾語功能"][1] += 1
                want = g["function"] + (g["modifies"] or "")
                got = (p.function + (p.modifies.text if p.modifies else "")) if p and p.function else None
                if p is not None and got == want:
                    stats["修飾語功能"][0] += 1
                elif p is not None:
                    errs.append(f"{label} 功能：答案 {want}，程式 {got or p.role}")

            if g.get("head") and p is not None:
                stats["核心字"][1] += 1
                got_heads = [h.text for h in p.heads]
                if got_heads == g["head"]:
                    stats["核心字"][0] += 1
                else:
                    errs.append(f"{label} 核心字：答案 {'、'.join(g['head'])}，程式 {'、'.join(got_heads) or '（無）'}")

        if res.status != "ok":
            errs.append(f"狀態：{res.status}（{res.message}）")
        if errs:
            lines.append(f"\n**#{item['id']}** {s}")
            lines.extend(f"- {e}" for e in errs)
    secs = time.perf_counter() - t0
    return stats, per_role, lines, secs


def main():
    exam = "--exam" in sys.argv
    name = "exam" if exam else "practice"
    items = yaml.safe_load((ROOT / "tests" / name / "gold.yaml").read_text(encoding="utf-8"))
    stats, per_role, lines, secs = evaluate(items)
    pct = lambda a, b: f"{a}/{b}（{100 * a / b:.0f}%）" if b else "—"
    out = [f"# 測試報告：{'考試題' if exam else '練習題'}（{len(items)} 句，{secs:.1f} 秒）", "",
           "| 項目 | 正確率 |", "|---|---|"]
    for k in ["主幹角色", "句型", "修飾語功能", "片段範圍", "核心字"]:
        out.append(f"| {k} | {pct(*stats[k])} |")
    roles = ["S", "Vt", "Vi", "V", "aux", "O", "IO", "DO", "SC", "OC"]
    out += ["", "| " + " | ".join(roles) + " |", "|" + "---|" * len(roles),
            "| " + " | ".join(f"{per_role[r][0]}/{per_role[r][1]}" for r in roles) + " |",
            "", f"## 錯誤明細（{sum(1 for l in lines if l.startswith(chr(10)))} 句有錯）"]
    out += lines or ["", "（全部正確）"]
    report = "\n".join(out)
    (ROOT / "tests" / f"report_{name}.md").write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
