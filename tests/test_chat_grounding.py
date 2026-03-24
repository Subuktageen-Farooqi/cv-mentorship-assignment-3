from app.services.chat_service import ChatService
from app.services.event_store import EventStore
from app.models import EventIn
from app.db import init_db


def test_chat_returns_not_found_for_missing_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    store = EventStore()
    chat = ChatService(store)

    response = __import__('asyncio').run(chat.answer_query('did someone run?'))
    assert response.grounded is True
    assert response.references == []
    assert 'No matching events found' in response.answer


def test_chat_returns_references(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    store = EventStore()
    store.add_event(EventIn(actor_id='person-1', scenario='presence', timestamp_sec=10, traits=['blue_shirt']))

    chat = ChatService(store)
    response = __import__('asyncio').run(chat.answer_query('blue shirt person'))

    assert len(response.references) == 1
    assert response.references[0].actor_id == 'person-1'
