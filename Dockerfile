# 部署用（第 3 階段）：Hugging Face Spaces（Docker）或任何支援 Docker 的主機
FROM python:3.12-slim

RUN useradd -m app
WORKDIR /home/app/site

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m spacy download en_core_web_trf

COPY backend backend
COPY frontend frontend
COPY tests/practice/gold.yaml tests/practice/gold.yaml

USER app
EXPOSE 7860
# --proxy-headers：主機前面有代理伺服器時，才能取得使用者真正的來源位址（次數限制要用）
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
