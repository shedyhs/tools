FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LITEPARSE_MODEL_DIR=/opt/liteparse/models

RUN pip install --no-cache-dir liteparse==2.21.3 fastapi==0.115.12 uvicorn==0.34.2 python-multipart==0.0.20

# Baixa o OCRia-nano-1 (~60 MB) na imagem, para funcionar offline
RUN lit models pull ocria-nano && lit models list

RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY app.py .
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
