import secrets
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from ..db import get_db
from ..models import User
from ..schemas import UserCreate, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/signup", response_model=LoginResponse)
def signup(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    api_key = f"sk-{secrets.token_hex(24)}"
    user = User(
        username=body.username,
        password_hash=pwd.hash(body.password),
        api_key=api_key,
    )
    db.add(user); db.commit(); db.refresh(user)
    return LoginResponse(api_key=user.api_key)

@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not pwd.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(api_key=user.api_key)
