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
    "build", "bake", "draw", "fetch", "order",
}

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
TONE_ADVERBS = {"please", "also", "too", "only", "just", "even", "really", "actually", "certainly", "surely", "maybe", "perhaps"}

# 天氣、狀況名詞（in the heavy rain → 表狀況）
CONDITION_NOUNS = {"rain", "snow", "wind", "storm", "sun", "sunshine", "heat", "cold", "dark", "darkness", "fog", "weather", "silence", "hurry", "danger", "trouble"}

# 人（with his friends → 表伴隨）
PERSON_NOUNS = {
    "friend", "family", "mother", "mom", "mum", "dad", "father", "parent", "brother",
    "sister", "teacher", "classmate", "people", "child", "kid", "grandma",
    "grandpa", "grandmother", "grandfather", "uncle", "aunt", "cousin", "son",
    "daughter", "wife", "husband", "boy", "girl", "man", "woman", "team",
    "student", "neighbor", "neighbour", "partner", "dog", "cat", "pet",
}

# 數量詞：most of the kids（不標核心字）
QUANTIFIERS = {
    "most", "some", "all", "half", "each", "one", "many", "much", "few", "both",
    "any", "none", "several", "neither", "either", "lots", "plenty", "part",
    "rest", "majority", "two", "three", "four", "five", "every",
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
