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

## Auth

Create a user and obtain an API token:

- `POST /auth/signup` – create a new user
- `POST /auth/login` – obtain a token for an existing user

Include the token on all other requests via the `Authorization` header:

```
Authorization: Bearer <token>
```

## Conversations API

- `POST /conversations` – create a conversation
- `GET /conversations` – list conversations (optional `search` and `include_archived`)
- `GET /conversations/{conversation_id}` – get conversation with messages
- `PATCH /conversations/{conversation_id}` – update title or archived state
- `DELETE /conversations/{conversation_id}` – delete conversation
- `GET /conversations/{conversation_id}/messages` – list messages (optional `search`)
- `POST /conversations/{conversation_id}/messages` – add message
- `PATCH /conversations/{conversation_id}/messages/{message_id}` – edit message

## OpenAI-Compatible Routes

Standard OpenAI-style endpoints are available under `/v1/*` and require the token header.
