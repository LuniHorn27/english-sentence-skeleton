"""產生「動詞句型字典」草稿：每個動詞可以用在哪幾種句型。

資料來源（前兩個要先下載到 data/，data/ 不進版本控制）：
  1. VerbNet 3.4（美國科羅拉多大學，可商用，要附版權聲明）
       git clone --depth 1 https://github.com/cu-clear/verbnet.git data/verbnet
  2. ECDICT（MIT）：只用字典裡標的 vt.／vi.，判斷能不能當及物／不及物
       https://github.com/skywind3000/ECDICT → data/ecdict/ecdict.csv
  3. 賴世雄《教你學英語語法》上冊列出的動詞（只記動詞和頁碼，不抄例句）
  4. 我們自己的字表（backend/analyzer/lexicon.py）
  5. 練習題標準答案（tests/practice/gold.yaml；考試題封存，不讀）

用法：
  python tools/build_verb_dict.py
輸出：
  backend/analyzer/verb_patterns.yaml   字典本身（之後給分析程式檢查用）
  docs/動詞句型字典-待確認.md             只列出來源互相矛盾、需要人工確認的動詞

句型一律用公式代號，避免和句型編號混淆：
  SV = 句型一 S+Vi、SVC = 句型二 S+V+SC、SVO = 句型三 S+Vt+O、
  SVOC = 句型四 S+Vt+O+OC、SVOO = 句型五 S+Vt+IO+DO
"""
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.analyzer import lexicon as L  # noqa: E402

VERBNET_DIR = ROOT / "data/verbnet/verbnet3.4"
ECDICT_CSV = ROOT / "data/ecdict/ecdict.csv"
GOLD = ROOT / "tests/practice/gold.yaml"
OUT_YAML = ROOT / "backend/analyzer/verb_patterns.yaml"
OUT_REVIEW = ROOT / "docs/動詞句型字典-待確認.md"

CODES = ["SV", "SVC", "SVO", "SVOC", "SVOO"]
LABEL = {
    "SV": "句型一 S+Vi",
    "SVC": "句型二 S+V+SC",
    "SVO": "句型三 S+Vt+O",
    "SVOC": "句型四 S+Vt+O+OC",
    "SVOO": "句型五 S+Vt+IO+DO",
}
# 內部代號（schema.py 的 pattern）→ 公式代號
INTERNAL = {1: "SV", 2: "SVO", 3: "SVC", 4: "SVOO", 5: "SVOC"}

# ── 賴世雄《教你學英語語法》上冊列出的動詞（書本頁碼） ──
LAI = {
    "SVC": {  # p.24～33 不完全不及物動詞（連綴動詞）
        "be", "become", "turn", "get", "seem", "appear",
        "look", "sound", "smell", "taste", "feel",
    },
    "SVOC": {  # p.44～60 不完全及物動詞
        "make", "have", "bid", "get", "let",  # 使役
        "force", "ask", "urge", "compel", "tell", "push", "seduce", "entice", "wish", "want",  # ＋ O ＋ to V
        "see", "observe", "watch", "hear", "feel",  # 知覺（look at、listen to 是片語，另計）
        "elect", "assign",  # 任命
        "regard", "view", "take", "consider", "deem", "think", "believe", "find",  # 認定
        "change", "turn",  # 轉變（＋ into）
        "set", "paint", "strike", "cry", "render", "drive", "name", "call", "leave", "keep", "help",
    },
    "SVOO": {  # p.60～65 授予動詞（只收可以直接接兩個受詞的）
        "give", "lend", "buy", "ask", "send", "tell", "teach", "make", "offer",
    },
}

# ── 我們自己的字表 ──
LEXICON = {
    "SVC": set(L.LINKING_VERBS),
    "SVOO": set(L.DATIVE_VERBS),
    "SVOC": set(L.CAUSATIVE_PERCEPTION),
}


# ───────────────────────── VerbNet ─────────────────────────

