import os

# Auth
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("MODEL", "llama3.1")
ALLOWED_MODELS = {
    m.strip() for m in os.getenv("MODELS", os.getenv("MODEL", DEFAULT_MODEL)).split(",") if m.strip()
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "")
ADDITIONAL_CORS = [u.strip() for u in os.getenv("ADDITIONAL_CORS", "").split(",") if u.strip()]

CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:300",
    "http://localhost:3001",
    "http://localhost:3003",
    "http://localhost:5173",
]
if FRONTEND_URL:
    CORS_ORIGINS.append(FRONTEND_URL)
if ADDITIONAL_CORS:
    CORS_ORIGINS.extend(ADDITIONAL_CORS)


# DB
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Server
APP_NAME = "OpenAI-compatible proxy for Ollama"
APP_VERSION = "1.1.0"
