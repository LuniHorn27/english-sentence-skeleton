#!/bin/bash
# 下載翻譯模型，可續傳（中途斷線再執行一次即可接著下載）。
#   bash spikes/download_models.sh         只下載正式網站用的 Qwen3-4B（2.5 GB）
#   bash spikes/download_models.sh --all   連同翻譯實測比較過的 OPUS-MT、Breeze-7B 一起下載（再加約 4.8 GB）
set -u
cd "$(dirname "$0")/.."
HF=https://huggingface.co
mkdir -p models

get() {
  echo "開始下載 $2"
  until curl -L -C - --retry 20 --retry-delay 5 -s -S -o "models/$2" "$HF/$1/resolve/main/$2"; do
    echo "中斷，5 秒後續傳 $2"; sleep 5
  done
  echo "$2 下載完成（$(du -h "models/$2" | cut -f1)）"
}
get unsloth/Qwen3-4B-Instruct-2507-GGUF Qwen3-4B-Instruct-2507-Q4_K_M.gguf

if [ "${1:-}" = "--all" ]; then
  # OPUS-MT：用 huggingface_hub 下載，關掉容易卡住的 xet 傳輸
  HF_HUB_DISABLE_XET=1 .venv/bin/python -c "
from huggingface_hub import hf_hub_download
for fn in ['config.json','generation_config.json','source.spm','target.spm','tokenizer_config.json','vocab.json','README.md','pytorch_model.bin']:
    hf_hub_download('Helsinki-NLP/opus-mt-en-zh', fn)
print('OPUS-MT 下載完成', flush=True)
"
  get YC-Chen/Breeze-7B-Instruct-v1_0-GGUF breeze-7b-instruct-v1_0-q4_k_m.gguf
fi
echo "全部下載完成"
