import os
import sys
from pathlib import Path

# Ensure a fresh SQLite database for testing
DB_PATH = Path("./test.db")
if DB_PATH.exists():
    DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"

# Make sure the application package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import Base, engine, SessionLocal
from app.auth import auth_middleware
from app.routers import conversations
from app.models import User

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.middleware("http")(auth_middleware)
app.include_router(conversations.router)

client = TestClient(app)


def _create_user():
    db = SessionLocal()
    user = User(username="u", password_hash="p", api_key="key")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def test_edit_message_deletes_following():
    user = _create_user()
    headers = {"Authorization": f"Bearer {user.api_key}"}

    resp = client.post("/conversations", json={"title": "t"}, headers=headers)
    assert resp.status_code == 200
    convo_id = resp.json()["id"]

    m1 = client.post(
        f"/conversations/{convo_id}/messages",
        json={"role": "user", "content": "hello"},
        headers=headers,
    ).json()
    client.post(
        f"/conversations/{convo_id}/messages",
        json={"role": "assistant", "content": "world"},
        headers=headers,
    )
    client.post(
        f"/conversations/{convo_id}/messages",
        json={"role": "user", "content": "bye"},
        headers=headers,
    )

    resp = client.patch(
        f"/conversations/{convo_id}/messages/{m1['id']}",
        json={"content": "hi"},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get(f"/conversations/{convo_id}/messages", headers=headers)
    msgs = resp.json()
    assert len(msgs) == 1
    assert msgs[0]["id"] == m1["id"]
    assert msgs[0]["content"] == "hi"

    # Clean up the temporary database file
    DB_PATH.unlink()

