from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .settings import OPENAI_API_KEY
from .db import SessionLocal
from .models import User

DOCS_WHITELIST = {"/","/auth/signup","/auth/login", "/docs", "/docs/", "/redoc", "/redoc/", "/openapi.json", "/health"}


async def auth_middleware(request: Request, call_next):
    if request.url.path in DOCS_WHITELIST:
        return await call_next(request)

    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing Authorization header"})
    token = auth_header.split(" ", 1)[1]

    if OPENAI_API_KEY and token == OPENAI_API_KEY:
       request.state.user_id = None
       return await call_next(request)

    db: Session = SessionLocal()
    try:
       user = db.query(User).filter(User.api_key == token).first()
       if not user:
          return JSONResponse(status_code=401, content={"error": "Invalid API key"})
       request.state.user_id = user.id
    finally:
       db.close()

    return await call_next(request)
