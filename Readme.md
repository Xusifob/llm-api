# OpenAI-Compatible API (Ollama backend) + Migrations

## Stack
- FastAPI (OpenAI-style `/v1/*`)
- Ollama (local LLM runtime)
- SQLAlchemy + Alembic (SQLite or Postgres)
- Bearer auth via `OPENAI_API_KEY`

## Prereqs
- Docker & docker-compose
- `.env` with:
  ```env
  OPENAI_API_KEY=sk-xxx
  MODELS=llama3.1,mistral:7b-instruct
  OLLAMA_HOST=http://ollama:11434
  MODEL=llama3.1
  # SQLite mounted file
  SQLITE_FILE=sqlite:////data/sqlite.db

### Search

- List conversations (search in titles and messages):
  GET /conversations?search=<term>

- List messages in one conversation (search in messages):
  GET /conversations/{conversation_id}/messages?search=<term>
