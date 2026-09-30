"""片段說明文字：點片段時顯示的那一兩句話，用範本自動產生。"""

ADVERB_NOTE = {
    "副詞・表時間": "說明「什麼時候」或「多久」。",
    "副詞・表地點": "說明「在哪裡」或「到哪裡」。",
    "副詞・表方式": "說明「怎麼做」。",
    "副詞・表目的": "說明「為了什麼」。",
    "副詞・表狀況": "說明動作發生時的狀況。",
    "副詞・表路程": "說明「多遠」或「經過哪裡」。",
    "副詞・表語氣": "加強或改變句子的語氣。",
    "副詞・表否定": "表示否定，意思是「不、沒有」。",
    "副詞・表原因": "說明「為什麼」。",
    "副詞・表比較": "比較的對象：和誰、和什麼比。",
    "副詞・表伴隨": "說明「跟誰一起」。",
    "副詞・表對象": "說明動作的「對象」：對誰、對什麼做這個動作。",
    "副詞・表執行者": "被動語態的 by ＋ 執行者：說明這個動作是「誰」做的。",
    "副詞子句・表時間": "副詞子句：說明主要句子「什麼時候」發生。它不能單獨成句。",
    "副詞子句・表原因": "副詞子句：說明主要句子的「原因」。它不能單獨成句。",
    "副詞子句・表條件": "副詞子句：說明「在什麼條件下」。它不能單獨成句。",
    "副詞子句・表讓步": "副詞子句：意思是「雖然、即使」。它不能單獨成句。",
    "副詞子句・表目的": "副詞子句：說明「為了什麼」。它不能單獨成句。",
    "副詞子句・表地點": "副詞子句：說明「在哪裡」。它不能單獨成句。",
    "副詞子句・表結果": "so／such … that 的 that 子句：說明「所以導致什麼結果」。",
    "副詞子句・表對比": "副詞子句：和主要句子形成對比（whereas、while）。它不能單獨成句。",
    "副詞子句・表比例": "副詞子句：意思是「隨著…」，一邊變化、另一邊也跟著變化。它不能單獨成句。",
    "副詞子句・表方式": "副詞子句：說明「照什麼方式、像什麼樣子」（as、as if）。它不能單獨成句。",
}


def _head(c):
    heads = c.get("heads") or []
    return "、".join(h.text for h in heads)


