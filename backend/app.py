"""網頁伺服器。

啟動：.venv/bin/uvicorn backend.app:app --port 8765
"""
import json
import logging
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
from backend import tts
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
    yield


def _warm_tts():
    try:
        tts.get_pipeline()
        log.info("朗讀模型載入完成")
    except Exception:
        log.exception("朗讀模型載入失敗，網頁會改用瀏覽器內建語音")


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
FEEDBACK_FILE = ROOT / "data" / "feedback.jsonl"
FEEDBACK_LIMIT = 20  # 同一個來源每小時最多幾則，防止洗版
_feedback_lock = threading.Lock()


class Feedback(BaseModel):
    kind: Literal["error", "suggestion"]
    sentence: str = Field("", max_length=2000)
    part: str = Field("", max_length=300, description="使用者選的片段或項目")
    current: str = Field("", max_length=300, description="目前的分析結果")
    message: str = Field(min_length=1, max_length=1000)
    analysis: Optional[dict] = None


@app.post("/api/feedback")
def feedback(item: Feedback, request: Request):
    check_rate(request, "feedback", FEEDBACK_LIMIT, 3600, "回饋次數太多了，請稍後再試")
    with _feedback_lock:
        FEEDBACK_FILE.parent.mkdir(exist_ok=True)
        record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **item.model_dump()}
        with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


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


@app.get("/api/quiz")
def quiz():
    import random

    item = random.choice(QUIZ_ITEMS)
    return {
        "sentence": item["sentence"],
        "pattern": item["pattern"],
        "passive": item["passive"],
        "chunks": [{"text": c["text"], "role": c["role"], "function": c.get("function")} for c in item["chunks"]],
    }


@app.get("/quiz")
def quiz_page():
    return FileResponse(ROOT / "frontend" / "quiz.html")


@app.get("/about")
def about_page():
    return FileResponse(ROOT / "frontend" / "about.html")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
