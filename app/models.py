from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StreamAttachRequest(BaseModel):
    rtsp_url: str = Field(min_length=8, description="Network stream URL (RTSP recommended).")


class StreamState(BaseModel):
    connected: bool
    url: str | None = None
    last_error: str | None = None
    connected_at: datetime | None = None


class EventIn(BaseModel):
    actor_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    timestamp_sec: float = Field(ge=0)
    traits: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: Literal["detector", "manual", "system"] = "detector"
    note: str | None = None


class EventOut(EventIn):
    id: int
    created_at: datetime


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatMessageOut(ChatMessageIn):
    id: int
    created_at: datetime


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=1)


class TimestampReference(BaseModel):
    event_id: int
    timestamp_sec: float
    actor_id: str
    scenario: str


class ChatQueryResponse(BaseModel):
    answer: str
    references: list[TimestampReference]
    grounded: bool = True


class DetectionStartRequest(BaseModel):
    source_url: str = Field(min_length=1, description="RTSP/RTSPS/HTTP/HTTPS source for YOLO tracking.")
    model_name: str = Field(default="yolov8n.pt", min_length=1)
    confidence: float = Field(default=0.35, ge=0.01, le=1.0)
    event_cooldown_sec: float = Field(default=5.0, ge=0.5, le=120.0)


class DetectionStatus(BaseModel):
    running: bool
    source_url: str | None = None
    model_name: str | None = None
    message: str | None = None
