import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.storage.db import init_db
from app.storage.events import EventStore

router = APIRouter(prefix="/runs", tags=["runs"])

DB_PATH = "runs.db"
init_db(DB_PATH)
store = EventStore(DB_PATH)


@router.get("/{run_id}/events")
def list_events(run_id: str):
    return {"run_id": run_id, "events": store.list_events(run_id)}


@router.get("/{run_id}/events/stream")
async def stream_events(run_id: str):
    async def event_generator():
        sent = 0
        for _ in range(30):
            events = store.list_events(run_id)
            for event in events[sent:]:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            sent = len(events)
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

