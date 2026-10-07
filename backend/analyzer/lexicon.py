"""字表：規則判斷時用到的單字清單。

分析程式（spaCy）負責找出字和字的關係，這些字表負責補上「課本的分類」，
例如哪些是連綴動詞、哪些是授與動詞、哪些名詞表示時間。
新增字的時候，記得跑一次測試（python tests/run_tests.py）。
"""

# 真正的助動詞（其他被分析程式誤判成助動詞的字，當成主要動詞處理）
AUX_LEMMAS = {
    "be", "have", "do", "will", "would", "can", "could", "shall", "should",
    "may", "might", "must", "ought",
}

# 連綴動詞：後面接主詞補語
LINKING_VERBS = {
    "be", "look", "sound", "smell", "taste", "feel", "become", "get", "turn",
    "grow", "stay", "keep", "remain", "seem", "appear", "go", "come", "prove",
}

# 授與動詞：可以接 IO ＋ DO
DATIVE_VERBS = {
    "give", "show", "send", "tell", "pass", "buy", "make", "lend", "bring",
    "teach", "offer", "cook", "find", "get", "write", "read", "sing", "hand",
    "pay", "owe", "promise", "ask", "cost", "leave", "save", "sell", "throw",
    "build", "bake", "draw", "fetch", "order", "take",
}

# seem ＋ 不定詞：不定詞是主詞補語（賴世雄 p.32）
SEEM_VERBS = {"seem", "appear"}

# 動詞 ＋ 受詞 ＋ into／as 片語：片語是受詞補語（賴世雄 p.54、p.58）
#   take … for 也在書上，但 take the dog for a walk 的 for 是表目的，容易混淆，先不收
OC_PREP_VERBS = {
    ("turn", "into"), ("change", "into"), ("make", "into"), ("transform", "into"), ("convert", "into"),
    ("regard", "as"), ("view", "as"), ("see", "as"), ("treat", "as"), ("describe", "as"),
    ("consider", "as"), ("accept", "as"), ("recognize", "as"), ("define", "as"),
    ("elect", "as"), ("appoint", "as"), ("choose", "as"),
}

# 命名、選舉類動詞：後面兩個名詞是「受詞＋受詞補語」（name the baby Lily、elected Amy president）。
# 小型分析程式常把這兩個名詞看成別的結構，engine.py 用這張表修正；make 意思太多，不放
NAMING_VERBS = {"name", "call", "elect", "appoint", "choose", "nickname", "crown", "dub", "vote"}

# 動詞 ＋ 受詞 ＋ 不定詞：不定詞是受詞補語（asked him to write…）。
# 不在這個清單的動詞，受詞後面的不定詞當「表目的」（used the cupboard to store food）
VERB_OBJ_TO_V = {
    "advise", "allow", "ask", "beg", "bid", "cause", "challenge", "command", "compel", "convince", "dare",
    "enable", "encourage", "entice", "expect", "forbid", "force", "get", "help", "hire", "inspire", "instruct",
    "intend", "invite", "lead", "like", "love", "hate", "mean", "motivate", "need", "oblige", "order",
    "pay", "permit", "persuade", "prefer", "prepare", "pressure", "push", "recommend", "remind", "request",
    "require", "schedule", "seduce", "teach", "tell", "tempt", "train", "trust", "urge", "want", "warn", "wish",
    "would", "choose", "elect", "appoint", "select",
    # 動詞 ＋ 受詞 ＋ to be（認為類，賴世雄 p.54）；被動也常見：is said to be、is supposed to
    "believe", "consider", "deem", "think", "find", "know", "suppose", "assume", "declare", "judge",
    "prove", "report", "say", "understand", "imagine", "feel",
}

# 動詞 ＋ 子句（子句裡用原形動詞）：I suggest you do that.、demanded he pay back → 整個子句是受詞
SUBJUNCTIVE_VERBS = {"suggest", "demand", "insist", "recommend", "propose", "request", "require", "urge", "ask", "advise"}

