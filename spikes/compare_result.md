
## 總表

| 分析程式 | 主幹角色 | 句型 | 片語邊界 | 44 句總時間 |
|---|---|---|---|---|
| spaCy 小型 | 133/145（92%） | 38/44（86%） | （不支援） | 0.2 秒 |
| spaCy 大型 | 141/145（97%） | 43/44（98%） | （不支援） | 1.5 秒 |
| spaCy 大型＋benepar | 141/145（97%） | 43/44（98%） | 181/183（99%） | 3.4 秒 |
| Stanza | 136/145（94%） | 39/44（89%） | 179/183（98%） | 8.1 秒 |

## 各角色正確率

| 分析程式 | S | Vi | Vt | V | aux | O | IO | DO | SC | OC |
|---|---|---|---|---|---|---|---|---|---|---|
| spaCy 小型 | 44/44 | 7/7 | 28/29 | 8/8 | 5/5 | 15/18 | 5/8 | 6/9 | 8/8 | 7/9 |
| spaCy 大型 | 44/44 | 7/7 | 28/29 | 8/8 | 5/5 | 17/18 | 7/8 | 8/9 | 8/8 | 9/9 |
| spaCy 大型＋benepar | 44/44 | 7/7 | 28/29 | 8/8 | 5/5 | 17/18 | 7/8 | 8/9 | 8/8 | 9/9 |
| Stanza | 44/44 | 7/7 | 28/29 | 8/8 | 4/5 | 17/18 | 7/8 | 8/9 | 8/8 | 5/9 |

## 錯誤明細：spaCy 小型（18 項）

  #24 句型：答案 4，程式 2　Grandpa gave each of us a red envelope.
  #24 「each of us」答案 IO，程式 O
  #24 「a red envelope」答案 DO，程式 O
  #27 「our dog」答案 O，程式 None
  #30 句型：答案 5，程式 4　They elected him class leader.
  #30 「him」答案 O，程式 IO
  #30 「class leader」答案 OC，程式 DO
  #33 句型：答案 4，程式 5　My big sister, who likes to cook, made our whole family a big chocolate cake for Mom's birthday.
  #33 「our whole family」答案 IO，程式 O
  #33 「a big chocolate cake」答案 DO，程式 OC
  #34 句型：答案 5，程式 2　Everyone in our class calls the funny boy with the big glasses Little Bear.
  #34 「Little Bear」答案 OC，程式 None
  #35 句型：答案 2，程式 1　Every morning before school, the children in Miss Lin's class water the small flowers in the garden.
  #35 「water」答案 Vt，程式 None
  #35 「the small flowers」答案 O，程式 Vi
  #38 句型：答案 4，程式 5　The nice man at the small store found us a good seat near the window on a busy day.
  #38 「us」答案 IO，程式 O
  #38 「a good seat」答案 DO，程式 OC

## 錯誤明細：spaCy 大型（5 項）

  #11 「enjoy」答案 Vt，程式 aux
  #11 「playing basketball」答案 O，程式 Vt
  #33 句型：答案 4，程式 2　My big sister, who likes to cook, made our whole family a big chocolate cake for Mom's birthday.
  #33 「our whole family」答案 IO，程式 None
  #33 「a big chocolate cake」答案 DO，程式 O

## 錯誤明細：spaCy 大型＋benepar（5 項）

  #11 「enjoy」答案 Vt，程式 aux
  #11 「playing basketball」答案 O，程式 Vt
  #33 句型：答案 4，程式 2　My big sister, who likes to cook, made our whole family a big chocolate cake for Mom's birthday.
  #33 「our whole family」答案 IO，程式 None
  #33 「a big chocolate cake」答案 DO，程式 O

## 錯誤明細：Stanza（14 項）

  #27 句型：答案 5，程式 2　We named our dog Lucky.
  #27 「Lucky」答案 OC，程式 None
  #30 句型：答案 5，程式 4　They elected him class leader.
  #30 「him」答案 O，程式 IO
  #30 「class leader」答案 OC，程式 DO
  #33 句型：答案 4，程式 5　My big sister, who likes to cook, made our whole family a big chocolate cake for Mom's birthday.
  #33 「our whole family」答案 IO，程式 O
  #33 「a big chocolate cake」答案 DO，程式 OC
  #34 句型：答案 5，程式 2　Everyone in our class calls the funny boy with the big glasses Little Bear.
  #34 「Little Bear」答案 OC，程式 None
  #44 句型：答案 5，程式 3　He was elected class leader.
  #44 「was」答案 aux，程式 V
  #44 「elected」答案 Vt，程式 None
  #44 「class leader」答案 OC，程式 SC
