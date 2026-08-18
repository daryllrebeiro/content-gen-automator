from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="Animated YouTube Shorts Prompt Agent",
    version="0.1.0",
    description="Stateful orchestration for consistent animated Shorts prompts.",
)

app.include_router(router)

