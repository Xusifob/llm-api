from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    api_key: str


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    archived: Optional[bool] = None


class ConversationOut(BaseModel):
    id: str
    title: Optional[str] = None
    archived: bool = False

    class Config:
        from_attributes = True


class FileOut(BaseModel):
    id: str
    mime_type: str
    size: int
    name: str
    path: str
    owner: str
    upload_date: datetime
    public_url: str

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str
    file_ids: List[str] = []


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    file_ids: Optional[List[str]] = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    files: List[FileOut] = []

    class Config:
        from_attributes = True


class ConversationWithMessages(BaseModel):
    id: str
    title: Optional[str] = None
    archived: bool = False
    messages: List[MessageOut]

    class Config:
        from_attributes = True
