from __future__ import annotations

import os
from datetime import datetime

from app.db import get_conn
from app.models import ChatMessageOut, ChatQueryResponse, TimestampReference
from app.services.event_store import EventStore


class ChatService:
    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store

    def add_message(self, role: str, content: str) -> ChatMessageOut:
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO chat_messages (role, content) VALUES (?, ?)",
                (role, content),
            )
            row = conn.execute("SELECT * FROM chat_messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return ChatMessageOut(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_messages(self) -> list[ChatMessageOut]:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM chat_messages ORDER BY id ASC").fetchall()
        return [
            ChatMessageOut(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def answer_query(self, question: str) -> ChatQueryResponse:
        matched = self.event_store.search_events_for_query(question)
        references = [
            TimestampReference(
                event_id=event.id,
                timestamp_sec=event.timestamp_sec,
                actor_id=event.actor_id,
                scenario=event.scenario,
            )
            for event in matched
        ]

        if not matched:
            answer = "No matching events found in logs."
            return ChatQueryResponse(answer=answer, references=[], grounded=True)

        context_lines = [
            f"Event #{event.id}: actor={event.actor_id}, scenario={event.scenario}, t={event.timestamp_sec:.1f}s, traits={','.join(event.traits) or 'n/a'}"
            for event in matched
        ]
        prompt = (
            "You are MemTracker assistant. Answer strictly from provided events. "
            "If uncertain, say not found. Keep it concise and list event IDs used.\n\n"
            "Events:\n" + "\n".join(context_lines) + f"\n\nQuestion: {question}"
        )

        answer = await self._groq_or_fallback(prompt, matched)
        return ChatQueryResponse(answer=answer, references=references, grounded=True)

    async def _groq_or_fallback(self, prompt: str, matched_events) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        if not api_key:
            ids = ", ".join(f"#{e.id}" for e in matched_events[:4])
            return f"Found related events {ids}. Set GROQ_API_KEY to enable natural-language summaries."

        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()
