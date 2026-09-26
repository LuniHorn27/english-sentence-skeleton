"""網頁伺服器。

啟動：.venv/bin/uvicorn backend.app:app --port 8765
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.analyzer.engine import analyze_text, get_nlp
from backend.analyzer.schema import AnalysisResult, Card, SentenceResult

ROOT = Path(__file__).resolve().parent.parent
MAX_CHARS = 2000
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app):
    get_nlp()  # 啟動時先載入分析程式，第一次分析才不會等很久
    log.info("分析程式載入完成")
    yield


app = FastAPI(title="英文句子骨架分析", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    text: str


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(req: AnalyzeRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "請輸入英文句子或一段英文文章")
    if len(text) > MAX_CHARS:
        raise HTTPException(400, f"句子太長了，請控制在 {MAX_CHARS} 個字元以內")
    try:
        sentences = analyze_text(text)
    except Exception:  # 分析引擎出錯時，不讓網頁當掉，回報「無法分析」
        log.exception("分析失敗：%r", text)
        sentences = [SentenceResult(text=text, status="failed", clauses=[], chunks=[],
                                    message="這段文字目前沒辦法分析，請換個說法再試一次。")]
    return AnalysisResult(input=text, sentences=sentences)


@app.get("/api/cards/{card_id}", response_model=Card)
def get_card(card_id: str):
    path = ROOT / "backend" / "cards" / f"{card_id}.yaml"
    if not card_id.replace("_", "").isalnum() or not path.exists():
        raise HTTPException(404, "找不到這張文法重點卡")
    return Card(**yaml.safe_load(path.read_text(encoding="utf-8")))


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