NP_TOKENS = ("NP", "NP-Dative", "NP-dative", "NP-Fulfilling", "NP-ATTR-POS", "NP-PRO-ARB")
ADJ_TOKENS = ("ADJ", "ADJP", "ADJP-Result")
CLAUSE_TOKENS = ("that", "what", "how", "whether", "whether/if", "when", "S", "S_INF", "S-INF",
                 "S_ING", "wh-S_INF", "for", "if", "why", "where")
SKIP_TOKENS = ("together", "apart", "up", "down", "out", "off", "away", "back", "(PP)")
RECIPIENT_ROLES = {"Recipient", "Beneficiary", "Goal", "Destination"}
COMPLEMENT_ROLES = {"Attribute", "Result", "Predicate", "Product"}


def direct_np_roles(frame):
    """動詞後面、前面沒有介系詞的名詞，依序列出語意角色"""
    roles, after_verb, after_prep = [], False, False
    for e in frame.find("SYNTAX"):
        if e.tag == "VERB":
            after_verb = True
            continue
        if not after_verb:
            continue
        if e.tag == "PREP":
            after_prep = True
        elif e.tag == "NP":
            if not after_prep:
                roles.append(e.get("value"))
            after_prep = False
    return roles


def subject_role(frame):
    for e in frame.find("SYNTAX"):
        if e.tag == "VERB":
            return None
        if e.tag == "NP":
            return e.get("value")
    return None


def has_prep_after_verb(frame):
    seen = False
    for e in frame.find("SYNTAX"):
        if e.tag == "VERB":
            seen = True
        elif seen and e.tag == "PREP":
            return True
    return False


def classify(frame):
    """把一個 VerbNet 句子結構換算成五大句型；回傳 (代號, 是否有疑問) 或 None（略過）"""
    primary = frame.find("DESCRIPTION").get("primary").strip()
    if primary == "Passive" or "S-Quote" in primary or "Middle" in primary:
        return None  # 被動、直接引述、中間語態（The bread cuts easily）不列入
    toks = primary.split()
    if "V" not in toks:
        return None
    vi = toks.index("V")
    subj, post = toks[:vi], toks[vi + 1:]
    if subj and (subj[0].startswith("PP") or subj[0] in ("There", "It")):
        return "SV", False  # 倒裝，或 It 當虛主詞（It matters that…）：後面的名詞／子句其實是主詞
    core = [t for t in post
            if not t.split(".")[0].startswith("PP") and t.split(".")[0] not in ("ADV", "ADVP", "P")
            and t not in SKIP_TOKENS]
    if not core:
        return "SV", False
    roles = direct_np_roles(frame)
    first, fb = core[0], core[0].split(".")[0]
    # 介系詞片語後面才出現的子句或名詞（relies on him to help），換算不可靠
    pp_first = post.index(first) > 0 and post[0].split(".")[0].startswith("PP")
    got = _classify_core(frame, core, roles, first, fb, post)
    return (got[0], True) if pp_first and got[0] != "SV" else got


def _classify_core(frame, core, roles, first, fb, post):

    if fb in ADJ_TOKENS:
        return ("SVC", False) if len(core) == 1 else ("SVOC", False)
    if fb in CLAUSE_TOKENS or fb == "to":
        if fb == "S_INF" and subject_role(frame) not in ("Agent", "Experiencer", "Causer"):
            return "SVC", True  # He seemed to come：賴世雄把 seem ＋ 不定詞算主詞補語
        return "SVO", False  # 受詞是子句、不定詞或動名詞
    if fb not in NP_TOKENS:
        return "SVO", True

    if len(core) == 1:
        if first == "NP" and post == ["NP"] and roles and roles[0] in COMPLEMENT_ROLES \
                and subject_role(frame) not in ("Agent", "Causer", "Instrument", "Asset", "Material"):
            return "SVC", False  # He became a banker.（主詞不是動作者；Martha carved a toy 不算）
        return "SVO", False

    second, sb = core[1], core[1].split(".")[0]
    if sb in ADJ_TOKENS or sb == "to":
        return "SVOC", False  # made him angry／judged him to be a good man
    if sb == "S":
        return "SVOC", False  # let us smoke
    if sb in ("S_INF", "S-INF"):
        return "SVOC", True  # asked him to leave；但也可能是表目的（used the cupboard to store food）
    if sb == "S_ING":
        return ("SVO", False) if has_prep_after_verb(frame) else ("SVOC", True)
    if sb in CLAUSE_TOKENS:
        return "SVOO", False  # told him that…
    if sb in NP_TOKENS or sb == "P":
        r0 = roles[0] if roles else None
        r1 = roles[1] if len(roles) > 1 else None
        if r1 and r1.startswith("Co-"):
            return "SVO", False
        if "ative" in fb or r0 in RECIPIENT_ROLES or first.split(".")[-1].capitalize() in RECIPIENT_ROLES:
            return "SVOO", False
        if r1 in COMPLEMENT_ROLES or second.split(".")[-1].capitalize() in COMPLEMENT_ROLES:
            return "SVOC", False
        if r1 == "Asset" or second.endswith("asset"):
            return "SVOO", False  # billed me $10
        if r1 == "Extent" or second.endswith("extent"):
            return "SVO", False
        return "SVOO", True
    return "SVO", True


