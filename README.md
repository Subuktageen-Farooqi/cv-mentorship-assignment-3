# MemTracker — CV Mentorship Assignment 3

MemTracker is an end-to-end starter web app for monitoring CCTV-like streams, logging timestamped multi-person events, and querying those logs with an LLM (Groq API-compatible).

## Implemented Features

- **Network stream attachment** endpoint (RTSP/RTSPS/HTTP/HTTPS URL validation).
- **Event logging API** with actor ID, scenario, confidence, traits, timestamp, and notes.
- **Grounded chat query API** that retrieves matching events first, then answers using Groq (or deterministic fallback when key is missing).
- **Timestamped clickable references** in the UI that seek the same on-page video player.
- **Persistent chat history** (SQLite-backed).
- **Dedicated Logs tab behavior** in the web UI with filters and refresh.

## Architecture

```text
[Browser UI]
  ├─ Stream panel + player
  ├─ Logs panel
  └─ Chat panel
       |
       v
[FastAPI Backend]
  ├─ StreamManager (attach/state)
  ├─ EventStore (SQLite events)
  └─ ChatService
       ├─ Retrieval over events (grounding)
       └─ Groq Chat Completions API (optional)
```

## Project Structure

```text
app/
  main.py
  db.py
  models.py
  services/
    stream_manager.py
    event_store.py
    chat_service.py
  static/
    index.html
    app.js
    styles.css
tests/
  test_chat_grounding.py
requirements.txt
```

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Configure Groq:

```bash
export GROQ_API_KEY=your_key_here
export GROQ_MODEL=llama-3.3-70b-versatile
```

4. Run the app:

```bash
uvicorn app.main:app --reload
```

5. Open `http://127.0.0.1:8000`.

## API Overview

- `POST /api/stream/attach`
- `GET /api/stream`
- `POST /api/events`
- `GET /api/events?actor_id=&scenario=`
- `GET /api/chat/history`
- `POST /api/chat/query`

## Notes on Assignment Scenarios

This starter supports these baseline scenarios out-of-the-box:

1. **Person presence** (`scenario="presence"`)
2. **Visual characteristics** through `traits[]` (e.g., `blue_shirt`, `helmet`, `backpack`)
3. **Custom scenarios** by setting arbitrary `scenario` labels (e.g., `phone_usage`, `fall_detected`)

For production scoring, plug your detection/tracking pipeline (YOLO/ByteTrack + trait/task classifier) into the `POST /api/events` ingestion path.
