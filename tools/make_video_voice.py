"""產生教學影片的中文旁白（video/public/voice/*.wav）。

- 旁白文字在 video/src/narration.json（字幕也用同一份，唸的和看的一模一樣）。
- 中文用中文語音；夾在中間的英文（S、Vt、in the sky…）改用網站的 Kokoro 英文聲音唸，再接起來。
- 每個聲音檔的秒數寫進 video/src/voice-durations.json，影片用它安排每一拍的長度。

執行：
  .venv/bin/python tools/make_video_voice.py                 # 全部旁白
  .venv/bin/python tools/make_video_voice.py --only p3       # 只做 p3 開頭的旁白
  .venv/bin/python tools/make_video_voice.py --engine kokoro-zh --out 某資料夾   # 換中文聲音（試聽比較用）

中文聲音：
  breeze    MediaTek Breeze2-VITS-onnx（台灣口音），模型放在 models/breeze2-vits/
            （模型頁沒寫授權；它的原始模型 BreezyVoice 和官方示範 App 都是 Apache 2.0）
  kokoro-zh Kokoro-82M-v1.1-zh（Apache 2.0，大陸口音），模型放在 models/kokoro-zh/
"""
import argparse
import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import soundfile as sf

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import tts  # noqa: E402

RATE = 24000  # 輸出的取樣率（和英文 Kokoro 一樣）
VIDEO = ROOT / "video"
GAP = 0.06  # 中英文接起來時中間停一下（秒）

# 公式裡的符號要一個字母一個字母唸
LETTERS = {"Vt": "V T", "Vi": "V I", "SC": "S C", "OC": "O C", "IO": "I O", "DO": "D O"}
NUMBERS = {"0 塊": "零塊", "1 塊": "一塊", "2 塊": "兩塊"}


def to_speech(text: str) -> str:
    """字幕文字 → 唸出來的文字"""
    for k, v in NUMBERS.items():
        text = text.replace(k, v)
    text = text.replace("＝", "等於").replace(" + ", " 加 ").replace("：", "，")
    text = re.sub(r"[「」]", "", text)
    return text


def segments(text: str):
    """切成 [(是否英文, 文字)]；英文是連續的拉丁字母（可以有空格）"""
    out = []
    for part in re.split(r"([A-Za-z][A-Za-z' ]*[A-Za-z]|[A-Za-z])", text):
        if not part.strip():
            continue
        is_en = bool(re.fullmatch(r"[A-Za-z' ]+", part))
        if is_en:
            part = " ".join(LETTERS.get(w, w) for w in part.split())
        out.append((is_en, part.strip()))
    return out


def resample(wav: np.ndarray, src: int) -> np.ndarray:
    if src == RATE:
        return wav
    n = int(round(len(wav) * RATE / src))
    return np.interp(np.linspace(0, len(wav) - 1, n), np.arange(len(wav)), wav).astype(np.float32)


def trim(wav: np.ndarray, threshold=0.01) -> np.ndarray:
    """去掉頭尾的靜音，接起來才不會停太久"""
    idx = np.where(np.abs(wav) > threshold)[0]
    return wav[max(0, idx[0] - 240) : idx[-1] + 480] if len(idx) else wav


def level(wav: np.ndarray, target=0.08) -> np.ndarray:
    """中英文兩個聲音的音量調成差不多"""
    rms = float(np.sqrt(np.mean(wav**2))) or 1.0
    return (wav * (target / rms)).clip(-1, 1)


class Breeze:
    def __init__(self):
        import sherpa_onnx

        d = ROOT / "models" / "breeze2-vits"
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(d / "breeze2-vits.onnx"), lexicon=str(d / "lexicon.txt"), tokens=str(d / "tokens.txt")),
                num_threads=4,
            )
        )
        self.tts = sherpa_onnx.OfflineTts(cfg)

    def __call__(self, text, speed):
        audio = self.tts.generate(text, sid=0, speed=speed)
        return resample(np.asarray(audio.samples, dtype=np.float32), audio.sample_rate)


class KokoroZh:
    def __init__(self, voice="zf_001"):
        from kokoro import KModel, KPipeline

        # 模型檔放在 models/kokoro-zh/（從 hexgrad/Kokoro-82M-v1.1-zh 下載）
        d = ROOT / "models" / "kokoro-zh"
        repo = "hexgrad/Kokoro-82M-v1.1-zh"
        model = KModel(repo_id=repo, config=str(d / "config.json"), model=str(d / "kokoro-v1_1-zh.pth"))
        self.pipeline = KPipeline(lang_code="z", repo_id=repo, model=model)
        self.voice = str(d / "voices" / f"{voice}.pt")

    def __call__(self, text, speed):
        return np.concatenate([np.asarray(a) for _, _, a in self.pipeline(text, voice=self.voice, speed=speed)])


def english(text, speed=0.9):
    parts = [np.asarray(a) for _, _, a in tts.get_pipeline()(text, voice=tts.VOICE, speed=speed)]
    return np.concatenate(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="breeze", choices=["breeze", "kokoro-zh"])
    ap.add_argument("--voice", default="zf_001", help="kokoro-zh 的聲音")
    ap.add_argument("--speed", type=float, default=0.7, help="中文語速；數字越小越慢")
    ap.add_argument("--only", default="", help="只做這個開頭的 key")
    ap.add_argument("--out", default=str(VIDEO / "public" / "voice"))
    args = ap.parse_args()

    zh = Breeze() if args.engine == "breeze" else KokoroZh(args.voice)
    lines = json.loads((VIDEO / "src" / "narration.json").read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    dur_file = VIDEO / "src" / "voice-durations.json"
    durations = json.loads(dur_file.read_text()) if dur_file.exists() else {}
    gap = np.zeros(int(GAP * RATE), dtype=np.float32)

    for key, text in lines.items():
        if not key.startswith(args.only):
            continue
        pieces = []
        for is_en, seg in segments(to_speech(text)):
            if is_en:
                pieces += [level(trim(english(seg))), gap]
                continue
            # 中文在逗號、句號後面多停一下，初學者比較聽得清楚
            for phrase in re.findall(r"[^，。！？]+[，。！？]?", seg):
                if not phrase.strip("，。！？ "):
                    continue
                pieces += [level(trim(zh(phrase, args.speed))), gap]
                if phrase[-1] in "，。！？":
                    pieces.append(np.zeros(int((0.12 if phrase[-1] == "，" else 0.2) * RATE), dtype=np.float32))
        wav = np.concatenate(pieces)
        sf.write(out / f"{key}.wav", wav, RATE, subtype="PCM_16")
        durations[key] = round(len(wav) / RATE, 2)
        print(f"{key}: {durations[key]} 秒　{text}")

    if out == VIDEO / "public" / "voice":
        dur_file.write_text(json.dumps(dict(sorted(durations.items())), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
