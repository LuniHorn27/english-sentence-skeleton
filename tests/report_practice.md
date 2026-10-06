# 測試報告：練習題（107 句，4.5 秒）

| 項目 | 正確率 |
|---|---|
| 主幹角色 | 343/361（95%） |
| 句型 | 99/107（93%） |
| 修飾語功能 | 90/105（86%） |
| 片段範圍 | 447/466（96%） |
| 核心字 | 60/60（100%） |
| 部分分析 | — |

| S | Vt | Vi | V | aux | O | IO | DO | SC | OC |
|---|---|---|---|---|---|---|---|---|---|
| 106/108 | 65/67 | 16/16 | 25/27 | 20/20 | 46/49 | 10/12 | 11/13 | 25/27 | 14/17 |

## 錯誤明細（15 句有錯）

**#27** We named our dog Lucky.
- 句型：答案 5，程式 3
- 「named」 角色：答案 Vt，程式 V
- 「our dog」 範圍不同，程式切成：our dog Lucky
- 「our dog」 角色：答案 O，程式 SC
- 「Lucky」 範圍不同，程式切成：our dog Lucky
- 「Lucky」 角色：答案 OC，程式 SC

**#30** They elected him class leader.
- 句型：答案 5，程式 4
- 「him」 角色：答案 O，程式 IO
- 「class leader」 角色：答案 OC，程式 DO

**#33** My big sister, who likes to cook, made our whole family a big chocolate cake for Mom's birthday.
- 句型：答案 4，程式 5
- 「our whole family」 角色：答案 IO，程式 O
- 「a big chocolate cake」 角色：答案 DO，程式 OC
- 「for Mom's birthday」 功能：答案 副詞・表目的，程式 形容詞・修飾cake

**#34** Everyone in our class calls the funny boy with the big glasses Little Bear.
- 句型：答案 5，程式 2
- 「with the big glasses」 功能：答案 形容詞・修飾boy，程式 副詞・表方式
- 「Little Bear」 角色：答案 OC，程式 M

**#35** Every morning before school, the children in Miss Lin's class water the small flowers in the garden.
- 句型：答案 2，程式 None
- 「Every morning」 範圍不同，程式切成：（沒有）
- 「before school」 範圍不同，程式切成：（沒有）
- 「the children」 範圍不同，程式切成：（沒有）
- 「in Miss Lin's class」 範圍不同，程式切成：（沒有）
- 「water」 範圍不同，程式切成：（沒有）
- 「the small flowers」 範圍不同，程式切成：（沒有）
- 「in the garden」 範圍不同，程式切成：（沒有）
- 狀態：failed（找不到句子的主要動詞，這可能不是一個完整的句子（例如只有片語），請再確認一次。）

**#36** The leaves on the big trees near the river turn red and yellow in the fall.
- 「red and yellow」 範圍不同，程式切成：red and yellow in the fall
- 「in the fall」 範圍不同，程式切成：red and yellow in the fall

**#38** The nice man at the small store found us a good seat near the window on a busy day.
- 句型：答案 4，程式 5
- 「us」 角色：答案 IO，程式 O
- 「a good seat」 角色：答案 DO，程式 OC

**#49** The old man sitting on the bench in the park feeds the pigeons with bread crumbs every morning.
- 「with bread crumbs」 功能：答案 副詞・表方式，程式 形容詞・修飾pigeons

**#52** My parents gave me some useful advice about how to manage my time when I started junior high school.
- 「about how to manage my time」 範圍不同，程式切成：about how to manage my time when I started junior high school
- 「when I started junior high school」 範圍不同，程式切成：about how to manage my time when I started junior high school

**#56** The small restaurant at the corner of the street, which is famous for its beef noodles, is always crowded at lunchtime.
- 「The small restaurant」 範圍不同，程式切成：The small restaurant at the corner of the street, which is famous for its beef noodles, is
- 「The small restaurant」 角色：答案 S，程式 V
- 「at the corner of the street」 範圍不同，程式切成：The small restaurant at the corner of the street, which is famous for its beef noodles, is
- 「which is famous for its beef noodles」 範圍不同，程式切成：The small restaurant at the corner of the street, which is famous for its beef noodles, is
- 「is」 範圍不同，程式切成：The small restaurant at the corner of the street, which is famous for its beef noodles, is

**#59** The children were so excited about the school trip that they could not sleep the night before.
- 「that they could not sleep the night before」 功能：答案 副詞子句・表結果，程式 形容詞・修飾trip

**#68** Even though it was raining, we went out.
- 「went」 範圍不同，程式切成：went out
- 「out」 範圍不同，程式切成：went out

**#72** It was such good coffee that I had another cup.
- 「that I had another cup」 功能：答案 副詞子句・表結果，程式 形容詞・修飾coffee

**#81** The door swung open.
- 句型：答案 3，程式 1
- 「swung」 角色：答案 V，程式 Vi
- 「open」 角色：答案 SC，程式 M

**#105** The door flew open.
- 句型：答案 3，程式 1
- 「flew」 角色：答案 V，程式 Vi
- 「open」 角色：答案 SC，程式 M