# 放在動詞後面、當副詞用的形容詞（He lives alone.）；連綴動詞後面照舊是補語（She felt alone.）
ADVERBIAL_ADJS = {"alone"}

# 使役動詞、感官動詞：＋ 受詞 ＋ 原形動詞
CAUSATIVE_PERCEPTION = {"make", "let", "have", "help", "see", "hear", "watch", "feel", "notice"}

# 同一個動詞有好幾種句型（出「同一個動詞，不同句型」文法重點卡）
MULTI_PATTERN_VERBS = {"find", "run", "turn", "make", "get", "keep", "grow", "leave", "call"}

# 表示時間的名詞
TIME_NOUNS = {
    "morning", "afternoon", "evening", "night", "day", "week", "month", "year",
    "today", "tonight", "tomorrow", "yesterday", "weekend", "weekday",
    "spring", "summer", "fall", "autumn", "winter", "season",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "hour", "minute", "second", "moment", "time", "noon", "midnight",
    "holiday", "vacation", "semester", "term", "lunchtime", "dinnertime", "bedtime",
    "past", "future", "century", "decade", "while",
}

# 表示時間的介系詞
TIME_PREPS = {"before", "after", "during", "until", "till", "since", "throughout"}

# 表示地點、方向的介系詞
PLACE_PREPS = {
    "in", "on", "at", "under", "behind", "near", "over", "above", "below",
    "beside", "between", "inside", "outside", "into", "onto", "around", "across",
    "through", "along", "toward", "towards", "from", "to", "beneath", "past",
    "among", "opposite", "beyond", "up", "down", "out", "off",
}

# 表示時間的副詞
TIME_ADVERBS = {
    "today", "tonight", "tomorrow", "yesterday", "now", "then", "already", "soon",
    "later", "early", "late", "always", "often", "usually", "sometimes", "never",
    "ever", "still", "yet", "recently", "again", "once", "finally", "ago",
    "lately", "nowadays", "immediately", "seldom", "rarely", "forever",
}

# 表示地點的副詞
PLACE_ADVERBS = {
    "home", "here", "there", "outside", "inside", "abroad", "upstairs",
    "downstairs", "away", "everywhere", "somewhere", "nowhere", "anywhere",
    "back", "out", "nearby", "downtown", "indoors", "outdoors", "overseas",
}

# 表示語氣的副詞
TONE_ADVERBS = {"please", "yes", "no", "also", "too", "only", "just", "even", "really", "actually", "certainly", "surely", "maybe", "perhaps"}

# 天氣、狀況名詞（in the heavy rain → 表狀況）
CONDITION_NOUNS = {"rain", "snow", "wind", "storm", "sun", "sunshine", "heat", "cold", "dark", "darkness", "fog", "weather", "silence", "hurry", "danger", "trouble"}

# 人（with his friends → 表伴隨）
PERSON_NOUNS = {
    "friend", "family", "mother", "mom", "mum", "dad", "father", "parent", "brother",
    "sister", "teacher", "classmate", "people", "child", "kid", "grandma",
    "grandpa", "grandmother", "grandfather", "uncle", "aunt", "cousin", "son",
    "daughter", "wife", "husband", "boy", "girl", "man", "woman", "team",
    "student", "neighbor", "neighbour", "partner", "dog", "cat", "pet",
    "guest", "visitor", "baby", "player",
}

# 指人的代名詞（it、this、that 不算：made it a rule 的 it 是虛受詞）
PERSON_PRONOUNS = {"i", "me", "you", "he", "him", "she", "her", "we", "us", "they", "them", "everyone", "everybody", "someone", "somebody"}

# 數量詞：most of the kids（不標核心字）
QUANTIFIERS = {
    "most", "some", "all", "half", "each", "one", "many", "much", "few", "both",
    "any", "none", "several", "neither", "either", "lots", "plenty", "part",
    "rest", "majority", "two", "three", "four", "five", "every", "lot", "number", "couple",
    "hundred", "hundreds", "thousand", "thousands", "million", "millions", "dozen", "dozens",
}

