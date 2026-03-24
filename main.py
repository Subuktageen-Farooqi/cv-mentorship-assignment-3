"""ASGI compatibility entrypoint.

Allows running the server with either:
- uvicorn app.main:app --reload
- uvicorn main:app --reload
"""

from app.main import app
