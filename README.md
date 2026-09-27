---
title: English Sentence Skeleton
emoji: 📝
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: 英文句子骨架分析：主詞、動詞、受詞、補語與五大句型
---

<!-- 上面這段是 Hugging Face Spaces 的設定（用 Docker 執行、網站在 7860 埠），不要刪 -->

# 英文句子骨架分析

幫助台灣學生和英文學習者看懂英文句子的工具：輸入一個英文句子，
自動標出主詞、動詞、受詞、補語、修飾語，判斷五大句型，並附上文法重點說明。

## 啟動

第一次使用要先安裝（約 2 GB，需要幾分鐘）：

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python -m spacy download en_core_web_trf
```

之後每次使用：

```bash
.venv/bin/uvicorn backend.app:app --port 8765
```

再用瀏覽器打開 http://127.0.0.1:8765 。翻譯需要先下載翻譯模型（2.5 GB）：`bash spikes/download_models.sh`；沒有模型時會改用瀏覽器內建翻譯（電腦版 Chrome 或 Edge）。

## 資料夾

| 位置 | 內容 |
|---|---|
| `backend/app.py` | 網頁伺服器 |
| `backend/analyzer/` | 分析引擎（engine.py）、字表（lexicon.py）、說明範本（notes.py）、資料格式（schema.py） |
| `backend/cards/` | 文法重點卡，一張一個檔案 |
| `frontend/` | 網頁畫面 |
| `tests/` | 題庫與自動測試 |
| `docs/` | 規格書、計畫、測試報告、**待審核清單** |

## 測試

```bash
.venv/bin/python tests/run_tests.py
```

改了規則或字表之後，一定要跑一次，確認分數沒有下降。