# 單位詞：a glass of water（核心字是 of 後面的名詞）
UNIT_NOUNS = {
    "glass", "cup", "piece", "bottle", "bowl", "slice", "pair", "bag", "box",
    "sheet", "loaf", "bar", "can", "carton", "spoonful", "plate", "jar",
    "packet", "pack", "bunch", "drop", "pound", "kilo", "liter", "litre",
}

# 從屬連接詞 → 副詞子句的功能
SUBORDINATORS = {
    "when": "表時間", "while": "表時間", "before": "表時間", "after": "表時間",
    "until": "表時間", "till": "表時間", "since": "表時間", "as": "表時間",
    "once": "表時間", "whenever": "表時間",
    "because": "表原因",
    "where": "表地點", "wherever": "表地點",
    "whereas": "表對比",
    "if": "表條件", "unless": "表條件",
    "although": "表讓步", "though": "表讓步",
    "so": "表目的",
}

# 場所名詞（water the flowers in the garden → 表地點）
PLACE_NOUNS = {
    "garden", "room", "park", "school", "kitchen", "classroom", "house", "home",
    "library", "yard", "field", "playground", "street", "city", "town", "beach",
    "store", "shop", "market", "office", "hospital", "station", "restaurant",
    "bedroom", "bathroom", "hall", "hallway", "gym", "zoo", "museum", "backyard",
    "country", "village", "world", "air", "water", "sky", "sea", "river", "lake",
    "mountain", "hill", "forest", "farm", "camp", "class", "church", "temple",
}

# 動詞 ＋ 介系詞的固定搭配：介系詞後面是動作的對象，不是地點（look at the photo）
VERB_PREP_OBJECT = {
    ("look", "at"), ("look", "for"), ("look", "after"), ("listen", "to"), ("wait", "for"),
    ("laugh", "at"), ("talk", "to"), ("talk", "about"), ("think", "about"), ("think", "of"),
    ("care", "about"), ("belong", "to"), ("depend", "on"), ("bark", "at"), ("shout", "at"),
    ("smile", "at"), ("point", "at"), ("stare", "at"), ("agree", "with"), ("worry", "about"),
    ("dream", "of"), ("dream", "about"), ("hear", "of"), ("hear", "about"), ("speak", "to"),
    ("reply", "to"), ("ask", "for"), ("pay", "for"), ("search", "for"), ("apply", "for"),
    ("run", "into"), ("bump", "into"), ("come", "across"), ("look", "into"), ("deal", "with"),
    ("take", "care"), ("get", "along"), ("take", "after"),
}

# 看起來像被動、其實當形容詞用的過去分詞（is crowded → 句型二 S + Vi + SC）
ADJ_PARTICIPLES = {
    "crowded", "interested", "excited", "bored", "tired", "surprised", "worried",
    "scared", "frightened", "pleased", "satisfied", "married", "closed", "finished",
    "located", "shocked", "disappointed", "amazed", "embarrassed", "confused",
    "exhausted", "delighted", "annoyed", "relaxed", "prepared", "done", "gone",
    "lost", "used", "dressed", "broken", "packed", "filled", "covered",
}

# 名詞 ＋ to（the door to success、the way to school）：to 片語修飾前面的名詞
NOUNS_TAKING_TO = {"door", "way", "key", "road", "path", "answer", "solution", "entrance", "gate", "access", "trip", "visit", "invitation", "journey", "route"}

# 多字的從屬連接詞（Azar 17-1）
# 後面常接同位語子句（that ＋ 完整句子）的名詞：the fact that…、the news that…
APPOSITIVE_NOUNS = {
    "fact", "news", "idea", "belief", "hope", "rumor", "rumour", "feeling", "thought", "possibility",
    "chance", "truth", "evidence", "promise", "fear", "doubt", "question", "suggestion", "opinion",
    "information", "report", "message", "sign", "view", "theory", "claim", "conclusion", "decision",
}

