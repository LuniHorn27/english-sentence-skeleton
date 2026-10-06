# Render 部署步驟（免費測試版）

> 2026-10-06。測試版放在 Render 免費方案：不用 Mac 一直開著、不用綁信用卡。完整版（大型模型、伺服器翻譯和朗讀）仍然在 Mac 上用 `requirements.txt` 執行，兩邊是同一套程式，只差環境變數。

## 測試版和完整版的差別

| | 完整版（Mac） | 測試版（Render） |
|---|---|---|
| 分析模型 | 大型 en_core_web_trf：題庫 471 句全對 | 小型 en_core_web_sm：約每 9 句有 1 句不對 |
| 記憶體 | 約 6 GB（含翻譯、朗讀） | 最高約 270 MB（上限 512 MB） |
| 翻譯 | 伺服器上的 Qwen3-4B | 只有電腦版 Chrome／Edge 能用瀏覽器內建翻譯 |
| 朗讀 | 伺服器上的 Kokoro | 瀏覽器內建語音 |
| 首頁提示 | 沒有 | 「🧪 測試版：分析結果偶爾會出錯…」 |
| 休眠 | 不會 | 閒置 15 分鐘後休眠，下一個人要等 30～60 秒 |

小型模型的實測數字和錯誤類型見 PR 說明。

## 設定在哪裡

- `render.yaml`：Render 讀這個檔案自動建立網站（免費方案、新加坡機房、環境變數）。
- `requirements-slim.txt`：測試版要安裝的套件（沒有 PyTorch、翻譯、朗讀）。
- 環境變數：
  - `SPACY_MODEL=en_core_web_sm`：換成小型模型。沒設定時用大型模型。
  - `TEST_EDITION=1`：首頁顯示測試版提示。
  - `FEEDBACK_SHEET_URL`：回饋試算表的網址。**只在 Render 後台填，不放進 GitHub。**

## 你要做的（約 10 分鐘）

1. 到 https://render.com 按 **Get Started**，選 **GitHub** 登入（不用信用卡）。
2. 登入後，右上角 **New → Blueprint**。
3. 第一次會要求連結 GitHub：選 **Only select repositories**，只勾 `english-sentence-skeleton`，按 **Install**。這一步是授權 Render 讀取這個專案。
4. 回到 Render，選 `english-sentence-skeleton`，按 **Connect**。
5. Render 會讀到 `render.yaml`，並要求填 `FEEDBACK_SHEET_URL`：貼上回饋試算表的網址，也就是 Apps Script「部署」後給的那個 `https://script.google.com/...` 網址，跟 Mac 上 `data/feedback_sheet.json` 裡的是同一個。
6. 按 **Apply**。第一次安裝套件約 3～5 分鐘，完成後網址是 `https://english-sentence-skeleton.onrender.com`（如果名字被用走了，Render 會在後面加幾個字）。
7. 把網址告訴我，我會從外面檢查：分析、回饋、次數限制、安全標頭。

之後每次合併到 main，Render 都會自動重新部署，網址不變。

## 上線後要檢查的事

- **次數限制**：2026-10-06 實測，只靠 `X-Forwarded-For` 標頭時，每次偽造一個假位址就能繞過「每分鐘最多分析 30 次」。已改成讀 Cloudflare 給的 `CF-Connecting-IP`（環境變數 `CLIENT_IP_HEADER`），訪客偽造的值會被 Cloudflare 蓋掉。
- **回饋**：送一則測試回饋，確認試算表有新的一行、有收到 email，然後刪掉這一行。
- **速度**：免費方案只有 0.1 顆 CPU，實際量一句、一整段文章各要多久。

## 不讓它休眠（選用）

到 https://cron-job.org 免費註冊，新增一個每 10 分鐘連一次網站首頁的排程。Render 免費方案每月有 750 小時，一個網站整個月不停也夠用。
