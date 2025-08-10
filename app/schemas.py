from pydantic import BaseModel, Field
from typing import List, Optional

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
    class Config: from_attributes = True

class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str

class MessageUpdate(BaseModel):
    content: str

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    class Config: from_attributes = True

class ConversationWithMessages(BaseModel):
    id: str
    title: Optional[str] = None
    archived: bool = False
    messages: List[MessageOut]
    class Config: from_attributes = True