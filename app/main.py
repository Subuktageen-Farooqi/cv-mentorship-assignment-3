from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.models import ChatMessageOut, ChatQueryRequest, ChatQueryResponse, EventIn, EventOut, StreamAttachRequest, StreamState
from app.services.chat_service import ChatService
from app.services.event_store import EventStore
from app.services.stream_manager import StreamManager

load_dotenv()

app = FastAPI(title="MemTracker", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
stream_manager = StreamManager()
event_store = EventStore()
chat_service = ChatService(event_store)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.post("/api/stream/attach", response_model=StreamState)
def attach_stream(body: StreamAttachRequest) -> StreamState:
    return stream_manager.attach(body.rtsp_url)


@app.get("/api/stream", response_model=StreamState)
def get_stream_state() -> StreamState:
    return stream_manager.state()


@app.post("/api/events", response_model=EventOut)
def add_event(event: EventIn) -> EventOut:
    return event_store.add_event(event)


@app.get("/api/events", response_model=list[EventOut])
def list_events(actor_id: str | None = None, scenario: str | None = None) -> list[EventOut]:
    return event_store.list_events(actor_id=actor_id, scenario=scenario)


@app.get("/api/chat/history", response_model=list[ChatMessageOut])
def history() -> list[ChatMessageOut]:
    return chat_service.list_messages()


@app.post("/api/chat/query", response_model=ChatQueryResponse)
async def query_chat(body: ChatQueryRequest) -> ChatQueryResponse:
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    chat_service.add_message("user", body.question)
    result = await chat_service.answer_query(body.question)
    chat_service.add_message("assistant", result.answer)
    return result
