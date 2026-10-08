"""Gemini 和我們的分析程式比一比：讓 Gemini 照標籤規則書分析題庫，用 tests/run_tests.py 同一套評分算正確率。

用法（在專案資料夾執行）：
  .venv/bin/python tools/gemini_compare.py 模型名稱 [practice exam probe]
  例：gemini-3.5-flash（免費額度一天約 20 次請求，8 句一批）；忙碌時可用 gemini-3.5-flash-lite
金鑰讀使用者家目錄的 .config/english-tool/gemini_api_key（不放在專案裡、不進 git）。
Gemini 的回答和報告存在 data/gemini/（不上傳），重跑時不會重複呼叫。
2026-10-07 比較結果：3.5 Flash 考試題 0 錯、練習題 9 錯（多半是切法習慣不同）；決定 Python 為主、Gemini 當開發時的抓錯助手。
"""
import json
import os
import sys
import time
import types
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import run_tests  # noqa: E402

MODEL = sys.argv[1]
SETS = sys.argv[2:] or ["practice", "exam", "probe"]
KEY = Path("~/.config/english-tool/gemini_api_key").expanduser().read_text().strip()
HERE = Path(__file__).resolve().parent.parent / "data" / "gemini"
HERE.mkdir(parents=True, exist_ok=True)
CACHE = HERE / f"gemini_cache_{MODEL}.jsonl"
BATCH = 8
DISPLAY_TO_INTERNAL = {1: 1, 2: 3, 3: 2, 4: 5, 5: 4}  # 賴世雄的句型編號 → 程式內部代號（schema.py PATTERN_DISPLAY 的反向）

SPEC = (ROOT / "docs" / "標籤規則.md").read_text(encoding="utf-8")
SYSTEM = f"""你是台灣國高中英文老師，要照下面這份「標籤規則書」拆解英文句子的骨架。規則書是唯一標準，和你平常的習慣不同時，一律照規則書。

輸出要求（很重要）：
- 每一句輸出 pattern（句型編號 1～5，照規則書的賴世雄編號：1＝S+Vi、2＝S+Vi+SC、3＝S+Vt+O、4＝S+Vt+O+OC、5＝S+Vt+IO+DO；對等句只填第一個子句）、passive（是不是被動語態）、chunks。
- chunks 照句子順序列出每個片段，text 必須是原句裡一字不差的一段（不含句尾標點；逗號也不要放進片段），全部片段合起來要涵蓋整句。
- role 只能是：S、Vt、Vi、V、aux、O、IO、DO、SC、OC、M、conj、RS、RO、EF。
  連綴動詞（be、look、seem、become…後面接主詞補語）填 V；其他不及物動詞填 Vi；修飾語一律填 M。
  祈使句省略的主詞輸出一個 text 為 "(You)"、role 為 S 的片段。
- role 是 M 時，function 填規則書第 4.1 節表格裡的標籤，例如 "副詞・表時間"、"副詞子句・表原因"、"形容詞・修飾"；
  形容詞修飾語另外把被修飾的那個字填在 modifies（例如 function "形容詞・修飾"、modifies "students"）。其他角色 function、modifies 留空字串。
- heads：照規則書 5.2 節列出核心字（只有名詞性的 S、O、IO、DO、SC、OC 片段要填；只有一個字的片段、數量詞＋of 不填）。沒有就給空陣列。

===== 標籤規則書 =====
{SPEC}"""

CHUNK = {"type": "object", "properties": {
    "text": {"type": "string"}, "role": {"type": "string"}, "function": {"type": "string"},
    "modifies": {"type": "string"}, "heads": {"type": "array", "items": {"type": "string"}}},
    "required": ["text", "role", "function", "modifies", "heads"]}
SCHEMA = {"type": "object", "properties": {"results": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "pattern": {"type": "integer"}, "passive": {"type": "boolean"},
    "chunks": {"type": "array", "items": CHUNK}}, "required": ["id", "pattern", "passive", "chunks"]}}},
    "required": ["results"]}


def call_gemini(batch):
    lines = "\n".join(f"{it['key']}\t{it['sentence']}" for it in batch)
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": "請拆解下面每一句（每行是 id、Tab、句子），id 照抄：\n" + lines}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    for attempt in range(8):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
        try:
            t = time.time()
            d = json.load(urllib.request.urlopen(req, timeout=300))
            text = d["candidates"][0]["content"]["parts"][0]["text"]
            usage = d.get("usageMetadata", {})
            return json.loads(text)["results"], time.time() - t, usage
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode(errors="replace")
            wait = 20 * (attempt + 1) if e.code in (429, 500, 503) else None
            print(f"  HTTP {e.code}：{msg[:160]}", flush=True)
            if wait is None:
                raise
            time.sleep(wait)
        except Exception as e:  # 回答格式壞掉、逾時：重試
            print(f"  錯誤：{e}", flush=True)
            time.sleep(10)
    raise RuntimeError("重試太多次")


