"""網頁伺服器。

啟動：.venv/bin/uvicorn backend.app:app --port 8765
"""
import html
import json
import logging
import os
import subprocess
import sys
import uuid
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.analyzer.engine import analyze_text, get_nlp
from backend.analyzer.phrases import translation_hints
from backend import dictionary, translate, tts
from backend.analyzer.schema import AnalysisResult, Card, SentenceResult

ROOT = Path(__file__).resolve().parent.parent
MAX_CHARS = 2000
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app):
    get_nlp()  # 啟動時先載入分析程式，第一次分析才不會等很久
    log.info("分析程式載入完成")
    # 朗讀模型在背景載入，不拖慢網站啟動
    threading.Thread(target=_warm_tts, daemon=True).start()
    threading.Thread(target=_warm_translate, daemon=True).start()
    yield


def _warm_tts():
    try:
        tts.get_pipeline()
        log.info("朗讀模型載入完成")
    except Exception:
        log.exception("朗讀模型載入失敗，網頁會改用瀏覽器內建語音")


def _warm_translate():
    if not translate.MODEL_PATH.exists():
        log.warning("找不到翻譯模型 %s，網頁會改用瀏覽器內建翻譯", translate.MODEL_PATH)
        return
    try:
        translate.load()
        log.info("翻譯模型載入完成")
    except Exception:
        log.exception("翻譯模型載入失敗，網頁會改用瀏覽器內建翻譯")


app = FastAPI(title="英文句子骨架分析", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    text: str


# ---------- 次數限制（防止有人大量送出，拖垮伺服器） ----------
_rate_lock = threading.Lock()
_rate_times: dict[tuple[str, str], deque] = defaultdict(deque)


def check_rate(request: Request, bucket: str, limit: int, window: int, message: str):
    """同一個來源在 window 秒內最多 limit 次；來源位址只放在記憶體裡計數，不存檔"""
    key = (bucket, request.client.host if request.client else "unknown")
    now = time.time()
    with _rate_lock:
        times = _rate_times[key]
        while times and now - times[0] > window:
            times.popleft()
        if len(times) >= limit:
            raise HTTPException(429, message)
        times.append(now)


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(req: AnalyzeRequest, request: Request):
    check_rate(request, "analyze", 30, 60, "分析次數太多了，請等一分鐘後再試")
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "請輸入英文句子或一段英文文章")
    if len(text) > MAX_CHARS:
        raise HTTPException(400, f"句子太長了，請控制在 {MAX_CHARS} 個字元以內")
    try:
        sentences = analyze_text(text)
    except Exception:  # 分析引擎出錯時，不讓網頁當掉，回報「無法分析」
        log.exception("分析失敗（輸入長度 %d 字元；為了隱私不記錄內容）", len(text))
        sentences = [SentenceResult(text=text, status="failed", clauses=[], chunks=[],
                                    message="這段文字目前沒辦法分析，請換個說法再試一次。")]
    return AnalysisResult(input=text, sentences=sentences)


# ---------- 使用者回饋（2-5） ----------
# 本機：存在 data/feedback.jsonl。
# 上線（Hugging Face Spaces）：主機重新啟動時檔案會消失，所以設定了 FEEDBACK_DATASET（私人資料集名稱）
# 和 HF_TOKEN（Space 的 secret）時，每 10 分鐘自動同步到那個私人資料集；每次開機寫到新的檔案，不會蓋掉舊的。
FEEDBACK_LIMIT = 20  # 同一個來源每小時最多幾則，防止洗版
FEEDBACK_DATASET = os.environ.get("FEEDBACK_DATASET")
FEEDBACK_FILE = ROOT / "data" / "feedback.jsonl"
_feedback_lock = threading.Lock()
if FEEDBACK_DATASET and os.environ.get("HF_TOKEN"):
    try:
        from huggingface_hub import CommitScheduler

        _synced = ROOT / "data" / "feedback" / f"feedback-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.jsonl"
        _synced.parent.mkdir(parents=True, exist_ok=True)
        _scheduler = CommitScheduler(
            repo_id=FEEDBACK_DATASET, repo_type="dataset", folder_path=_synced.parent,
            path_in_repo="feedback", every=10, private=True, token=os.environ["HF_TOKEN"],
        )
        FEEDBACK_FILE, _feedback_lock = _synced, _scheduler.lock  # 寫檔和上傳不會同時進行
        log.info("回饋會同步到私人資料集 %s", FEEDBACK_DATASET)
    except Exception:
        log.exception("回饋同步設定失敗，先存在主機上的檔案（重新啟動會消失）")


class Feedback(BaseModel):
    kind: Literal["error", "suggestion"]
    sentence: str = Field("", max_length=2000)
    part: str = Field("", max_length=300, description="使用者選的片段或項目")
    current: str = Field("", max_length=300, description="目前的分析結果")
    message: str = Field(min_length=1, max_length=1000)
    analysis: Optional[dict] = None