def load_verbnet():
    """回傳 {動詞: {代號: [(類別, 例句, 有疑問)]}}；子類別會繼承上層類別的句子結構"""
    result = defaultdict(lambda: defaultdict(list))
    stats = Counter()

    def walk(cls, inherited):
        frames = inherited + list(cls.find("FRAMES"))
        members = [m.get("name") for m in cls.find("MEMBERS")]
        for f in frames:
            got = classify(f)
            stats["frames"] += 1
            if got is None:
                stats["skipped"] += 1
                continue
            code, doubtful = got
            ex = f.find("EXAMPLES/EXAMPLE")
            example = " ".join((ex.text or "").split()) if ex is not None else ""
            for m in members:
                if "_" in m or "-" in m:
                    continue  # 片語動詞（come_out、give-back）先不收
                result[m][code].append((cls.get("ID"), example, doubtful))
        for sub in cls.findall("SUBCLASSES/VNSUBCLASS"):
            walk(sub, frames)

    for path in sorted(VERBNET_DIR.glob("*.xml")):
        walk(ET.parse(path).getroot(), [])
    return result, stats


# ───────────────────────── ECDICT ─────────────────────────

def load_ecdict():
    """回傳 {單字: 資訊}，只留有動詞解釋的字；另外回傳 {變化形: 原形}"""
    if not ECDICT_CSV.exists():
        return None, {}
    info, lemma_of = {}, {}
    with ECDICT_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            word = row["word"]
            if not re.fullmatch(r"[a-z]+", word):
                continue
            tr = row["translation"].replace("\\n", "\n")
            vt = bool(re.search(r"(^|\n)\s*vt\.", tr))
            vi = bool(re.search(r"(^|\n)\s*vi\.", tr))
            v = vt or vi or bool(re.search(r"(^|\n)\s*v\.", tr))
            for part in row["exchange"].split("/"):
                if part.startswith(("p:", "d:", "i:", "3:")):
                    lemma_of.setdefault(part[2:], word)
            if not v:
                continue
            tags = set(row["tag"].split())
            info[word] = {
                "vt": vt,
                "vi": vi,
                "common": row["oxford"] == "1" or bool(tags & {"zk", "gk"}),
                "tags": tags,
            }
    return info, lemma_of


# ───────────────────────── 練習題 ─────────────────────────

BE_FORMS = {"am", "is", "are", "was", "were", "been", "being", "'m", "'s", "'re"}

def gold_verbs(lemma_of):
    """練習題裡每一句的主要動詞（原形）和標準答案的句型"""
    out = defaultdict(set)
    for item in yaml.safe_load(GOLD.read_text(encoding="utf-8")):
        code = INTERNAL[item["pattern"]]
        if item.get("passive"):
            continue  # 被動句的動詞形式和主動不同，不拿來當證據
        verbs = [c["text"] for c in item["chunks"] if c["role"] in ("Vt", "Vi", "V")]
        if not verbs:
            continue
        word = verbs[0].split()[-1].lower()
        word = "be" if word in BE_FORMS else word
        out[lemma_of.get(word, word)].add((code, item["id"]))
    return out


