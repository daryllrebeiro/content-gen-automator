from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings


app = FastAPI(
    title="Animated YouTube Shorts Prompt Agent",
    version="0.1.0",
    description="Stateful orchestration for consistent animated Shorts prompts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Request-ID"],
)

app.include_router(router)

from fastapi.staticfiles import StaticFiles
import os

os.makedirs("app/static/audio", exist_ok=True)
os.makedirs("app/static/video", exist_ok=True)
os.makedirs("app/static/output", exist_ok=True)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

