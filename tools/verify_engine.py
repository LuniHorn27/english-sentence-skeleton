"""分析引擎一鍵驗證：三個模型 × 四套題，和基準比對，告訴你有沒有改壞。

給 /delegate 指令和修分析程式的人（或模型）用。在專案資料夾或 worktree 裡執行，
python 用主資料夾的 .venv（worktree 裡沒有 .venv 和 models，工具會自己找主資料夾）：

  <主資料夾>/.venv/bin/python tools/verify_engine.py                  # 全部驗證，和基準比對
  <主資料夾>/.venv/bin/python tools/verify_engine.py --save-baseline  # 把現在的結果存成基準（只在 main 上、修正合併後做）
  <主資料夾>/.venv/bin/python tools/verify_engine.py --only trf       # 只跑一個模型：trf／distilled／sm
  <主資料夾>/.venv/bin/python tools/verify_engine.py show "It started to rain." --deps
  <主資料夾>/.venv/bin/python tools/verify_engine.py show 句子檔.txt   # 一行一句；三個模型的分析結果並排

四套題：練習題、考試題、體檢題（tests/*/gold.yaml），和題庫以外的新測試句（docs/引擎檢查-新測試句.md）。
三個模型：trf＝大型（Mac 完整版）、distilled＝蒸餾版（Render 網站）、sm＝原本的小型（備援）。
基準存在 tests/engine_baseline.json：記錄每個模型目前「不通過」的句子。
判定：大型模型三套題要全對；任何模型「基準裡通過、現在不通過」就是退步。這個工具不會改動 tests/report_*.md。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tests" / "engine_baseline.json"
NEW_FILE = ROOT / "docs" / "引擎檢查-新測試句.md"
SUITES = {"practice": "練習題", "exam": "考試題", "probe": "體檢題", "new": "新測試句"}
NAMES = {"trf": "大型", "distilled": "蒸餾版（網站）", "sm": "小型"}


def main_folder() -> Path:
    """主資料夾（worktree 裡沒有 .venv、models，要回主資料夾找）"""
    try:
        out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        return Path(out).parent
    except Exception:
        return ROOT


def model_path(key: str) -> str:
    if key == "trf":
        return "en_core_web_trf"
    if key == "sm":
        return "en_core_web_sm"
    for base in (ROOT, main_folder()):
        p = base / "models" / "en_core_web_sm_distilled"
        if p.exists():
            return str(p)
    sys.exit("找不到蒸餾版模型 models/en_core_web_sm_distilled（主資料夾也沒有）")


# ---------- 新測試句 ----------
def load_new():
    """讀 docs/引擎檢查-新測試句.md 的表格列：| 代號 | 代碼 | 正確句型 | 句子 | 重點答案 | 結果 |"""
    items = []
    for line in NEW_FILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([A-Z]\d\d) \| ([^|]+) \| [^|]* \| (.+?) \| ([^|]*) \| [^|]* \|$", line)
        if not m:
            continue
        checks = []
        for c in m.group(4).split("；"):
            if "=" in c:
                t, r = c.rsplit("=", 1)
                checks.append((t.strip(), r.strip()))
        items.append({"id": m.group(1), "code": m.group(2).strip(), "sentence": m.group(3).strip(), "checks": checks})
    return items


def norm(t: str) -> str:
    return t.strip(" .,?!;:")


def pattern_code(res) -> str:
    from backend.analyzer.schema import PATTERN_DISPLAY
    return "&".join("E" if c.elliptic else f"{PATTERN_DISPLAY[c.pattern]}{'p' if c.passive else ''}" for c in res.clauses) or "-"


def check_new(item, analyze) -> list[str]:
    """回傳錯誤清單（空的就是通過）。比對方法見 docs/引擎全面檢查-2026-11.md 附錄"""
    try:
        res = analyze(item["sentence"])
    except Exception as e:  # 當掉也算錯
        return [f"當掉：{e!r}"]
    errs, got = [], pattern_code(res)
    want = item["code"]
    if want != "?":
        g = got if "&" in want else got.split("&")[0]
        if g != want:
            errs.append(f"句型 應 {want} 得 {got}")
    chunks = {norm(c.text): c for c in res.chunks}
    for text, role in item["checks"]:
        c = chunks.get(norm(text))
        if c is None:
            near = [x for x in res.chunks if text in x.text or (len(x.text) > 1 and x.text in text)]
            errs.append(f"「{text}」範圍不同 → {' ／ '.join(f'{x.role}:{x.text}' for x in near) or '無'}")
        elif role.startswith("M:"):
            f = (c.function or "") + (c.modifies.text if c.modifies else "")
            if c.role != "M" or not f.startswith(role[2:]):
                errs.append(f"「{text}」應 {role[2:]} 得 {f or c.role}")
        elif c.role != role:
            errs.append(f"「{text}」應 {role} 得 {c.role}")
    if res.status != "ok":
        errs.append(f"狀態 {res.status}")
    return errs


# ---------- 子行程：一個模型跑全部 ----------
def child(out_path: str):
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    import yaml
    import run_tests
    from backend.analyzer.engine import analyze_sentence

    result = {}
    for name in ("practice", "exam", "probe"):
        items = yaml.safe_load((ROOT / "tests" / name / "gold.yaml").read_text(encoding="utf-8"))
        failed = {}
        for it in items:
            try:
                _, _, lines, _ = run_tests.evaluate([it])
                errs = [l[2:] for l in lines if l.startswith("- ")]
            except Exception as e:
                errs = [f"當掉：{e!r}"]
            if errs:
                failed[it["sentence"]] = errs
        result[name] = {"total": len(items), "failed": failed, "all": sorted({it["sentence"] for it in items})}
    new = load_new()
    failed = {}
    for it in new:
        errs = check_new(it, analyze_sentence)
        if errs:
            failed[f"{it['id']} {it['sentence']}"] = errs
    result["new"] = {"total": len(new), "failed": failed, "all": sorted(f"{it['id']} {it['sentence']}" for it in new)}
    Path(out_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def run_models(keys):
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="verify_engine_"))
    procs = {}
    for k in keys:
        env = dict(os.environ, SPACY_MODEL=model_path(k))
        procs[k] = subprocess.Popen([sys.executable, __file__, "--child", str(tmp / f"{k}.json")],
                                    env=env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    out = {}
    for k, p in procs.items():
        _, err = p.communicate()
        f = tmp / f"{k}.json"
        if p.returncode != 0 or not f.exists():
            sys.exit(f"{NAMES[k]}模型跑失敗：\n{err[-2000:]}")
        out[k] = json.loads(f.read_text(encoding="utf-8"))
    return out


def side_tests():
    """片語測試、格式檢查：回傳 [(名稱, 通過?, 最後一行)]"""
    out = []
    for name, script in (("片語測試", "tests/phrases_test.py"), ("格式檢查", "tests/validate_formats.py")):
        p = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        last = lines[-1] if lines else p.stderr[-300:]
        bad = p.returncode != 0 or any(l.lstrip().startswith(("✗", "✘", "×")) for l in lines)
        out.append((name, not bad, last))
    return out


# ---------- show：看某幾句的分析結果 ----------
def show_child(sentences, deps):
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(ROOT))
    from backend.analyzer.engine import analyze_sentence, get_nlp

    def fmt(c):
        lab = c.role if c.role != "M" else (c.function + (c.modifies.text if c.modifies else ""))
        s = f"[{lab} {c.text}]"
        return s + ("{" + " ".join(fmt(x) for x in c.inner) + "}" if c.inner else "")

    out = []
    for s in sentences:
        try:
            r = analyze_sentence(s)
            d = {"status": r.status, "header": r.header, "chunks": " ".join(fmt(c) for c in r.chunks),
                 "cards": [c.id for c in r.cards], "msg": r.message or ""}
        except Exception as e:
            d = {"status": "當掉", "header": "", "chunks": repr(e), "cards": [], "msg": ""}
        if deps:
            d["deps"] = " ".join(f"{t.text}/{t.tag_}/{t.dep_}←{t.head.text}" for t in get_nlp()(s))
        out.append(d)
    print(json.dumps(out, ensure_ascii=False))


def show(args):
    deps = "--deps" in args
    keys = ["trf", "distilled", "sm"]
    if "--model" in args:
        k = args[args.index("--model") + 1]
        keys = keys if k == "all" else [k]
        args = [a for i, a in enumerate(args) if a != "--model" and (i == 0 or args[i - 1] != "--model")]
    rest = [a for a in args if a != "--deps"]
    if not rest:
        sys.exit("用法：verify_engine.py show \"句子\" 或 句子檔.txt [--deps] [--model trf|distilled|sm|all]")
    p = Path(rest[0])
    sentences = ([l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
                 if len(rest) == 1 and p.exists() else rest)
    results = {}
    procs = {k: subprocess.Popen([sys.executable, __file__, "--show-child", json.dumps(sentences), "1" if deps else "0"],
                                 env=dict(os.environ, SPACY_MODEL=model_path(k)), cwd=ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for k in keys}
    for k, pr in procs.items():
        o, e = pr.communicate()
        try:
            results[k] = json.loads(o.strip().splitlines()[-1])
        except Exception:
            sys.exit(f"{NAMES[k]}模型跑失敗：\n{e[-2000:]}")
    for i, s in enumerate(sentences):
        print(f"\n■ {s}")
        for k in keys:
            d = results[k][i]
            print(f"  {NAMES[k]}：{d['status']}｜{d['header']}{'｜' + d['msg'] if d['msg'] else ''}")
            print(f"    {d['chunks']}")
            if d["cards"]:
                print(f"    卡片：{'、'.join(d['cards'])}")
            if deps:
                print(f"    依附：{d['deps']}")


# ---------- 主程式 ----------
def main():
    args = sys.argv[1:]
    if args[:1] == ["--child"]:
        return child(args[1])
    if args[:1] == ["--show-child"]:
        return show_child(json.loads(args[1]), args[2] == "1")
    if args[:1] == ["show"]:
        return show(args[1:])

    keys = ["trf", "distilled", "sm"]
    if "--only" in args:
        keys = [args[args.index("--only") + 1]]
    print(f"跑 {'、'.join(NAMES[k] for k in keys)}模型 × 四套題（約 1～2 分鐘）…", flush=True)
    now = run_models(keys)

    if "--save-baseline" in args:
        base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        for k in keys:
            base[k] = {s: {"total": now[k][s]["total"], "failed": sorted(now[k][s]["failed"])} for s in SUITES}
        # 存基準時題庫裡有哪些句子：之後才分得出「舊題退步」和「新加的題目小模型本來就不會」
        base["_題目"] = {s: now[keys[0]][s]["all"] for s in SUITES}
        BASELINE.write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"基準已存到 {BASELINE.relative_to(ROOT)}")

    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    old_items = {s: set(v) for s, v in base.get("_題目", {}).items()}
    problems, details = [], []
    print("\n| 模型 | " + " | ".join(SUITES.values()) + " |\n|---|" + "---|" * len(SUITES))
    for k in keys:
        cells = []
        for s in SUITES:
            cur = now[k][s]
            b = base.get(k, {}).get(s)
            cell = f"{cur['total'] - len(cur['failed'])}/{cur['total']}"
            if b is not None:
                old = set(b["failed"])
                failing = set(cur["failed"]) - old
                # 存基準之後才加進題庫的題目：大型模型一定要過（下面另外檢查）；小模型不過只列出來，不算退步
                added = {w for w in failing if w not in old_items.get(s, set())} if s in old_items else set()
                worse = sorted(failing - added)
                better = sorted(old - set(cur["failed"]))
                if worse:
                    cell += f"　退步 {len(worse)}"
                    problems.append(f"{NAMES[k]}模型 {SUITES[s]}：{len(worse)} 句原本通過、現在不通過")
                    for w in worse:
                        details.append(f"✗ [{NAMES[k]}／{SUITES[s]}] {w}\n    " + "\n    ".join(cur["failed"][w][:4]))
                if added:
                    cell += f"　新題不過 {len(added)}"
                    if k != "trf":
                        for w in sorted(added):
                            details.append(f"△ [{NAMES[k]}／{SUITES[s]}] 新加的題目這個模型不過：{w}\n    " + "\n    ".join(cur["failed"][w][:4]))
                if better:
                    cell += f"　修好 {len(better)}"
                    for w in better:
                        details.append(f"✓ [{NAMES[k]}／{SUITES[s]}] 修好：{w}")
            if k == "trf" and s != "new" and cur["failed"]:
                problems.append(f"大型模型 {SUITES[s]}有 {len(cur['failed'])} 句不通過（要全對）")
                for w, e in cur["failed"].items():
                    line = f"✗ [大型／{SUITES[s]}] {w}\n    " + "\n    ".join(e[:4])
                    if line not in details:
                        details.append(line)
            cells.append(cell)
        print(f"| {NAMES[k]} | " + " | ".join(cells) + " |")
    if not base:
        print("\n（還沒有基準，先在 main 上跑一次 --save-baseline）")

    for name, ok, last in side_tests():
        print(f"{name}：{'通過' if ok else '不通過'}（{last.strip()}）")
        if not ok:
            problems.append(f"{name}不通過")
    if details:
        print("\n" + "\n".join(details))
    print("\n判定：" + ("✗ 不能存 git\n  - " + "\n  - ".join(problems) if problems else "✓ 可以存 git（沒有退步）"))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
