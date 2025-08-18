from datetime import datetime
import json
from typing import Any, AsyncGenerator, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Conversation, Message, File
from ..schemas import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    ConversationWithMessages,
    MessageCreate,
    MessageOut,
    MessageUpdate,
)
from ..settings import DEFAULT_MODEL, OLLAMA_HOST


bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Security(bearer_scheme)],
)


def _require_user(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        raise HTTPException(status_code=401, detail="User API key required")
    return uid


@router.post("", response_model=ConversationOut, summary="Create conversation")
def create_conversation(
    payload: ConversationCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    convo = Conversation(title=payload.title, user_id=user_id)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get(
    "",
    response_model=List[ConversationOut],
    summary="List conversations",
    description="Optional `search` matches title or any message content.",
)
def list_conversations(
    request: Request,
    db: Session = Depends(get_db),
    search: str | None = Query(
        default=None, description="Search in conversation title and messages"
    ),
    include_archived: bool = Query(
        default=False, description="Include archived conversations"
    ),
):
    user_id = _require_user(request)
    q = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .options(joinedload(Conversation.messages).joinedload(Message.files))
        .order_by(Conversation.created_at.desc())
    )
    if not include_archived:
        q = q.filter(Conversation.archived == False)  # noqa: E712
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Conversation.title.ilike(like),
                Conversation.messages.any(Message.content.ilike(like)),
            )
        )
    return q.all()


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
def get_conversation(
    conversation_id: str, request: Request, db: Session = Depends(get_db)
):
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages).joinedload(Message.files))
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str, request: Request, db: Session = Depends(get_db)
):
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(convo)
    db.commit()
    return


@router.patch(
    "/{conversation_id}",
    response_model=ConversationOut,
    summary="Update conversation (title / archived)",
)
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if payload.title is not None:
        convo.title = payload.title
    if payload.archived is not None:
        convo.archived = bool(payload.archived)
        convo.archived_at = datetime.utcnow() if convo.archived else None

    db.commit()
    db.refresh(convo)
    return convo


@router.get(
    "/{conversation_id}/messages",
    response_model=List[MessageOut],
    summary="List messages in a conversation",
    description="Optional `search` matches message content.",
)
def list_messages(
    conversation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Search in message content"),
):
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    q = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .options(joinedload(Message.files))
    )

    if search:
        like = f"%{search}%"
        q = q.filter(Message.content.ilike(like))

    return q.all()


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageOut,
    summary="Add message to conversation",
)
def add_message(
    conversation_id: str,
    body: MessageCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg = Message(conversation_id=conversation_id, role=body.role, content=body.content)
    if body.file_ids:
        files = (
            db.query(File)
            .filter(File.id.in_(body.file_ids), File.owner == user_id)
            .all()
        )
        msg.files = files
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.patch(
    "/{conversation_id}/messages/{message_id}",
    response_model=MessageOut,
    summary="Edit a message",
)
def edit_message(
    conversation_id: str,
    message_id: str,
    body: MessageUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = (
        db.query(Message)
        .filter(Message.id == message_id, Message.conversation_id == conversation_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if body.content is not None:
        msg.content = body.content
    if body.file_ids is not None:
        files = (
            db.query(File)
            .filter(File.id.in_(body.file_ids), File.owner == user_id)
            .all()
        )
        msg.files = files
    db.commit()
    db.refresh(msg)
    return msg


@router.post(
    "/{conversation_id}/reply",
    summary="Generate assistant reply for a conversation",
)
async def generate_reply(
    conversation_id: str,
    request: Request,
    body: Dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
):
    """Call the model with the full conversation and stream back the reply."""
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    model = (body or {}).get("model", DEFAULT_MODEL)
    messages = [{"role": m.role, "content": m.content} for m in convo.messages]

    async def event_stream() -> AsyncGenerator[bytes, None]:
        buffer: List[str] = []
        async with httpx.AsyncClient(timeout=None) as client:
            req = {"model": model, "messages": messages, "stream": True}
            async with client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=req) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if chunk.get("done"):
                        reply = "".join(buffer)
                        msg = Message(conversation_id=conversation_id, role="assistant", content=reply)
                        db.add(msg)
                        db.commit()
                        db.refresh(msg)
                        payload = {
                            "message": MessageOut.model_validate(msg).model_dump(),
                            "done": True,
                        }
                        yield f"data: {json.dumps(payload)}\n\n".encode()
                        return
                    delta = (
                        chunk.get("message", {}).get("content")
                        or chunk.get("response", "")
                        or ""
                    )
                    if delta:
                        buffer.append(delta)
                        yield f"data: {json.dumps({'delta': delta})}\n\n".encode()

    return StreamingResponse(event_stream(), media_type="text/event-stream")

