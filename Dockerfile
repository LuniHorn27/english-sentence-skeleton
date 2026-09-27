# 部署用（第 3 階段）：Hugging Face Spaces（Docker）或任何支援 Docker 的主機
FROM python:3.12-slim

# llama-cpp-python（翻譯）安裝時要編譯 C++ 程式
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m app
WORKDIR /home/app/site
# 模型下載到網站資料夾裡（不是 root 的家目錄），網站執行時的 app 帳號才讀得到
ENV HF_HOME=/home/app/site/hf-cache

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m spacy download en_core_web_trf \
 && python -c "from kokoro import KPipeline; KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')" \
 && python -c "from huggingface_hub import hf_hub_download; hf_hub_download('unsloth/Qwen3-4B-Instruct-2507-GGUF', 'Qwen3-4B-Instruct-2507-Q4_K_M.gguf', local_dir='models')"

COPY backend backend
COPY frontend frontend
COPY tests/practice/gold.yaml tests/practice/gold.yaml

USER app
# 模型都在建置時下載好了，執行時不再連線到 Hugging Face
ENV HF_HUB_OFFLINE=1
EXPOSE 7860
# --proxy-headers：主機前面有代理伺服器時，才能取得使用者真正的來源位址（次數限制要用）
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
