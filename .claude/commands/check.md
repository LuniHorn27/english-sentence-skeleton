---
description: 全面檢查：跑所有測試和驗收檢查，回報有沒有問題
---

請跑下面這些檢查，最後用幾句話回報結果（全部通過就簡短說；有失敗就說哪裡壞了、可能的原因、要不要修）：

1. `.venv/bin/python tests/run_tests.py`（練習題）、`--exam`（考試題）、`--probe`（體檢題）
2. `.venv/bin/python tests/phrases_test.py`
3. `.venv/bin/python tests/validate_formats.py`
4. `.venv/bin/python -u tests/robustness.py`（確認沒有當掉）
5. 網站伺服器有在跑的話，再跑 `.venv/bin/python tools/acceptance_check.py`（注意它最後會觸發次數限制，之後約 1 分鐘分析會被擋）

跑完把 `tests/report_*.md` 還原（`git checkout -- tests/report_*.md`，體檢題的報告直接刪掉），不要因為只有時間變動而存 git。台灣繁體中文。
