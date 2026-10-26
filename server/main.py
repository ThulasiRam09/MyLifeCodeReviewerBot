"""FastAPI backend that exposes the MyLifeCodeReviewer Gemini agent as a web API."""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from reviewer_bot.reviewer import DEFAULT_MODEL, create_chat, create_client, get_system, stream_reply

app = FastAPI(title="MyLifeCodeReviewer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

conversations: dict = {}


class ReviewRequest(BaseModel):
    code: str = ""
    language: str = "Java"
    problem: str = ""
    conversation_id: str = "default"
    model: Optional[str] = None
    no_search: bool = False


class ResetRequest(BaseModel):
    conversation_id: str = "default"


def build_user_text(req: ReviewRequest) -> str:
    parts = []
    if req.problem and req.problem.strip():
        parts.append(f"Problem: {req.problem.strip()}")
    parts.append(f"Language: {req.language.strip() or 'detect'}")
    parts.append("Code:\n```\n" + req.code + "\n```")
    return "\n\n".join(parts)


def get_chat(conv_id: str, model: Optional[str], search: bool):
    chat = conversations.get(conv_id)
    if chat is None:
        client = create_client()
        chat = create_chat(client, model=model or DEFAULT_MODEL, system=get_system(), search=search)
        conversations[conv_id] = chat
    return chat


def event_stream(req: ReviewRequest):
    text = build_user_text(req)
    chat = get_chat(req.conversation_id, req.model, not req.no_search)

    def gen():
        try:
            for chunk in stream_reply(chat, text):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/review")
async def review(req: ReviewRequest):
    return event_stream(req)


@app.post("/api/reset")
async def reset(req: ResetRequest = None):
    conv_id = "default"
    if req and req.conversation_id:
        conv_id = req.conversation_id
    conversations.pop(conv_id, None)
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "service": "MyLifeCodeReviewer"}


# Serve built frontend if present
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path == "health":
            return {"error": "not found"}
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "not found"}
