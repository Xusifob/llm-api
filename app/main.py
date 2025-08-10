from fastapi import FastAPI
from .auth import auth_middleware
from .db import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from .settings import APP_NAME, APP_VERSION, CORS_ORIGINS
from .routers import openai_proxy, conversations, users

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware
from .auth import auth_middleware
app.middleware("http")(auth_middleware)

# Routers
app.include_router(users.router)
app.include_router(openai_proxy.router)
app.include_router(conversations.router)
