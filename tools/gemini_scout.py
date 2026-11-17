"""Gemini 抓錯助手：讓 Gemini 照〈標籤規則〉分析一批句子，和我們的分析程式比對，
只列出兩邊答案不同的句子給人判斷（我們錯 → 照 /fix 修；標法不同 → 待審核清單；Gemini 錯 → 略過）。

用法（在專案資料夾或 worktree 執行）：
  .venv/bin/python tools/gemini_scout.py                    # Tatoeba 新句子，累計到 80 句
  .venv/bin/python tools/gemini_scout.py --n 400 --batch 20 # 累計到 400 句，一次送 20 句
  .venv/bin/python tools/gemini_scout.py --file 文章.txt     # 使用者貼的文章（一行一句或整段都可以）
  .venv/bin/python tools/gemini_scout.py --n 296 --cached-only  # 額度用完時，只用已經問過的句子出報告
金鑰讀使用者家目錄的 .config/english-tool/gemini_api_key（不進 git）。
免費額度：gemini-3.5-flash 一天約 20 次請求（算次數不算句數），美西午夜（台灣下午 3 點左右）恢復。
Gemini 的回答存在 data/gemini_scout/（不上傳），用句子本身當代號，重跑不會重複呼叫；報告寫到同一個資料夾的 scout_report.md。
在 worktree 裡執行時，data/ 不在 worktree，請設定 ENGLISH_DATA=主資料夾的 data 路徑。
"""
import argparse
import bz2
import json
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
DATA = Path(os.environ.get("ENGLISH_DATA", ROOT / "data"))
OUT = DATA / "gemini_scout"

parser = argparse.ArgumentParser()
parser.add_argument("--n", type=int, default=80, help="Tatoeba 句子累計要比對幾句（已問過的也算在內）")
parser.add_argument("--model", default="gemini-3.5-flash")
parser.add_argument("--batch", type=int, default=8, help="一次請求送幾句（額度算次數，送多一點一天能問比較多）")
parser.add_argument("--file", help="改用這個檔案裡的句子（例如使用者貼的文章）")
parser.add_argument("--cached-only", action="store_true", help="只用已經問過的句子出報告，不再呼叫 Gemini")
ARGS = parser.parse_args()

# 借用比較工具的規則書提示、呼叫方式和格式清理（它在 import 時讀 sys.argv 的模型名稱）
sys.path.insert(0, str(Path(__file__).resolve().parent))
_argv, sys.argv = sys.argv, [sys.argv[0], ARGS.model]
import gemini_compare as gc  # noqa: E402
sys.argv = _argv
gc.BATCH = ARGS.batch
import run_tests  # noqa: E402  （gemini_compare 已經把 tests/ 放進路徑）
from backend.analyzer.engine import analyze_sentence, split_sentences  # noqa: E402
from backend.analyzer.schema import PATTERN_DISPLAY  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / f"scout_cache_{ARGS.model}.jsonl"
FORMULA = {1: "S + Vi", 2: "S + Vi + SC", 3: "S + Vt + O", 4: "S + Vt + O + OC", 5: "S + Vt + IO + DO"}


def pattern_label(internal, passive):
    if internal is None:
        return "（沒有句型）"
    d = PATTERN_DISPLAY[internal]
    return f"句型{'一二三四五'[d - 1]}{'（被動）' if passive else ''}：{FORMULA[d]}"


def known_sentences():
    out = set()
    for name in ("practice", "exam", "probe"):
        for it in run_tests.yaml.safe_load((ROOT / "tests" / name / "gold.yaml").read_text(encoding="utf-8")):
            out.add(it["sentence"].strip().lower())
    return out