MULTI_SUBORDINATORS = {
    "as soon as": "表時間", "by the time": "表時間", "every time": "表時間",
    "the first time": "表時間", "the last time": "表時間", "the next time": "表時間",
    "as long as": "表條件", "so long as": "表條件", "in case": "表條件", "only if": "表條件",
    "even if": "表讓步", "even though": "表讓步",
    "now that": "表原因",
    "so that": "表目的", "in order that": "表目的",
    "as if": "表方式", "as though": "表方式",  # He talks as if he knew everything.
    "as far as": "表比較",  # I ran as far as I could.；後面接 know、concerned 這類動詞時改標表語氣（見下方）
}

# As far as I know／am concerned／can tell…：「就我所知、就我看來」，說話者表達看法 → 表語氣（跟 In my opinion 一樣）
AS_FAR_AS_OPINION_VERBS = {"know", "concern", "concerned", "tell", "see", "remember", "recall", "understand", "say", "judge"}

# 狀態被動：過去分詞 ＋ 固定介系詞（Azar 11-5、11-6），當形容詞用
STATIVE_PAIRS = {
    ("made", "of"), ("made", "from"), ("known", "for"), ("known", "as"), ("covered", "with"),
    ("filled", "with"), ("located", "in"), ("located", "on"), ("located", "at"), ("located", "near"),
    ("interested", "in"), ("satisfied", "with"), ("married", "to"), ("done", "with"),
    ("finished", "with"), ("related", "to"), ("involved", "in"), ("dressed", "in"),
    ("composed", "of"), ("qualified", "for"), ("prepared", "for"), ("opposed", "to"),
    ("devoted", "to"), ("accustomed", "to"), ("used", "to"), ("scared", "of"), ("tired", "of"),
    ("excited", "about"), ("worried", "about"), ("pleased", "with"), ("disappointed", "in"),
    ("disappointed", "with"), ("surprised", "at"), ("surprised", "by"), ("crowded", "with"),
}

# 需要地點才完整的動詞（七大句型的 SVA、SVOA）：地點修飾語不能省略
PLACE_REQUIRED_VERBS = {"be", "live", "put", "place", "lay", "set", "stay"}

# 形容詞 ＋ 固定介系詞：後面的介系詞片語是「對象」（interested in art、good at math）
ADJ_PREPS = {
    ("interested", "in"), ("good", "at"), ("bad", "at"), ("afraid", "of"), ("proud", "of"),
    ("famous", "for"), ("full", "of"), ("different", "from"), ("similar", "to"), ("kind", "to"),
    ("responsible", "for"), ("popular", "with"), ("excited", "about"), ("worried", "about"),
    ("angry", "with"), ("angry", "at"), ("sorry", "about"), ("sorry", "for"), ("aware", "of"),
    ("fond", "of"), ("tired", "of"), ("busy", "with"), ("familiar", "with"), ("careful", "with"),
    ("happy", "with"), ("happy", "about"), ("ready", "for"), ("late", "for"), ("good", "for"),
    ("bad", "for"), ("close", "to"), ("far", "from"), ("nice", "to"), ("polite", "to"),
}

# 移動動詞：後面的距離、時間是修飾語，不是受詞（sailed a hundred miles、walked two hours）
MOTION_VERBS = {"walk", "run", "sail", "drive", "fly", "swim", "travel", "go", "ride", "move", "jog", "hike", "climb",
                "cycle", "row", "drift", "march", "wander", "crawl", "journey", "commute"}
# 距離單位
DISTANCE_NOUNS = {"mile", "kilometer", "kilometre", "km", "meter", "metre", "foot", "feet", "yard", "block", "step", "inch",
                  "centimeter", "lap", "way"}
