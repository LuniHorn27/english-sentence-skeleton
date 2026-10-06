# 測試報告：考試題（33 句，3.3 秒）

| 項目 | 正確率 |
|---|---|
| 主幹角色 | 108/114（95%） |
| 句型 | 30/33（91%） |
| 修飾語功能 | 29/29（100%） |
| 片段範圍 | 138/143（97%） |
| 核心字 | 39/40（98%） |
| 部分分析 | — |

| S | Vt | Vi | V | aux | O | IO | DO | SC | OC |
|---|---|---|---|---|---|---|---|---|---|
| 32/33 | 20/21 | 6/6 | 5/6 | 10/10 | 11/12 | 6/6 | 7/7 | 5/6 | 6/7 |

## 錯誤明細（3 句有錯）

**#E11** Some of my classmates like spicy food.
- 句型：答案 2，程式 None
- 「Some of my classmates」 範圍不同，程式切成：（沒有）
- 「like」 範圍不同，程式切成：（沒有）
- 「spicy food」 範圍不同，程式切成：（沒有）
- 狀態：failed（找不到句子的主要動詞，這可能不是一個完整的句子（例如只有片語），請再確認一次。）

**#E18** Is your sister a nurse?
- 句型：答案 3，程式 1
- 「Is」 角色：答案 V，程式 Vi
- 「a nurse」 角色：答案 SC，程式 M
- 「a nurse」 核心字：答案 nurse，程式 （無）

**#E29** Leave the window open, please.
- 句型：答案 5，程式 2
- 「the window」 範圍不同，程式切成：the window open
- 「open」 範圍不同，程式切成：the window open
- 「open」 角色：答案 OC，程式 O