# 回饋同時送到 Google 試算表（設定方式見 docs/回饋試算表設定.md）
#   網址放在環境變數 FEEDBACK_SHEET_URL，或 data/feedback_sheet.json 的 {"url": "..."}（data/ 不會上傳到 GitHub）
def _sheet_url():
    url = os.environ.get("FEEDBACK_SHEET_URL")
    cfg = ROOT / "data" / "feedback_sheet.json"
    if not url and cfg.exists():
        try:
            url = json.loads(cfg.read_text(encoding="utf-8")).get("url")
        except ValueError:
            log.warning("data/feedback_sheet.json 格式不對，回饋不會送到試算表")
    return url if url and url.startswith("https://script.google.com/") else None


def _send_to_sheet(record: dict):
    url = _sheet_url()
    if not url:
        return

    def post():
        import urllib.error
        import urllib.request

        data = json.dumps({k: record.get(k) for k in ("time", "kind", "sentence", "part", "current", "message")}, ensure_ascii=False)
        req = urllib.request.Request(url, data=data.encode("utf-8"), headers={"Content-Type": "application/json"})

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None  # Google 寫完後會轉到結果頁，不用跟過去

        try:
            urllib.request.build_opener(NoRedirect).open(req, timeout=15).read()
        except urllib.error.HTTPError as e:
            if e.code != 302:  # 302 代表 Google 已經寫進試算表
                log.warning("回饋送到試算表失敗：HTTP %s（本機檔案已保存）", e.code)
        except Exception:  # 送不到試算表時，本機檔案裡還有一份
            log.warning("回饋送到試算表失敗（本機檔案已保存）")

    threading.Thread(target=post, daemon=True).start()