# ───────────────────────── 合併 ─────────────────────────

def build():
    vn, vn_stats = load_verbnet()
    ec, lemma_of = load_ecdict()
    gold = gold_verbs(lemma_of)

    lai_verbs = set().union(*LAI.values())
    lex_verbs = set().union(*LEXICON.values())
    common = {w for w, i in (ec or {}).items() if i["common"]}
    # 字典收錄範圍：常用動詞 ＋ 其他來源提到的動詞；VerbNet 裡的其他動詞也收，但標成不常用
    vocab = set(vn) | lai_verbs | lex_verbs | set(gold) | common

    entries, review = [], defaultdict(list)
    for verb in sorted(vocab):
        src = defaultdict(set)
        examples = {}
        for code, hits in vn.get(verb, {}).items():
            if all(d for _, _, d in hits):
                src[code].add("VerbNet?")  # 只有換算時有疑問的結構
            else:
                src[code].add("VerbNet")
            ex = next((e for _, e, d in hits if e and not d), None)
            if ex:
                examples[code] = ex
        if ec and verb in ec:
            if ec[verb]["vt"]:
                src["SVO"].add("ECDICT")
            if ec[verb]["vi"]:
                src["SV"].add("ECDICT")
        for code, verbs in LAI.items():
            if verb in verbs:
                src[code].add("賴世雄")
        for code, verbs in LEXICON.items():
            if verb in verbs:
                src[code].add("字表")
        for code, _id in gold.get(verb, ()):
            src[code].add("題庫")
        if not src:
            continue

        is_common = verb in common or verb in lai_verbs or verb in lex_verbs or verb in gold
        entry = {
            "verb": verb,
            "common": is_common,
            "patterns": {c: sorted(src[c]) for c in CODES if c in src},
        }
        if examples:
            entry["examples"] = {c: examples[c] for c in CODES if c in examples}
        entries.append(entry)

        if is_common:
            flag_review(verb, src, ec, review)

    return entries, review, vn_stats, ec is not None


TRUSTED = {"賴世雄", "字表", "題庫"}


def flag_review(verb, src, ec, review):
    """只挑出真的需要人判斷的情況"""
    # 1. VerbNet 說可以接補語／兩個受詞，但台灣教材和我們的字表都沒有
    for code in ("SVC", "SVOC", "SVOO"):
        if code in src and not (src[code] & TRUSTED):
            review[code].append((verb, sorted(src[code])))
    # 2. 題庫或賴世雄用到的句型，VerbNet 和 ECDICT 都沒有（可能是 VerbNet 漏收，也可能是我們標錯）
    for code, s in src.items():
        if s & {"題庫", "賴世雄"} and not s & {"VerbNet", "ECDICT", "VerbNet?"}:
            review["missing"].append((verb, code, sorted(s)))
    # 3. ECDICT 只標不及物，VerbNet 卻說可以接受詞（或反過來）
    if ec and verb in ec:
        vt, vi = ec[verb]["vt"], ec[verb]["vi"]
        vn_codes = {c for c, s in src.items() if s & {"VerbNet"}}
        if vi and not vt and vn_codes & {"SVO", "SVOC", "SVOO"} and not (src.get("SVO", set()) & TRUSTED):
            review["vi_only"].append((verb, sorted(vn_codes)))


def write_yaml(entries):
    header = (
        "# 動詞句型字典（草稿，由 tools/build_verb_dict.py 產生，請勿手動修改；要改請改程式或審核清單）\n"
        "# 每個動詞列出可以用的句型，以及是哪些來源說的：\n"
        "#   VerbNet＝VerbNet 3.4 換算、VerbNet?＝換算時有疑問、ECDICT＝字典標 vt./vi.、\n"
        "#   賴世雄＝《教你學英語語法》上冊、字表＝lexicon.py、題庫＝練習題標準答案\n"
        "# 句型代號：SV 句型一 S+Vi、SVC 句型二 S+V+SC、SVO 句型三 S+Vt+O、\n"
        "#           SVOC 句型四 S+Vt+O+OC、SVOO 句型五 S+Vt+IO+DO\n"
        "# common: true＝常用動詞（牛津 3000、中國中考／高考字表、或其他來源提到）\n"
        "#\n"
        "# 本檔部分內容衍生自 VerbNet 3.4。\n"
        "# VerbNet 3.0 (or 3.X) Copyright 2009 by University of Colorado. All rights reserved.\n"
        "# 依其授權條款使用（含免責聲明），條款全文見 backend/analyzer/LICENSE-VerbNet.txt。\n"
        "# 例句（examples）取自 VerbNet。及物／不及物資訊取自 ECDICT（MIT 授權）。\n"
    )
    body = yaml.safe_dump(entries, allow_unicode=True, sort_keys=False, width=120)
    OUT_YAML.write_text(header + body, encoding="utf-8")


