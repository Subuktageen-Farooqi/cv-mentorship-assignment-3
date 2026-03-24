from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.models import DetectionStatus, EventIn
from app.services.event_store import EventStore


@dataclass
class _RuntimeConfig:
    source_url: str
    model_name: str
    confidence: float
    event_cooldown_sec: float


class DetectionPipeline:
    """Background YOLOv8 multi-person detection + tracking loop."""

    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._status = DetectionStatus(running=False)
        self._last_seen_by_track: dict[int, float] = {}
        self._frames_processed = 0
        self._events_logged = 0

    def start(self, source_url: str, model_name: str, confidence: float, event_cooldown_sec: float) -> DetectionStatus:
        if self._thread and self._thread.is_alive():
            return DetectionStatus(
                running=True,
                source_url=self._status.source_url,
                model_name=self._status.model_name,
                message="Detection is already running.",
                frames_processed=self._frames_processed,
                events_logged=self._events_logged,
            )

        self._stop_event.clear()
        config = _RuntimeConfig(
            source_url=source_url,
            model_name=model_name,
            confidence=confidence,
            event_cooldown_sec=event_cooldown_sec,
        )

        self._thread = threading.Thread(target=self._run, args=(config,), daemon=True)
        self._thread.start()
        self._frames_processed = 0
        self._events_logged = 0
        self._status = DetectionStatus(
            running=True,
            source_url=source_url,
            model_name=model_name,
            message="YOLO tracking started.",
            frames_processed=self._frames_processed,
            events_logged=self._events_logged,
        )
        return self._status

    def stop(self) -> DetectionStatus:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._status = DetectionStatus(
            running=False,
            source_url=self._status.source_url,
            model_name=self._status.model_name,
            message="YOLO tracking stopped.",
            frames_processed=self._frames_processed,
            events_logged=self._events_logged,
        )
        self._last_seen_by_track.clear()
        return self._status

    def status(self) -> DetectionStatus:
        running = bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set())
        if not running and self._status.running:
            self._status = DetectionStatus(
                running=False,
                source_url=self._status.source_url,
                model_name=self._status.model_name,
                message="Detection loop ended.",
                frames_processed=self._frames_processed,
                events_logged=self._events_logged,
            )
        return self._status

    def _run(self, config: _RuntimeConfig) -> None:
        try:
            import cv2
            from ultralytics import YOLO
        except Exception as exc:  # pragma: no cover - depends on external package
            self._status = DetectionStatus(
                running=False,
                source_url=config.source_url,
                model_name=config.model_name,
                message=f"Missing runtime dependency: {exc}",
                frames_processed=self._frames_processed,
                events_logged=self._events_logged,
            )
            return

        try:
            capture = cv2.VideoCapture(config.source_url)
            if not capture.isOpened():
                self._status = DetectionStatus(
                    running=False,
                    source_url=config.source_url,
                    model_name=config.model_name,
                    message="Could not open stream. Check RTSP URL/network/firewall/credentials.",
                    frames_processed=self._frames_processed,
                    events_logged=self._events_logged,
                )
                return
            capture.release()

            model = YOLO(config.model_name)
            results = model.track(
                source=config.source_url,
                stream=True,
                persist=True,
                classes=[0],  # person
                conf=config.confidence,
                verbose=False,
            )

            for result in results:
                if self._stop_event.is_set():
                    break

                self._frames_processed += 1
                ts = time.time()
                boxes = getattr(result, "boxes", None)
                if boxes is None or boxes.id is None:
                    continue

                track_ids = boxes.id.int().tolist()
                confidences = boxes.conf.tolist() if boxes.conf is not None else [1.0] * len(track_ids)

                for track_id, conf in zip(track_ids, confidences):
                    last_seen = self._last_seen_by_track.get(track_id, 0.0)
                    if ts - last_seen < config.event_cooldown_sec:
                        continue

                    self._last_seen_by_track[track_id] = ts
                    self.event_store.add_event(
                        EventIn(
                            actor_id=f"track-{track_id}",
                            scenario="person_presence",
                            timestamp_sec=ts,
                            traits=[],
                            confidence=float(conf),
                            source="detector",
                            note="YOLOv8 track(person)",
                        )
                    )
                    self._events_logged += 1

            self._status = DetectionStatus(
                running=False,
                source_url=config.source_url,
                model_name=config.model_name,
                message="Detection finished.",
                frames_processed=self._frames_processed,
                events_logged=self._events_logged,
            )
        except Exception as exc:  # pragma: no cover - runtime/model/stream specific
            self._status = DetectionStatus(
                running=False,
                source_url=config.source_url,
                model_name=config.model_name,
                message=str(exc),
                frames_processed=self._frames_processed,
                events_logged=self._events_logged,
            )
