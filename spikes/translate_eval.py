"""翻譯實測：比較 OPUS-MT、Qwen3-4B、Breeze-7B 的英翻中（台灣繁體）品質與速度。

用法：.venv/bin/python spikes/translate_eval.py
結果：docs/翻譯實測-原始結果.md（每句三個模型的翻譯＋花費時間）

速度是在「只用 CPU」的條件下量的（不用 Mac 的 GPU），比較接近將來放上免費主機的情況。
"""
import sys
import time
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parent.parent
THREADS = 4

SENTENCES = [
    # A. 使用者試用時回報的問題
    ("回報", "Voting is an important way for citizens to express their opinions."),
    ("回報", "I give you a big hand."),
    ("回報", "The teacher asked the students to give their classmate a big hand after his excellent speech."),
    # B. 慣用語、片語動詞
    ("慣用語", "It's raining cats and dogs, so let's stay inside."),
    ("慣用語", "Good luck on your performance tonight. Break a leg!"),
    ("慣用語", "I'm feeling a bit under the weather today."),
    ("慣用語", "He let the cat out of the bag about the surprise party."),
    ("慣用語", "She gave up smoking last year."),
    ("慣用語", "While walking to class, I ran into an old friend."),
    # C. 台灣用語
    ("台灣用語", "Many people in Taiwan ride scooters to work every day."),
    ("台灣用語", "You can find more information on our website."),
    ("台灣用語", "Please download the software and watch the video."),
    ("台灣用語", "The quality of this program is very good."),
    ("台灣用語", "We bought some snacks at the convenience store near the MRT station."),
    ("台灣用語", "Night markets are popular with tourists from other countries."),
    # D. 題庫的句子（各種句型）
    ("題庫", "My big sister, who likes to cook, made our whole family a big chocolate cake for Mom's birthday."),
    ("題庫", "Everyone in our class calls the funny boy with the big glasses Little Bear."),
    ("題庫", "The children were so excited about the school trip that they could not sleep the night before."),
    ("題庫", "It is hard to learn English."),
    ("題庫", "There is a cat under the table."),
    ("題庫", "Please keep the door open."),
    ("題庫", "The proposal was approved by the manager."),
    ("題庫", "Because it was raining, we stayed at home."),
    ("題庫", "The book that my sister lent me last week tells the story of a brave girl who saves her village from a terrible flood."),
    ("題庫", "Most of the kids at the party found the new game very fun."),
    ("題庫", "If you want to become a better writer, you should read as many books as possible and practice writing every day."),
]

SYSTEM_PROMPT = (
    "你是專業的英翻中譯者，服務對象是台灣的英文學習者。"
    "請把使用者給的英文句子翻譯成自然、通順的台灣繁體中文，使用台灣的慣用詞彙（例如：軟體、影片、資訊、機車、捷運）。"
    "遇到慣用語或片語，要翻出真正的意思，不要逐字直譯。"
    "只輸出翻譯結果，不要加任何解釋、引號或英文。"
)

s2twp = OpenCC("s2twp")  # 簡體 → 台灣繁體（含台灣用語）
s2t = OpenCC("s2t")


def has_simplified(text):
    return s2t.convert(text) != text


# ---------- OPUS-MT ----------
def load_opus():
    from transformers import MarianMTModel, MarianTokenizer

    name = "Helsinki-NLP/opus-mt-en-zh"
    tok = MarianTokenizer.from_pretrained(name)
    model = MarianMTModel.from_pretrained(name)
    model.eval()

    def translate(text):
        import torch

        # 這個模型可以輸出多種中文，句首加目標語言標記：cmn_Hant＝繁體中文
        batch = tok([f">>cmn_Hant<< {text}"], return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**batch, num_beams=4, max_new_tokens=200)
        raw = tok.decode(out[0], skip_special_tokens=True)
        return raw, s2twp.convert(raw)

    return translate


# ---------- llama.cpp 模型（Qwen3、Breeze） ----------
def load_gguf(filename):
    from llama_cpp import Llama

    path = str(ROOT / "models" / filename)  # 由 spikes/download_models.sh 下載
    llm = Llama(model_path=path, n_ctx=1024, n_threads=THREADS, n_gpu_layers=0, verbose=False)

    def translate(text):
        out = llm.create_chat_completion(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}],
            temperature=0.0,
            max_tokens=200,
        )
        raw = out["choices"][0]["message"]["content"].strip()
        return raw, s2twp.convert(raw)

    return translate, llm


def main():
    models = [
        ("OPUS-MT", lambda: (load_opus(), None)),
        ("Qwen3-4B", lambda: load_gguf("Qwen3-4B-Instruct-2507-Q4_K_M.gguf")),
        ("Breeze-7B", lambda: load_gguf("breeze-7b-instruct-v1_0-q4_k_m.gguf")),
    ]
    only = set(sys.argv[1:])
    results = {}
    for name, loader in models:
        if only and name not in only:
            continue
        t = time.perf_counter()
        translate, llm = loader()
        load_s = time.perf_counter() - t
        rows = []
        for cat, s in SENTENCES:
            t = time.perf_counter()
            raw, fixed = translate(s)
            rows.append((raw, fixed, time.perf_counter() - t))
            print(f"[{name}] {time.perf_counter() - t:5.1f}s  {s}\n          → {raw}", flush=True)
        results[name] = (load_s, rows)
        if llm is not None:
            if hasattr(llm, "metadata"):
                print(f"[{name}] chat template: {'有' if llm.metadata.get('tokenizer.chat_template') else '沒有'}")
            del llm

    import json

    store = ROOT / "spikes" / "translate_results.json"
    saved = json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}
    saved.update({k: [v[0], v[1]] for k, v in results.items()})
    store.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    results = {k: (v[0], [tuple(r) for r in v[1]]) for k, v in saved.items()}

    out = ["# 翻譯實測：原始結果", "", f"環境：Apple M1、只用 CPU（{THREADS} 執行緒）、溫度 0（每次結果相同）", ""]
    out += ["| 模型 | 載入時間 | 平均每句 | 最慢一句 | 輸出含簡體字的句數 |", "|---|---|---|---|---|"]
    for name, (load_s, rows) in results.items():
        times = [r[2] for r in rows]
        simp = sum(has_simplified(r[0]) for r in rows)
        out.append(f"| {name} | {load_s:.1f} 秒 | {sum(times) / len(times):.1f} 秒 | {max(times):.1f} 秒 | {simp} |")
    out.append("")
    for i, (cat, s) in enumerate(SENTENCES):
        out += [f"### {i + 1}.（{cat}）{s}", "", "| 模型 | 翻譯（經 OpenCC 轉台灣繁體） | 秒 |", "|---|---|---|"]
        for name, (_, rows) in results.items():
            raw, fixed, secs = rows[i]
            note = "（原始輸出含簡體）" if has_simplified(raw) else ""
            out.append(f"| {name} | {fixed}{note} | {secs:.1f} |")
        out.append("")
    (ROOT / "docs" / "翻譯實測-原始結果.md").write_text("\n".join(out), encoding="utf-8")
    print("完成 → docs/翻譯實測-原始結果.md")


if __name__ == "__main__":
    main()