def write_review(review, entries, vn_stats, has_ecdict):
    by_verb = {e["verb"]: e for e in entries}
    n_common = sum(e["common"] for e in entries)
    lines = [
        "# 動詞句型字典：待確認清單",
        "",
        "> 由 `tools/build_verb_dict.py` 自動產生。字典本身在 `backend/analyzer/verb_patterns.yaml`。",
        "> 這裡只列**常用動詞**中，來源互相矛盾、需要人判斷的地方。",
        "",
        "## 概況",
        "",
        f"- 收錄動詞：{len(entries)} 個，其中常用 {n_common} 個",
        f"- VerbNet 句子結構：{vn_stats['frames']} 個，略過 {vn_stats['skipped']} 個（被動、直接引述、中間語態）",
        f"- ECDICT：{'已使用' if has_ecdict else '⚠️ 尚未下載，這一版沒有及物／不及物資訊'}",
        "",
    ]

    def fmt(verb):
        e = by_verb[verb]
        return "、".join(LABEL[c] for c in e["patterns"])

    sections = [
        ("SVC", "句型二 S+V+SC：只有 VerbNet 說可以接主詞補語", "VerbNet 的「補語」範圍比台灣教材寬（例如 *come undone*、*fall ill*）。請確認哪些要留。"),
        ("SVOC", "句型四 S+Vt+O+OC：只有 VerbNet 說可以接受詞補語", "包含「動詞＋受詞＋形容詞」的結果用法（*wipe the table clean*），台灣教材通常也算句型四。"),
        ("SVOO", "句型五 S+Vt+IO+DO：只有 VerbNet 說可以接兩個受詞", ""),
    ]
    for code, title, note in sections:
        items = review.get(code, [])
        lines += [f"## {title}（{len(items)} 個）", ""]
        if note:
            lines += [note, ""]
        if items:
            lines += ["| 動詞 | 字典目前的句型 | 這個句型的來源 |", "|---|---|---|"]
            lines += [f"| {v} | {fmt(v)} | {'、'.join(s)} |" for v, s in items]
        lines.append("")

    items = review.get("missing", [])
    lines += [f"## 題庫或賴世雄用到、但 VerbNet 和 ECDICT 都沒有的句型（{len(items)} 個）", "",
              "可能是 VerbNet 漏收，也可能是題庫標錯。", ""]
    if items:
        lines += ["| 動詞 | 句型 | 來源 |", "|---|---|---|"]
        lines += [f"| {v} | {LABEL[c]} | {'、'.join(s)} |" for v, c, s in items]
    lines.append("")

    items = review.get("vi_only", [])
    lines += [f"## ECDICT 只標不及物（vi.），VerbNet 卻說可以接受詞（{len(items)} 個）", ""]
    if items:
        lines += ["| 動詞 | VerbNet 的句型 |", "|---|---|"]
        lines += [f"| {v} | {'、'.join(LABEL[c] for c in s)} |" for v, s in items]
    lines.append("")
    OUT_REVIEW.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    entries, review, vn_stats, has_ecdict = build()
    write_yaml(entries)
    write_review(review, entries, vn_stats, has_ecdict)
    print(f"動詞 {len(entries)} 個（常用 {sum(e['common'] for e in entries)} 個）")
    for k, v in review.items():
        print(f"  待確認 {k}: {len(v)}")