def tatoeba_sentences(n, cached, cached_only):
    """抽 8～20 字、只有一般英文字和標點的句子；固定亂數種子，每次抽到的順序一樣。
    已經問過 Gemini 的句子一定保留（就算後來加進了題庫）；其他句子跳過題庫裡已有的。
    回傳 [(代號, 句子)]，代號是句子在亂數排列後語料裡的位置（P123），題庫怎麼變都不會錯位"""
    ok = re.compile(r"^[A-Z][A-Za-z ,']+[.?!]$")
    pool = []
    with bz2.open(DATA / "tatoeba" / "eng_sentences.tsv.bz2", "rt", encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n").split("\t")[-1].strip()
            if ok.match(s) and 8 <= len(s.split()) <= 20:
                pool.append(s)
    random.Random(20261007).shuffle(pool)
    seen, out = known_sentences(), []
    for i, s in enumerate(pool):
        if cached_only and s not in cached:
            continue
        if s in cached or s.lower() not in seen:
            seen.add(s.lower())
            out.append((f"P{i + 1}", s))
            if len(out) == n:
                break
    return out


def file_sentences(path):
    """檔案裡的句子：每行先用分析程式的斷句切開（整段文章也可以）"""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        out.extend(s for s in split_sentences(line) if re.search(r"[A-Za-z]{2,}", s))
    return [(f"F{i + 1}", s) for i, s in enumerate(dict.fromkeys(out))]


def gemini_as_gold(sentence, r, key):
    """Gemini 的回答 → 題庫答案的格式，給 run_tests.evaluate 當「答案」比對我們的程式"""
    g = gc.to_result(sentence, r)  # 已處理：找不到原文的片段丟掉、標籤格式清理
    alias = {"真主詞": "RS", "真受詞": "RO", "強調框架": "EF"}  # Gemini 偶爾用中文名稱
    # 片段照位置排好，去掉和前一段重疊的（Gemini 偶爾重複或亂序，評分程式要求依序不重疊）
    ordered, last_end = [], -1
    for c in sorted(g.chunks, key=lambda c: (c.start, c.end)):
        if c.implicit or c.start >= last_end:
            ordered.append(c)
            last_end = max(last_end, c.end)
    chunks = []
    for c in ordered:
        c.role = alias.get(c.role, c.role)
        d = {"role": c.role, "text": c.text}
        if c.role == "M":
            d["function"] = c.function or ""
            # 規則書只有形容詞修飾語要標被修飾的字；Gemini 有時其他修飾語也填，不算差異
            d["modifies"] = c.modifies.text if c.modifies and c.function == "形容詞・修飾" else None
        if c.heads:
            d["head"] = [h.text for h in c.heads]
        chunks.append(d)
    return {"id": key, "sentence": sentence, "pattern": g.clauses[0].pattern, "passive": g.clauses[0].passive, "chunks": chunks}


def ask(todo, cache):
    """沒問過的句子分批問 Gemini，每批的回答立刻存檔；額度用完就停下，用已有的回答出報告"""
    with CACHE.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), gc.BATCH):
            batch = todo[i:i + gc.BATCH]
            try:
                results, secs, _ = gc.call_gemini(batch)
            except Exception as e:
                print(f"停在第 {i} 句：{e}", flush=True)
                return
            got = {str(r.get("id")): r for r in results}
            for it in batch:
                r = got.get(it["key"]) or {"chunks": [], "pattern": None, "passive": False}
                r["id"] = it["sentence"]
                cache[it["sentence"]] = r
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            print(f"  {min(i + gc.BATCH, len(todo))}/{len(todo)}　{secs:.1f} 秒", flush=True)
            gc.time.sleep(4)


def main():
    cache = {}  # 句子 → Gemini 的回答
    if CACHE.exists():
        for line in CACHE.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            cache[r["id"]] = r
    if ARGS.file:
        source = f"檔案 {Path(ARGS.file).name}"
        items = [{"key": k, "sentence": s} for k, s in file_sentences(ARGS.file)]
    else:
        source = "Tatoeba 新句子"
        items = [{"key": k, "sentence": s} for k, s in tatoeba_sentences(ARGS.n, cache, ARGS.cached_only)]
    todo = [] if ARGS.cached_only else [it for it in items if it["sentence"] not in cache]
    print(f"{ARGS.model}：{len(items)} 句，要問 {len(todo)} 句（一次 {gc.BATCH} 句）", flush=True)
    ask(todo, cache)

    big, small, spans_only, same, skipped = [], [], 0, 0, 0
    for it in items:
        r = cache.get(it["sentence"])
        if not r or r.get("pattern") is None:
            skipped += 1
            continue
        gold = gemini_as_gold(it["sentence"], r, it["key"])
        if gold["pattern"] is None:
            skipped += 1
            continue
        try:
            _, _, lines, _ = run_tests.evaluate([gold])
        except ValueError:  # Gemini 的片段對不回原句
            skipped += 1
            continue
        errs = [l[2:] for l in lines if l.startswith("- ")]
        if not errs:
            same += 1
            continue
        res = analyze_sentence(it["sentence"])
        mine = res.clauses[0] if res.clauses else None
        out = []
        for e in errs:
            if e.startswith("句型："):
                e = (f"句型：Gemini {pattern_label(gold['pattern'], gold['passive'])}，"
                     f"我們 {pattern_label(mine.pattern if mine else None, mine.passive if mine else False)}")
            out.append(e.replace("答案", "Gemini").replace("程式", "我們"))
        core = any(e.startswith("句型") or "角色：" in e or e.startswith("狀態") for e in out)
        if not core and all("範圍不同" in e for e in out):
            spans_only += 1  # 只有切法習慣不同：Gemini 常這樣，不列出
            continue
        ours = " ".join(f"[{c.role}{' ' + c.function if c.function else ''} {c.text}]" for c in res.chunks)
        gem = " ".join(f"[{c['role']}{' ' + c['function'] if c.get('function') else ''} {c['text']}]" for c in gold["chunks"])
        block = [f"\n**{it['key']}** {it['sentence']}", *[f"- {e}" for e in out], f"  - 我們：{ours}", f"  - Gemini：{gem}"]
        (big if core else small).append("\n".join(block))

    report = [f"# Gemini 抓錯助手報告（{ARGS.model}，{source} {len(items)} 句）", "",
              f"兩邊一樣 {same} 句；只有片段切法不同 {spans_only} 句（不列）；"
              f"Gemini 沒回答 {skipped} 句；主幹或句型不同 {len(big)} 句；只有修飾語或核心字不同 {len(small)} 句。",
              "", "## 一、主幹或句型不同（優先看）", *big, "", "## 二、只有修飾語功能或核心字不同", *small]
    (OUT / "scout_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:3]))
    print(f"報告：{OUT / 'scout_report.md'}")


if __name__ == "__main__":
    main()