def _notify_mac(item: "Feedback"):
    """網站在自己的 Mac 上執行時，有新回饋就跳出系統通知（只在這台 Mac 上，不送到外部服務）"""
    if sys.platform != "darwin" or os.environ.get("FEEDBACK_NOTIFY") == "0":
        return
    title = "新的回報錯誤" if item.kind == "error" else "新的回饋"
    body = " ".join(item.message.split())[:80]
    script = 'on run argv\ndisplay notification (item 2 of argv) with title "英文句子骨架分析" subtitle (item 1 of argv) sound name "Glass"\nend run'
    try:
        subprocess.Popen(["osascript", "-e", script, title, body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


@app.post("/api/feedback")
def feedback(item: Feedback, request: Request):
    check_rate(request, "feedback", FEEDBACK_LIMIT, 3600, "回饋次數太多了，請稍後再試")
    with _feedback_lock:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **item.model_dump()}
        with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    _send_to_sheet(record)
    _notify_mac(item)
    return {"ok": True}


def _is_local(request: Request) -> bool:
    """只有在這台電腦上直接打開才算（經過通道、代理伺服器進來的一律不算）"""
    host = request.client.host if request.client else ""
    forwarded = any(h in request.headers for h in ("x-forwarded-for", "cf-connecting-ip", "forwarded", "x-real-ip"))
    return host in ("127.0.0.1", "::1") and not forwarded


@app.get("/admin/feedback")
def feedback_list(request: Request):
    """回饋清單：只能在執行網站的這台電腦上打開"""
    if not _is_local(request):
        raise HTTPException(404, "Not Found")
    files = [ROOT / "data" / "feedback.jsonl", *sorted((ROOT / "data").glob("feedback/*.jsonl"))]
    records = []
    for f in files:
        if f.exists():
            records += [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    records.sort(key=lambda r: r.get("time", ""), reverse=True)
    esc = html.escape
    rows = []
    for r in records:
        local = datetime.fromisoformat(r["time"]).astimezone().strftime("%Y-%m-%d %H:%M")
        kind = "🐞 回報錯誤" if r.get("kind") == "error" else "💬 一起讓它更好"
        where = f"{esc(r.get('part', ''))}（目前：{esc(r.get('current') or '—')}）" if r.get("part") else ""
        rows.append(f"<tr><td>{local}</td><td>{kind}</td><td>{esc(r.get('sentence', ''))}</td><td>{where}</td><td>{esc(r.get('message', ''))}</td></tr>")
    body = "".join(rows) or '<tr><td colspan="5">目前還沒有回饋。</td></tr>'
    page = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>回饋清單</title><link rel="stylesheet" href="/static/style.css"></head><body><main>
<h1>回饋清單（{len(records)} 則）</h1><p class="hint">只有在執行網站的這台電腦上才打得開。最新的在最上面；重新整理頁面可以看到新的回饋。</p>
<div class="table-wrap"><table class="fb-table"><thead><tr><th>時間</th><th>種類</th><th>句子</th><th>哪裡</th><th>內容</th></tr></thead>
<tbody>{body}</tbody></table></div></main></body></html>"""
    return Response(page, media_type="text/html", headers={"Cache-Control": "no-store"})


# ---------- 朗讀（Kokoro） ----------
class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=tts.MAX_CHARS)
    speed: Literal["normal", "slow"] = "normal"


@app.post("/api/tts")
def speak(req: SpeakRequest, request: Request):
    # 用 POST 而不是把句子放在網址裡，句子才不會出現在伺服器的存取紀錄中
    check_rate(request, "tts", 60, 60, "朗讀次數太多了，請等一分鐘後再試")
    try:
        audio = tts.synthesize(req.text, req.speed)
    except Exception:
        log.exception("朗讀失敗（輸入長度 %d 字元）", len(req.text))
        raise HTTPException(503, "朗讀暫時無法使用")
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "private, max-age=86400"})


# ---------- 中文翻譯（Qwen3-4B） ----------
class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=translate.MAX_CHARS)
    phrases: list[str] = Field(default_factory=list, max_length=20, description="分析找到的片語代號（只接受清單裡有的）")


@app.post("/api/translate")
def translate_sentence(req: TranslateRequest, request: Request):
    # 翻譯最吃電腦資源（一句 1～5 秒、一次只能翻一句），限制次數才不會有人把伺服器佔滿
    check_rate(request, "translate", 60, 60, "翻譯次數太多了，請等一分鐘後再試")
    if not translate.is_available():
        raise HTTPException(503, "翻譯暫時無法使用")
    try:
        return {"translation": translate.translate(req.text, translation_hints(req.phrases))}
    except Exception:
        log.exception("翻譯失敗（輸入長度 %d 字元）", len(req.text))
        raise HTTPException(503, "翻譯暫時無法使用")


# ---------- 查單字（ECDICT） ----------
class LookupRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300)


@app.post("/api/lookup")
def lookup(req: LookupRequest, request: Request):
    check_rate(request, "lookup", 120, 60, "查詢次數太多了，請等一分鐘後再試")
    return {"words": dictionary.lookup_text(req.text)}


@app.get("/api/cards/{card_id}", response_model=Card)
def get_card(card_id: str):
    path = ROOT / "backend" / "cards" / f"{card_id}.yaml"
    if not card_id.replace("_", "").isalnum() or not path.exists():
        raise HTTPException(404, "找不到這張文法重點卡")
    return Card(**yaml.safe_load(path.read_text(encoding="utf-8")))


@app.middleware("http")
async def no_stale_files(request, call_next):
    """網頁檔案更新後，瀏覽器要重新確認，不要用舊的快取"""
    response = await call_next(request)
    if request.url.path in ("/", "/patterns", "/about", "/quiz") or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/patterns")
def patterns_page():
    return FileResponse(ROOT / "frontend" / "patterns.html")


# ---------- 句型小遊戲（F2）：題目來自人工審核過的練習題 ----------
QUIZ_ITEMS = yaml.safe_load((ROOT / "tests" / "practice" / "gold.yaml").read_text(encoding="utf-8"))


# 小遊戲只出「答案沒有爭議」的題目。不同文法書說法不同、或容易混淆的都不出：
#   對等句（兩個主詞）、被動語態、There is、be ＋ 地點（I am at school）、
#   seem ＋ to V、as／into 當受詞補語、虛主詞 It、還沒分析的句子
_BE = {"am", "is", "are", "was", "were", "be", "been", "being", "'m", "'s", "'re"}


def _quiz_ok(item):
    chunks = item["chunks"]
    roles = {c["role"] for c in chunks}
    return not (
        roles & {"conj", "RS", "unknown"}
        or item.get("passive")
        or any(c.get("function") == "引導詞" for c in chunks)
        or any(c["role"] == "Vi" and c["text"].lower() in _BE for c in chunks)
        or any(c["role"] == "SC" and c["text"].lower().startswith("to ") for c in chunks)
        or any(c["role"] == "OC" and c["text"].lower().startswith(("as ", "into ")) for c in chunks)
    )


QUIZ_POOL = [x for x in QUIZ_ITEMS if _quiz_ok(x)]
# 題目的中文翻譯（人工檢查過；新題目用 tools/make_quiz_zh.py 產生草稿）
_zh_file = ROOT / "backend" / "quiz_zh.yaml"
QUIZ_ZH = yaml.safe_load(_zh_file.read_text(encoding="utf-8")) if _zh_file.exists() else {}


def _quiz_item(item):
    return {
        "sentence": item["sentence"],
        "zh": QUIZ_ZH.get(item["sentence"]),
        "pattern": item["pattern"],
        "passive": item["passive"],
        "chunks": [{"text": c["text"], "role": c["role"], "function": c.get("function"),
                    "implicit": bool(c.get("implicit")) or c["text"].startswith("(")} for c in item["chunks"]],
    }


@app.get("/api/quiz")
def quiz(count: int = 10):
    """一回合的題目（不重複），最多 20 題"""
    import random

    picks = random.sample(QUIZ_POOL, min(max(count, 1), 20, len(QUIZ_POOL)))
    return {"items": [_quiz_item(x) for x in picks]}


@app.get("/quiz")
def quiz_page():
    return FileResponse(ROOT / "frontend" / "quiz.html")


@app.get("/resources")
def resources_page(request: Request):
    """學習資源（草稿）：使用者確認內容前，只能在執行網站的這台電腦上打開"""
    if not _is_local(request):
        raise HTTPException(404, "Not Found")
    return FileResponse(ROOT / "backend" / "drafts" / "resources.html")  # 不放在 frontend/，免得從 /static/ 被打開


@app.get("/about")
def about_page():
    return FileResponse(ROOT / "frontend" / "about.html")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
