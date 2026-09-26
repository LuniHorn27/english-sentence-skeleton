"""產生 0-5 的示範分析結果（backend/samples/*.json）。

手寫 JSON 時字元位置很容易算錯，所以用這個小程式從片段文字自動算位置，
再交給 schema 檢查。這些示範檔會在 1-1 當作「假資料」使用。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "backend")
from analyzer.schema import AnalysisResult  # noqa: E402


def build(sentence, specs, clauses, cards, kind="simple", status="ok", message=None):
    """specs：[(文字, 角色, 其他欄位dict)]，依序排列；implicit 片段的文字不在句子裡"""
    chunks, pos = [], 0

    def span(word, within):
        s = sentence.index(word, within[0])
        return {"start": s, "end": s + len(word), "text": word}

    for i, (text, role, extra) in enumerate(specs):
        extra = dict(extra)
        if extra.get("implicit"):
            start = end = pos
        else:
            start = sentence.index(text, pos)
            end = pos = start + len(text)
        rng = (start, end)
        heads = [span(h, rng) for h in extra.pop("heads", [])]
        modifies = extra.pop("modifies", None)
        if modifies:
            modifies = span(modifies, (0,))
        inner = []
        for j, (itext, irole, iextra) in enumerate(extra.pop("inner", [])):
            s = sentence.index(itext, start)
            inner.append({"id": j, "text": itext, "start": s, "end": s + len(itext), "role": irole, **iextra})
        chunks.append(
            {"id": i, "text": text, "start": start, "end": end, "role": role,
             "heads": heads, "modifies": modifies, "inner": inner, **extra}
        )
    return {
        "text": sentence, "status": status, "message": message, "kind": kind,
        "clauses": clauses, "chunks": chunks, "cards": cards,
    }


SAMPLES = {
    "sample_relative_clause": build(
        "My big sister, who likes to cook, made our whole family a big chocolate cake for Mom's birthday.",
        [
            ("My big sister", "S", {"heads": ["sister"], "structure": "名詞片語", "note": "主詞，核心字是 sister；big sister 是「姊姊」。"}),
            ("who likes to cook", "M", {
                "function": "形容詞・修飾", "modifies": "sister", "structure": "形容詞子句",
                "note": "由 who 帶頭的形容詞子句，補充說明姊姊。前後有逗號，表示只是補充，拿掉也不影響主幹。",
                "inner": [("who", "S", {}), ("likes", "Vt", {}), ("to cook", "O", {"structure": "不定詞片語"})],
            }),
            ("made", "Vt", {"note": "make 在這裡是「為某人做某物」，後面接兩個受詞。"}),
            ("our whole family", "IO", {"heads": ["family"], "structure": "名詞片語", "note": "間接受詞：替「誰」做？"}),
            ("a big chocolate cake", "DO", {"heads": ["cake"], "structure": "名詞片語", "note": "直接受詞：做了「什麼」？"}),
            ("for Mom's birthday", "M", {"function": "副詞・表目的", "structure": "介系詞片語", "note": "說明為什麼做蛋糕。"}),
        ],
        [{"index": 0, "pattern": 4, "formula": "S + Vt + IO + DO"}],
        [{"id": "relative_pronoun"}, {"id": "dative_verbs"}],
    ),
    "sample_compound": build(
        "I like tea, but she likes coffee.",
        [
            ("I", "S", {"clause": 0, "note": "子句一的主詞。"}),
            ("like", "Vt", {"clause": 0, "note": "子句一的動詞。"}),
            ("tea", "O", {"clause": 0, "note": "子句一的受詞。"}),
            ("but", "conj", {"clause": 0, "note": "對等連接詞，連接兩個完整的句子，不算進公式。"}),
            ("she", "S", {"clause": 1, "note": "子句二的主詞。"}),
            ("likes", "Vt", {"clause": 1, "note": "子句二的動詞。"}),
            ("coffee", "O", {"clause": 1, "note": "子句二的受詞。"}),
        ],
        [{"index": 0, "pattern": 2, "formula": "S + Vt + O"}, {"index": 1, "pattern": 2, "formula": "S + Vt + O"}],
        [{"id": "coordinating_conj"}],
        kind="compound",
    ),
    "sample_imperative": build(
        "Please keep the door open.",
        [
            ("Please", "M", {"function": "副詞・表語氣", "structure": "副詞", "note": "加上 please 語氣比較客氣。"}),
            ("(You)", "S", {"implicit": True, "note": "省略的主詞，括號表示句子裡看不到，但文法上存在。"}),
            ("keep", "Vt", {"note": "keep 在這裡是「讓…保持某種狀態」。祈使句的動詞用原形。"}),
            ("the door", "O", {"heads": ["door"], "structure": "名詞片語", "note": "受詞，核心字是 door。"}),
            ("open", "OC", {"structure": "形容詞", "note": "受詞補語：門要保持什麼狀態。the door = open。"}),
        ],
        [{"index": 0, "pattern": 5, "formula": "S + Vt + O + OC"}],
        [{"id": "imperative"}],
    ),
}

if __name__ == "__main__":
    out = Path("backend/samples")
    out.mkdir(exist_ok=True)
    for name, sent in SAMPLES.items():
        result = AnalysisResult(input=sent["text"], sentences=[sent])  # 用 schema 檢查
        (out / f"{name}.json").write_text(
            json.dumps(result.model_dump(exclude_none=True), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"{name}.json　標題：{result.sentences[0].header}")
