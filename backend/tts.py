"""朗讀：用 Kokoro-82M（Apache 2.0 開源語音模型）在伺服器上產生英文語音。

- 所有人聽到的聲音都一樣，不受瀏覽器、作業系統影響。
- 產生過的句子暫存在記憶體（最多 200 句），同一句第二次朗讀不用重新產生；
  不寫進硬碟，伺服器重新啟動就清空（隱私：不保存使用者輸入的句子）。
- 完全在自己的伺服器上執行，不呼叫任何外部服務，也不需要 API 金鑰。
"""
import importlib.util
import io
import threading
from collections import OrderedDict

import numpy as np

CACHE_SIZE = 200
SAMPLE_RATE = 24000
MAX_CHARS = 500
VOICE = "af_heart"  # 美式英文女聲（Kokoro 評價最好的聲音）
SPEEDS = {"normal": 0.95, "slow": 0.75}

_pipeline = None
_lock = threading.Lock()  # 模型一次只處理一個請求，避免同時佔用太多記憶體
_cache: "OrderedDict[tuple, bytes]" = OrderedDict()


def is_available() -> bool:
    """有沒有安裝朗讀套件。精簡版伺服器（免費主機）不裝，網頁會改用瀏覽器內建語音"""
    return all(importlib.util.find_spec(m) is not None for m in ("kokoro", "soundfile"))


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        import warnings

        warnings.filterwarnings("ignore")
        from kokoro import KPipeline

        _pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    return _pipeline


def synthesize(text: str, speed: str = "normal") -> bytes:
    """回傳 WAV 格式的聲音"""
    import soundfile as sf

    text = " ".join(text.split())[:MAX_CHARS]
    rate = SPEEDS.get(speed, SPEEDS["normal"])
    key = (VOICE, rate, text)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        parts = [audio for _, _, audio in get_pipeline()(text, voice=VOICE, speed=rate)]
    wav = np.concatenate([np.asarray(p) for p in parts]) if parts else np.zeros(1, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, wav, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    data = buf.getvalue()
    with _lock:
        _cache[key] = data
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return data