def chunk_note(c, infos, text, compound=None) -> str:
    role = c["role"]
    spec = c.get("_spec")
    root = c.get("_root")
    info = infos.get(c.get("clause", 0))
    head = _head(c)
    compound = len(infos) > 1 if compound is None else compound
    prefix = f"子句{'一二三四'[c.get('clause', 0)]}的" if compound and role not in ("M", "conj") else ""

    focus = "被強調的部分（強調句把它放在 It is／was 和 that 中間）。" if spec is not None and spec.kind == "cleft_focus" else ""
    if role == "EF":
        return ("強調句的框架：It is／was ＋ 被強調的部分 ＋ that／who ＋ 其餘部分。"
                "把框架拿掉，剩下的就是原本的句子，句型照原本的句子判斷。框架不算進公式。")
    if focus and role == "M":
        return focus + ADVERB_NOTE.get(c.get("function") or "", "")
    if focus:
        names = {"S": "主詞", "O": "受詞", "IO": "間接受詞", "DO": "直接受詞", "SC": "主詞補語", "OC": "受詞補語"}
        return f"{focus}還原成原本的句子後，它是{names.get(role, '')}。"
    if role == "S":
        if spec is not None and spec.kind == "lets_us":
            return ("主詞：'s 是 us（我們）的縮寫，Let's＝Let us，不是 Let is。"
                    "提議「我們一起…吧」，所以做動作的是「我們」。")
        if c.get("implicit"):
            return "省略的主詞：祈使句是直接對「你」說話，所以主詞 You 省略不寫。括號表示句子裡看不到，但文法上存在。"
        if spec is not None and spec.kind == "real_subject":
            return f"真正的主詞，位置在動詞後面。{'核心字是 ' + head + '。' if head else ''}"
        if root is not None and info is not None and "gerund_subject" in info.flags and root.dep_.startswith("nsubj"):
            return "動名詞（V-ing）當主詞，意思是「做這件事」，視為單數。"
        if root is not None and root.lower_ == "it" and info and "dummy_it" in info.flags:
            return "虛主詞（形式主詞），本身沒有意思，只是先佔住主詞的位置，真正的主詞在句尾。"
        if not head and c.get("structure") == "名詞片語" and root is not None and any(ch.lower_ == "of" for ch in root.children):
            return f"{prefix}主詞。這種「數量詞 ＋ of ＋ 名詞」的主詞不標核心字，看下方文法重點。"
        return f"{prefix}主詞{'，核心字是 ' + head if head else ''}。"
    if role == "RS":
        if c.get("text", "").lower().startswith("for "):
            return ("真正的主詞，因為太長，所以移到句尾，用 It 代替。不算進公式（虛線）。"
                    "for ＋ 人 說明「誰」去做後面的動作（不定詞的意義上主詞）。")
        return "真正的主詞，因為太長，所以移到句尾，用 It 代替。不算進公式（虛線）。"
    if role == "RO":
        return "真正的受詞，因為太長，所以移到句尾，受詞的位置先用 it 代替。不算進公式（虛線）。"
    if role == "Vt":
        if info and info.passive:
            return "被動語態的主要動詞（過去分詞 p.p.）。它本來是及物動詞，主詞是動作的承受者。"
        if info and info.pattern == 4:
            return f"{prefix}動詞，後面接兩個受詞：給「誰」（IO）什麼東西（DO）。"
        if info and info.pattern == 5:
            return f"{prefix}動詞，後面接受詞，再接說明受詞的受詞補語。"
        return f"{prefix}及物動詞，後面需要受詞。"
    if role == "Vi":
        if info and info.existential:
            return "be 動詞在這裡表示「存在、有」，後面不接受詞，所以是 Vi。單複數跟著後面真正的主詞。"
        if info and info.verb_token.lemma_ == "be":
            return "be 動詞在這裡表示「在（某個地方）」，是不及物動詞 Vi。後面的地點是修飾語，但不能省略，少了它意思就不完整。"
        return f"{prefix}不及物動詞，後面不需要受詞，主幹到這裡就完整了。"
    if role == "V":
        return (f"{prefix}不及物動詞 Vi，而且是「連綴動詞」：像等號一樣把主詞和後面的補語連起來，"
                "後面接的不是受詞，但一定要接補語，意思才完整。")
    if role == "aux":
        lower = c["text"].lower()
        if spec is not None and spec.kind == "lets":
            return ("Let's 的 Let：用來提議「我們一起…吧」，後面的 's 是 us（我們），再接原形動詞。"
                    "Let 在這裡不算進公式，句型看後面的動詞。")
        if info and info.passive and lower in ("am", "is", "are", "was", "were", "be", "been", "being"):
            return "be 動詞在這裡當助動詞，和過去分詞組成被動語態，不算進公式（虛線）。"
        if lower in ("am", "is", "are", "was", "were") and info and info.verb_token.tag_ == "VBG":
            return "be 動詞在這裡當助動詞，和 V-ing 組成進行式，不算進公式（虛線）。"
        if lower in ("have", "has", "had") and info and info.verb_token.tag_ == "VBN":
            return "have／has 在這裡當助動詞，和過去分詞組成完成式，不算進公式（虛線）。"
        if "n't" in lower or "not" in lower:
            return "否定的助動詞，不算進公式（虛線）。"
        if info and info.question:
            return "助動詞，移到主詞前面就變成疑問句。它幫主要動詞表達語氣或時態，不算進公式（虛線）。"
        return "助動詞，幫主要動詞表達時態或語氣，不算進公式（虛線）。"
    if role == "O":
        if info and "dummy_object" in info.flags and c.get("text", "").lower() == "it":
            return "虛受詞（形式受詞），本身沒有意思，只是先佔住受詞的位置，真正的受詞在句尾。"
        s = c.get("structure")
        if s in ("不定詞片語", "動名詞片語", "動名詞"):
            return f"受詞：{s}當名詞用，是動作的對象。"
        if s == "名詞子句":
            return "受詞：整個名詞子句當受詞，是動作的對象。點一下可以展開子句。"
        return f"{prefix}受詞，動作的對象{'，核心字是 ' + head if head else ''}。"
    if role == "IO":
        return f"間接受詞：動作給「誰」？{'核心字是 ' + head + '。' if head else ''}"
    if role == "DO":
        if c.get("structure") == "名詞子句":
            return "直接受詞：整個名詞子句是給對方的「內容」。點一下可以展開子句。"
        return f"直接受詞：給「什麼」？{'核心字是 ' + head + '。' if head else ''}"
    if role == "SC":
        if root is not None and (root.dep_ == "prep" or root.lower_ in ("here", "there", "home", "where")):
            return ("主詞補語：be 動詞後面的介系詞片語或地方副詞，說明主詞「在哪裡」或「處於什麼狀態」。"
                    "少了它，句子的意思就不完整。")
        return "主詞補語：說明主詞的身分或狀態，可以想成「主詞 ＝ 補語」。"
    if role == "OC":
        if c.get("structure") == "不定詞片語":
            return "受詞補語：說明受詞「要去做什麼」。ask、tell、want、allow 等動詞常用「受詞 ＋ to V」。"
        if c.get("structure") == "原形動詞片語":
            return "受詞補語：說明受詞做什麼。使役動詞、感官動詞後面接原形動詞。"
        return "受詞補語：說明受詞的狀態或身分，可以想成「受詞 ＝ 補語」。"
    if role == "conj":
        word = c["text"].lower()
        if compound:
            return f"對等連接詞 {word}，連接兩個完整的句子。它不屬於任何一個子句，所以不算進公式。"
        if len(infos) > 1:
            return f"對等連接詞 {word}，連接兩個動詞（平行結構）：主詞只出現一次，兩個動詞共用同一個主詞。"
        return f"連接詞 {word}，帶出後面的子句。"
    if role == "M":
        f = c.get("function") or ""
        if f == "同位語・說明":
            target = c["modifies"].text if c.get("modifies") else ""
            return f"同位語：緊接在 {target} 後面，換個說法補充說明 {target} 是誰或是什麼，兩者指的是同一個人事物。"
        if f == "副詞・分詞構句":
            return "分詞構句：由副詞子句省略主詞、動詞改成 V-ing（或 p.p.）變來的，主詞和主要句子相同。常表示「同時」或「原因」。"
        if f == "附加問句":
            return "附加問句：接在句尾，向對方確認「對吧？」。前面是否定，附加問句就用肯定；前面是肯定，就用否定。它不屬於句子的主幹，不算進公式。"
        if f == "引導詞":
            return "There 在這裡不是「那裡」，只是用來引出主詞的引導詞。看下方文法重點。"
        if f == "形容詞・修飾":
            target = c["modifies"].text if c.get("modifies") else ""
            extra = ""
            if c.get("structure") == "形容詞子句":
                extra = "前後有逗號時，表示只是補充說明。點一下可以展開子句。" if "," in text else "點一下可以展開子句。"
            note = f"放在 {target} 後面，說明是「哪一個」{target}。{extra}"
            mod_root = root.head if root is not None else None
            if root is not None and root.lower_ in ("in", "on", "at", "near") and mod_root is not None and mod_root.dep_ == "dobj":
                note += f"也可以理解成說明動作發生的地點（副詞），意思差不多。"
            return note
        base = ADVERB_NOTE.get(f, "")
        if f == "副詞・表否定" and c["text"].lower() == "never":
            base = "表示否定，意思是「從來不、從來沒有」。"
        if f == "副詞・表對象" and root is not None and (root.head.pos_ == "ADJ" or root.head.dep_ == "acomp"):
            adj = root.head.text
            base = (f"放在形容詞 {adj} 後面，說明 {adj} 的對象或範圍（對什麼、在哪方面）。"
                    f"形容詞 ＋ 介系詞常常是固定搭配（good at、interested in），整組一起記。")
        if f.startswith("副詞・表") and root is not None and root.dep_ == "advcl" and root.tag_ in ("VBG", "VBN"):
            base = f"由副詞子句縮減而來的副詞片語（省略主詞、動詞改成 V-ing），{base}"
        if f == "副詞・表地點" and root is not None and root.head.lemma_ in ("be", "live", "put", "place", "lay", "set", "stay"):
            base += "這裡的地點是動詞必需的，拿掉之後句子意思就不完整。"
        if spec is not None and spec.kind == "ambiguous_place":
            base += "也可以理解成修飾前面的名詞（例如「花園裡的花」），意思差不多。"
        if f.startswith("副詞子句") and c["text"].lower().startswith("as ") and not c["text"].lower().startswith(("as if", "as though", "as soon as", "as long as")):
            base += ("as 有五種常見意思，可以用換字法判斷：換成 when／while 說得通是表時間（當…時）；"
                     "換成 because 是表原因（因為）；翻成「隨著」是表比例；換成 in the way that 是表方式（依照、如同）；"
                     "形容詞放在 as 前面（Tired as Mom was）是表讓步（雖然）。")
        if c.get("inner"):
            base += "點一下可以展開子句。"
        return base
    if role == "unknown":
        return "這部分目前的規則還沒辦法分析，所以先標成「未分析」。"
    return ""
