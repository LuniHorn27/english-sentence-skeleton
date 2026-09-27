# 部署用（第 3 階段）：Hugging Face Spaces（Docker）或任何支援 Docker 的主機
FROM python:3.12-slim

# llama-cpp-python（翻譯）安裝時要編譯 C++ 程式
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
 && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces 用 uid 1000 執行網站；第一個建立的帳號就是 1000
RUN useradd -m -u 1000 app
WORKDIR /home/app/site
# 網站資料夾交給 app 帳號，執行時才能建立 data/（使用者回饋）
RUN chown app:app /home/app/site

# ---------- 套件（要用 root 安裝） ----------
COPY requirements.txt .
# torch 先裝「只用 CPU」的版本：免費主機沒有顯示卡，GPU 版多好幾 GB
RUN pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt \
 && python -m spacy download en_core_web_trf \
 && python -m spacy download en_core_web_sm

# ---------- 模型（用 app 帳號下載，執行時才讀寫得到） ----------
USER app
ENV HF_HOME=/home/app/site/hf-cache
RUN python -c "from kokoro import KPipeline; KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')" \
 && python -c "from huggingface_hub import hf_hub_download; hf_hub_download('unsloth/Qwen3-4B-Instruct-2507-GGUF', 'Qwen3-4B-Instruct-2507-Q4_K_M.gguf', local_dir='models')"

COPY --chown=app:app backend backend
COPY --chown=app:app frontend frontend
COPY --chown=app:app tests/practice/gold.yaml tests/practice/gold.yaml

# 模型都在建置時下載好了，執行時不再連線到 Hugging Face
ENV HF_HUB_OFFLINE=1
EXPOSE 7860
# --proxy-headers：主機前面有代理伺服器時，才能取得使用者真正的來源位址（次數限制要用）
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
