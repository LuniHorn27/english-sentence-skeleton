"""網頁伺服器。

啟動：.venv/bin/uvicorn backend.app:app --port 8765
1-1 階段：分析功能先回傳 backend/samples/ 的示範假資料，還沒有接上分析引擎。
"""
import json
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.analyzer.schema import AnalysisResult, Card

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = sorted((ROOT / "backend" / "samples").glob("*.json"))
MAX_CHARS = 300

app = FastAPI(title="英文句子骨架分析")


class AnalyzeRequest(BaseModel):
    text: str


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(req: AnalyzeRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "請輸入一個英文句子")
    if len(text) > MAX_CHARS:
        raise HTTPException(400, f"句子太長了，請控制在 {MAX_CHARS} 個字元以內")
    # 假資料：依照輸入的長度輪流回傳示範結果，方便測試不同畫面
    sample = SAMPLES[len(text) % len(SAMPLES)]
    return AnalysisResult(**json.loads(sample.read_text(encoding="utf-8")))


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
