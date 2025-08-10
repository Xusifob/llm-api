from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .settings import DATABASE_URL

class Base(DeclarativeBase):
    pass

# Import models so metadata is populated
from . import models  # noqa: E402

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def utcnow():
    return datetime.utcnow()
