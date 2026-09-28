---
description: 啟動網站：本機伺服器＋Cloudflare 臨時網址，測試後把網址給使用者
---

請幫使用者把網站開起來：

1. 先看 8765 埠是不是已經有這個專案的伺服器在跑（`lsof -iTCP:8765 -sTCP:LISTEN`，確認是 `uvicorn backend.app:app`）。有就沿用，不要再開一份。
2. 沒有的話，用背景執行啟動穩定模式（不要加 --reload）：
   `.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8765 --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-access-log`
   等到 http://127.0.0.1:8765/ 回 200。
3. 看有沒有 cloudflared 通道在跑而且連得上；沒有或已失效（日誌出現 Tunnel not found）就停掉舊的，用背景執行：
   `cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8765`
   從輸出找出 `https://….trycloudflare.com` 網址。
4. 從外部測試網址（Mac 的網址快取可能還沒更新，用 `dig +short` 查到 IP 後以 `curl --resolve` 測），確認回 200。
5. 在內建瀏覽器打開 http://localhost:8765 給使用者看。
6. 把臨時網址更新到 `docs/交接筆記.md` 的「網站」那一行，只 commit 這個檔案。
7. 用一兩句話回報：網站開好了、臨時網址是什麼，並提醒 Mac 睡眠或關機後網址會失效。

回答用台灣繁體中文，簡短。