def load_cache():
    out = {}
    if CACHE.exists():
        for line in CACHE.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def to_result(sentence, r):
    """Gemini 的回答 → 和 analyze_sentence 一樣形狀的物件，給 run_tests.evaluate 評分"""
    chunks, pos = [], 0
    for c in r.get("chunks", []):
        text = c["text"].strip()
        if text in ("(You)", "（You）"):
            chunks.append(types.SimpleNamespace(implicit=True, text="(You)", start=0, end=0, role=c["role"],
                                                function=None, modifies=None, heads=[]))
            continue
        start = sentence.find(text, pos)
        if start < 0:
            start = sentence.find(text)
        if start < 0:
            continue  # 不是原句裡的字（Gemini 改寫了句子）：當成沒切到
        end = start + len(text)
        pos = end
        heads = [types.SimpleNamespace(text=h) for h in c.get("heads") or []]
        mod = types.SimpleNamespace(text=c["modifies"]) if c.get("modifies") else None
        role = c["role"].strip().rstrip(".")  # aux.／conj. 這類純格式差異不算錯
        func = (c.get("function") or "").replace(" X", "").replace("X", "").strip()  # 照抄規則書範例的「說明 X」
        if c.get("modifies") and func.endswith(c["modifies"]):
            func = func[: -len(c["modifies"])].strip()  # 被修飾的字同時寫在標籤和 modifies 裡：只算一次
        c = dict(c, function=func)
        chunks.append(types.SimpleNamespace(implicit=False, text=text, start=start, end=end, role=role,
                                            function=(c.get("function") or None) if role == "M" else None,
                                            modifies=mod if role == "M" else None,
                                            heads=heads if role in run_tests.CORE else []))
    pattern = DISPLAY_TO_INTERNAL.get(r.get("pattern"), None)
    clause = types.SimpleNamespace(pattern=pattern, passive=bool(r.get("passive")))
    return types.SimpleNamespace(chunks=chunks, clauses=[clause], status="ok", message=None)


def main():
    cache = load_cache()
    all_items = {}
    for name in SETS:
        items = yaml.safe_load((ROOT / "tests" / name / "gold.yaml").read_text(encoding="utf-8"))
        for it in items:
            it["key"] = f"{name}-{it['id']}"
        all_items[name] = items
    todo = [it for items in all_items.values() for it in items if it["key"] not in cache]
    print(f"{MODEL}：要問 {len(todo)} 句（已有 {len(cache)} 句的回答）", flush=True)
    total_secs, tokens = 0.0, 0
    with CACHE.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            results, secs, usage = call_gemini(batch)
            total_secs += secs
            tokens += usage.get("totalTokenCount", 0)
            got = {str(r.get("id")): r for r in results}
            for it in batch:
                r = got.get(it["key"]) or {"chunks": [], "pattern": None, "passive": False}
                r["id"] = it["key"]
                cache[it["key"]] = r
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            print(f"  {min(i + BATCH, len(todo))}/{len(todo)}　這批 {secs:.1f} 秒", flush=True)
            time.sleep(4)
    if todo:
        print(f"呼叫 Gemini 共 {total_secs:.0f} 秒，平均每句 {total_secs / len(todo):.1f} 秒，用了 {tokens} tokens")

    for name, items in all_items.items():
        run_tests.analyze_sentence = lambda s, _items=items: None  # 先佔位，下面逐句換
        lookup = {it["sentence"]: cache[it["key"]] for it in items}
        run_tests.analyze_sentence = lambda s: to_result(s, lookup[s])
        stats, per_role, lines, _ = run_tests.evaluate(items)
        pct = lambda a, b: f"{a}/{b}（{100 * a / b:.0f}%）" if b else "—"
        wrong = sum(1 for l in lines if l.startswith("\n"))
        print(f"\n## {name}（{len(items)} 句）：{wrong} 句有錯")
        for k in ["主幹角色", "句型", "修飾語功能", "片段範圍", "核心字"]:
            print(f"  {k}：{pct(*stats[k])}")
        (HERE / f"gemini_report_{MODEL}_{name}.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
