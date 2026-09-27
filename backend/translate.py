"""中文翻譯：用 Qwen3-4B-Instruct（Apache 2.0 開源模型）在伺服器上把英文翻成台灣繁體中文。

- 選這個模型的原因見 docs/翻譯實測-比較報告.md（26 句實測，品質最好、速度第二快）。
- 模型輸出偶爾有簡體字，一律經過 OpenCC（s2twp）轉成台灣繁體與台灣用語。
- 句子裡有慣用語時（例如 give someone a big hand），把真正的意思告訴模型，避免照字面翻。
- 原文是 and、翻譯卻變成「但是」時，指明連接詞再翻一次。
- 翻譯裡如果留下英文單字（原句的專有名詞、縮寫除外），加一句提醒再翻一次。
- 翻過的句子暫存在記憶體（最多 500 句）；不寫進硬碟，伺服器重新啟動就清空（隱私）。
- 完全在自己的伺服器上執行，不呼叫任何外部服務。
"""
import os
import re
import threading
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_FILE = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
MODEL_PATH = Path(os.environ.get("TRANSLATE_MODEL", ROOT / "models" / MODEL_FILE))
THREADS = int(os.environ.get("TRANSLATE_THREADS", min(4, os.cpu_count() or 1)))
CACHE_SIZE = 500
MAX_CHARS = 2000  # 和分析的上限一樣；一整句不會被截斷

SYSTEM_PROMPT = (
    "你是專業的英翻中譯者，服務對象是台灣的英文學習者。"
    "請把使用者給的英文句子翻譯成自然、通順的台灣繁體中文，使用台灣的慣用詞彙（例如：軟體、影片、資訊、機車、捷運）。"
    "遇到慣用語或片語，要翻出真正的意思，不要逐字直譯。"
    "連接詞要照原文的意思翻（and＝而且、並且、和；but＝但是；so＝所以），不要自己改成別的關係。"
    "只輸出翻譯結果，不要加任何解釋、引號或英文。"
)
CONTRAST_WORDS = re.compile(r"\b(but|yet|however|although|though|while|whereas|still|instead)\b", re.I)
CONJ_NOTE = "注意：原文的連接詞是 and（而且、並且、和），不是 but，翻譯裡不要出現「但、可是、不過、卻」。"


def and_as_but(zh: str, source: str) -> bool:
    """原文只有 and、沒有轉折字，翻譯卻出現「但是」之類的字"""
    return bool(re.search(r"\band\b", source, re.I)) and not CONTRAST_WORDS.search(source) \
        and bool(re.search(r"但|可是|不過|卻", zh))


RETRY_NOTE = "注意：每個英文單字都要翻成中文（人名、地名、縮寫可以保留）。"

_llm = None
_converter = None
_load_error = None
_lock = threading.Lock()  # 模型一次只翻一句，避免同時佔用太多記憶體和 CPU
_cache: "OrderedDict[tuple, str]" = OrderedDict()


def is_available() -> bool:
    return MODEL_PATH.exists() and _load_error is None


def load():
    """載入模型（約 15 秒）；啟動時在背景呼叫，第一次翻譯就不用等"""
    global _llm, _converter, _load_error
    with _lock:
        if _llm is not None:
            return
        try:
            from llama_cpp import Llama
            from opencc import OpenCC

            _converter = OpenCC("s2twp")
            _llm = Llama(model_path=str(MODEL_PATH), n_ctx=2048, n_threads=THREADS, n_gpu_layers=0, verbose=False)
        except Exception as e:
            _load_error = e
            raise


def leftover_english(zh: str, source: str) -> list[str]:
    """翻譯裡留下的英文單字；原句中的專有名詞（句中大寫開頭的字，如 Taiwan）和縮寫（如 MRT）不算。
    句首的字不算專有名詞（例如 Everyone 只是剛好在句首）。"""
    keep = set()
    for m in re.finditer(r"[A-Za-z]+", source):
        w = m.group()
        at_start = not source[: m.start()].strip() or source[: m.start()].rstrip()[-1] in ".!?\"'“"
        if (w.isupper() and len(w) > 1) or (w[0].isupper() and not at_start):
            keep.add(w)
    return [w for w in re.findall(r"[A-Za-z]{2,}", zh) if w not in keep]


# OpenCC 沒有處理到的台灣用字：香菸、抽菸、戒菸用「菸」（煙霧的「煙」不變）
TAIWAN_FIXES = [
    (re.compile(r"(抽|吸|戒|點)(了|過|完|根)?煙"), r"\1\2菸"),
    (re.compile(r"香煙|煙草|煙酒|煙蒂|煙灰缸"), lambda m: m.group().replace("煙", "菸")),
    # OpenCC 會把「通過」一律轉成「透過」；考試、審核的「通過」要改回來
    (re.compile(r"(沒有|沒|未|不|順利|已經|才|都)透過"), r"\1通過"),
    (re.compile(r"透過(了|考試|測驗|檢查|審核|面試)"), r"通過\1"),
]


def taiwan_fix(zh: str) -> str:
    for pattern, repl in TAIWAN_FIXES:
        zh = pattern.sub(repl, zh)
    return zh


def _generate(text: str, extra: str = "") -> str:
    out = _llm.create_chat_completion(
        messages=[{"role": "system", "content": SYSTEM_PROMPT + extra}, {"role": "user", "content": text}],
        temperature=0.0,
        max_tokens=800,
    )
    return taiwan_fix(_converter.convert(out["choices"][0]["message"]["content"].strip()))


def translate(text: str, hints: str = "") -> str:
    """hints：慣用語的真正意思（由 analyzer/phrases.py 的 translation_hints 產生）"""
    text = " ".join(text.split())[:MAX_CHARS]
    extra = f"這句話裡的慣用語：{hints}" if hints else ""
    key = (text, extra)
    if _llm is None:
        load()
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        zh = _generate(text, extra)
        if leftover_english(zh, text):
            retry = _generate(text, extra + RETRY_NOTE)
            if len(leftover_english(retry, text)) < len(leftover_english(zh, text)):
                zh = retry
        if and_as_but(zh, text):
            retry = _generate(text, extra + CONJ_NOTE)
            if not and_as_but(retry, text) and not leftover_english(retry, text):
                zh = retry
        _cache[key] = zh
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return zh
