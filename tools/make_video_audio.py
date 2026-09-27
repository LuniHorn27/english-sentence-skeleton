"""產生教學影片用的英文例句語音（video/public/audio/*.wav）。

- 例句清單在 video/src/sentences.json（影片程式也讀同一份）。
- 用網站朗讀同一個 Kokoro 聲音（backend/tts.py），速度稍慢，適合初學者。
- 每個聲音檔的秒數寫進 video/src/audio-durations.json，影片用它安排時間。

執行：.venv/bin/python tools/make_video_audio.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import soundfile as sf

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import tts  # noqa: E402

SPEED = 0.85  # 比網站的「一般」（0.95）稍慢
VIDEO = ROOT / "video"
OUT = VIDEO / "public" / "audio"


def main():
    sentences = json.loads((VIDEO / "src" / "sentences.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    pipeline = tts.get_pipeline()
    durations = {}
    for key, text in sentences.items():
        parts = [np.asarray(a) for _, _, a in pipeline(text, voice=tts.VOICE, speed=SPEED)]
        wav = np.concatenate(parts)
        sf.write(OUT / f"{key}.wav", wav, tts.SAMPLE_RATE, subtype="PCM_16")
        durations[key] = round(len(wav) / tts.SAMPLE_RATE, 2)
        print(f"{key}: {durations[key]} 秒　{text}")
    (VIDEO / "src" / "audio-durations.json").write_text(json.dumps(durations, indent=2) + "\n")


if __name__ == "__main__":
    main()
