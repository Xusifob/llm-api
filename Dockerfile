# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app ./app
COPY alembic.ini .
COPY requirements.txt ./requirements.txt

# Minimal deps for a FastAPI OpenAI-compatible proxy to a local LLM (e.g., Ollama)
RUN  pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

