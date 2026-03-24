from __future__ import annotations

import json
from datetime import datetime

from app.db import get_conn
from app.models import EventIn, EventOut


class EventStore:
    def add_event(self, event: EventIn) -> EventOut:
        with get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (actor_id, scenario, timestamp_sec, traits, confidence, source, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.actor_id,
                    event.scenario,
                    event.timestamp_sec,
                    json.dumps(event.traits),
                    event.confidence,
                    event.source,
                    event.note,
                ),
            )
            row = conn.execute("SELECT * FROM events WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_model(row)

    def list_events(self, actor_id: str | None = None, scenario: str | None = None) -> list[EventOut]:
        query = "SELECT * FROM events WHERE 1=1"
        params: list[str] = []
        if actor_id:
            query += " AND actor_id = ?"
            params.append(actor_id)
        if scenario:
            query += " AND scenario = ?"
            params.append(scenario)
        query += " ORDER BY timestamp_sec ASC"

        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._to_model(row) for row in rows]

    def search_events_for_query(self, text: str) -> list[EventOut]:
        tokens = [token.strip().lower() for token in text.split() if token.strip()]
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY timestamp_sec ASC").fetchall()

        events = [self._to_model(row) for row in rows]
        if not tokens:
            return events[:5]

        def score(event: EventOut) -> int:
            haystack = f"{event.actor_id} {event.scenario} {' '.join(event.traits)} {(event.note or '')}".lower()
            return sum(1 for tok in tokens if tok in haystack)

        ranked = sorted(events, key=score, reverse=True)
        ranked = [event for event in ranked if score(event) > 0]
        return ranked[:8]

    @staticmethod
    def _to_model(row) -> EventOut:
        return EventOut(
            id=row["id"],
            actor_id=row["actor_id"],
            scenario=row["scenario"],
            timestamp_sec=row["timestamp_sec"],
            traits=json.loads(row["traits"]),
            confidence=row["confidence"],
            source=row["source"],
            note=row["note"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
