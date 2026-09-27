"""驗收檢查：對執行中的網站逐項測試，印出每一項的結果（docs/驗收文件.md 的佐證）。

用法（網站要先啟動）：.venv/bin/python tools/acceptance_check.py [網址，預設 http://127.0.0.1:8765]
注意：最後一項會故意送出大量請求，觸發「次數限制」，之後約 1 分鐘內分析會被擋。
不會送出回饋（避免寫進回饋檔、跳出通知）。
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765").rstrip("/")
results = []


def call(path, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return r.status, raw, r.headers.get("Content-Type", ""), time.perf_counter() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", ""), time.perf_counter() - t


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} {name}　{detail}", flush=True)


def analyze(text):
    code, raw, _, secs = call("/api/analyze", {"text": text})
    return code, (json.loads(raw) if code == 200 else raw.decode("utf-8", "replace")), secs


# ---------- 頁面 ----------
for path in ["/", "/patterns", "/quiz", "/about", "/static/style.css", "/static/app.js"]:
    code, raw, ctype, _ = call(path)
    check(f"頁面 {path}", code == 200, f"HTTP {code}")

# ---------- 分析 ----------
code, d, secs = analyze("Everyone in our class calls the funny boy with the big glasses Little Bear.")
s = d["sentences"][0] if code == 200 else {}
check("單句分析：句型與公式", code == 200 and s.get("header") == "句型四：S + Vt + O + OC", f"{s.get('header')}（{secs:.1f} 秒）")
check("單句分析：核心字", code == 200 and any(h["text"] == "boy" for c in s["chunks"] for h in c.get("heads", [])), "the funny boy 的核心字 boy")
code, d, _ = analyze("I give you a big hand.")
check("片語卡：慣用語", code == 200 and any(p["id"] == "give_a_big_hand" for p in d["sentences"][0]["phrases"]), "give someone a big hand")
code, d, _ = analyze("I am at school.")
check("I am at school 歸句型一（使用者決定）", code == 200 and d["sentences"][0]["header"] == "句型一：S + Vi", d["sentences"][0]["header"] if code == 200 else "")
code, d, _ = analyze("It was not easy.")
check("not 標「副詞・表否定」", code == 200 and any(c.get("function") == "副詞・表否定" for c in d["sentences"][0]["chunks"]))
para = " ".join(["The sun rises in the east."] * 32)
code, d, _ = analyze(para)
check("整段文章：最多 30 句", code == 200 and len(d["sentences"]) == 31 and d["sentences"][-1]["status"] == "failed", f"{len(d['sentences']) if code == 200 else code} 個結果（30 句＋1 則提示）")
code, d, _ = analyze("x" * 2001)
check("輸入太長會被擋（2000 字元）", code == 400, f"HTTP {code}")
code, d, _ = analyze("這是中文")
check("中文輸入會提示", code == 200 and d["sentences"][0]["status"] == "failed", d["sentences"][0].get("message", "") if code == 200 else "")
code, d, _ = analyze("<script>alert(1)</script> I like you.")
check("含 HTML 的輸入不會出錯", code == 200, "畫面一律用純文字顯示（textContent）")

# ---------- 翻譯 ----------
code, raw, _, secs = call("/api/translate", {"text": "I give you a big hand.", "phrases": ["give_a_big_hand"]})
zh = json.loads(raw).get("translation", "") if code == 200 else ""
check("翻譯：慣用語提示", code == 200 and "鼓掌" in zh, f"{zh}（{secs:.1f} 秒）")
code, raw, _, _ = call("/api/translate", {"text": "She gave up smoking last year, and it was not a piece of cake.", "phrases": ["give_up", "a_piece_of_cake"]})
zh = json.loads(raw).get("translation", "") if code == 200 else ""
check("翻譯：and 不翻成「但」、用「菸」", code == 200 and "但" not in zh and "菸" in zh, zh)

# ---------- 朗讀 ----------
code, raw, ctype, secs = call("/api/tts", {"text": "Birds fly.", "speed": "normal"})
check("朗讀：產生聲音", code == 200 and ctype.startswith("audio/") and len(raw) > 1000, f"{ctype}、{len(raw) // 1024} KB、{secs:.1f} 秒")

# ---------- 查單字 ----------
code, raw, _, _ = call("/api/lookup", {"text": "the funny boy with the big glasses"})
words = {w["word"]: w for w in json.loads(raw)["words"]} if code == 200 else {}
check("查單字：略過小字、glasses＝眼鏡", code == 200 and "the" not in words and "眼鏡" in words.get("glasses", {}).get("meaning", ""), "、".join(words))
code, raw, _, _ = call("/api/lookup", {"text": "gave"})
w = json.loads(raw)["words"][0] if code == 200 else {}
check("查單字：變化形查原形", w.get("base") == "give", "gave → give")

# ---------- 文法重點卡 ----------
code, raw, _, _ = call("/api/cards/passive")
check("文法重點卡", code == 200, f"HTTP {code}")
code, raw, _, _ = call("/api/cards/..%2Fapp")
check("文法重點卡：不能讀其他檔案", code == 404, f"HTTP {code}")

# ---------- 小遊戲 ----------
code, raw, _, _ = call("/api/quiz?count=20")
items = json.loads(raw)["items"] if code == 200 else []
bad = [i["sentence"] for i in items if i["passive"] or any(c["role"] in ("conj", "RS") or c.get("function") == "引導詞" for c in i["chunks"])]
check("小遊戲：20 題不重複", len({i["sentence"] for i in items}) == 20)
check("小遊戲：不出有爭議的題目", not bad, "、".join(bad) or "沒有被動、對等句、There is、虛主詞")
check("小遊戲：每題都有中文翻譯", all(i.get("zh") for i in items))

# ---------- 回饋 ----------
code, _, _, _ = call("/api/feedback", {"kind": "error", "message": ""})
check("回饋：空白內容會被擋", code == 422, f"HTTP {code}")
code, _, _, _ = call("/admin/feedback")
local = BASE.startswith("http://127.0.0.1") or BASE.startswith("http://localhost")
check("回饋清單：本機打得開、外部打不開", code == (200 if local else 404), f"HTTP {code}（{'本機' if local else '外部'}）")
code, _, _, _ = call("/resources")
check("學習資源草稿：本機打得開、外部打不開", code == (200 if local else 404), f"HTTP {code}")
code, _, _, _ = call("/static/resources.html")
check("草稿頁不能從 /static/ 打開", code == 404, f"HTTP {code}")

# ---------- 次數限制（放最後） ----------
codes = [call("/api/analyze", {"text": "Birds fly."})[0] for _ in range(32)]
check("次數限制：分析每分鐘 30 次", 429 in codes, f"第 {codes.index(429) + 1 if 429 in codes else '—'} 次開始被擋")

passed = sum(ok for _, ok, _ in results)
print(f"\n{passed}／{len(results)} 項通過")
sys.exit(0 if passed == len(results) else 1)
