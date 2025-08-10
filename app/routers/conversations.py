from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from typing import List
from ..db import get_db
from ..models import Conversation, Message
from ..schemas import ConversationCreate, ConversationOut, ConversationWithMessages, MessageCreate, MessageOut, ConversationUpdate, MessageUpdate
from datetime import datetime


router = APIRouter(prefix="/conversations", tags=["conversations"])

def _require_user(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        raise HTTPException(status_code=401, detail="User API key required")
    return uid

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

@router.get("", response_model=List[ConversationOut], summary="List conversations", description="Optional `search` matches title or any message content.")
def list_conversations(
    request: Request,
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Search in conversation title and messages"),
    include_archived: bool = Query(default=False, description="Include archived conversations"),
):
    user_id = _require_user(request)
    q = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .options(joinedload(Conversation.messages))
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
def get_conversation(conversation_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = _require_user(request)
    convo = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
    if not convo: raise HTTPException(status_code=404, detail="Conversation not found")
    return convo

@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = _require_user(request)
    convo = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
    if not convo: raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(convo); db.commit(); return

@router.patch("/{conversation_id}", response_model=ConversationOut, summary="Update conversation (title / archived)")
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

    db.commit(); db.refresh(convo)
    return convo

@router.get("/{conversation_id}/messages", response_model=List[MessageOut], summary="List messages in a conversation", description="Optional `search` matches message content.")
def list_messages(
    conversation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Search in message content")
):
    user_id = _require_user(request)
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    q = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())

    if search:
        like = f"%{search}%"
        q = q.filter(Message.content.ilike(like))

    return q.all()


@router.get("/{conversation_id}/messages", response_model=List[MessageOut])
def list_messages(conversation_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = _require_user(request)
    convo = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
    if not convo: raise HTTPException(status_code=404, detail="Conversation not found")
    return convo.messages


@router.patch("/{conversation_id}/messages/{message_id}", response_model=MessageOut, summary="Edit a message")
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

    msg.content = body.content
    db.commit(); db.refresh(msg)
    return msg