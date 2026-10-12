---
description: Gemini 抓錯助手：讓 Gemini 照標籤規則分析一批句子，和我們的程式比對，找出我們分析錯的地方
argument-hint: （可以留空）句數，或「文章」＋貼上的英文
---

使用者要求跑 Gemini 抓錯助手：$ARGUMENTS

**做法**：我們的程式和 Gemini 各分析一次，只列出兩邊不一樣的句子，由你逐句判斷誰對。Gemini 的答案只能當線索，不是標準答案：比對過的經驗是差異裡大約兩成是 Gemini 錯（例如把狀態被動 *is covered with* 標成被動、There 標成強調框架）。

1. **跑工具**（從最新 main 開 worktree，在 worktree 裡執行；`data/` 只在主資料夾，所以要設 `ENGLISH_DATA`）：
   - 沒有指定時：Tatoeba 新句子，在上次的累計句數上再加 160 句（看 `data/gemini_scout/` 快取有幾行），`--batch 20`。
   - 使用者貼了文章：先存成 `data/gemini_scout/文章-日期.txt`（不進 git，可能有版權），用 `--file` 跑。
   - 額度用完時工具會自己停下，用已經問到的回答出報告；只想重看報告用 `--cached-only`。
   ```
   ENGLISH_DATA=<主資料夾>/data .venv/bin/python tools/gemini_scout.py --n <累計句數> --batch 20
   ```
2. **讀報告** `data/gemini_scout/scout_report.md`，先看「一、主幹或句型不同」，再看「二、修飾語功能或核心字」。只有片段切法不同的句子工具已經略過。
3. **逐句分類**，對照 `docs/標籤規則.md`：
   - **我們錯**（違反規則書已寫明的原則，或明顯不合文法）：依根本原因分組，每組照 `/fix` 的步驟修（造同類句子、修在字表或通用規則、大小模型都跑、加體檢題）。
   - **標法不同、規則書沒寫到**：不改，寫進 `docs/待審核清單.md`，附兩種標法和建議。
   - **Gemini 錯**：略過，回報時列一行。
   - 待審核清單裡已經在等使用者決定的同一件事，不重複列。
4. **開 PR 前**先 `git fetch` 看 origin/main：別的對話可能同時改了 `engine.py`、體檢題或待審核清單，題號從 main 最新號碼接著編。
5. **回報**：這次問了幾句、兩邊一樣幾句、修了哪幾類（附 PR）、記進待審核清單的有哪些。

**隱私和版權**：Tatoeba 是公開語料（CC BY 2.0 FR）可以直接送；使用者貼的文章只送使用者這次給的內容，課本、考題原文不進 git、不放進 PR 和體檢題（要用時改寫成文法結構相同的句子）。金鑰在使用者家目錄的 `.config/english-tool/gemini_api_key`，不要印出來、不要貼進對話。

台灣繁體中文，先講結論，句型編號一定配公式。
