import asyncio
import json

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.storage.db import init_db
from app.storage.artifacts import ArtifactStore
from app.storage.events import EventStore

router = APIRouter(prefix="/runs", tags=["runs"])

DB_PATH = "runs.db"
init_db(DB_PATH)
store = EventStore(DB_PATH)
artifact_store = ArtifactStore()


@router.get("/{run_id}/events")
def list_events(run_id: str):
    return {"run_id": run_id, "events": store.list_events(run_id)}


@router.get("/{run_id}/artifacts")
def list_artifacts(run_id: str):
    return {"run_id": run_id, "artifacts": artifact_store.list_artifacts(run_id)}


@router.get("/{run_id}/artifacts/{artifact_name}")
def download_artifact(run_id: str, artifact_name: str):
    path = artifact_store.get_artifact_path(run_id, artifact_name)
    if path is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    artifacts = {item["name"]: item for item in artifact_store.list_artifacts(run_id)}
    media_type = artifacts.get(artifact_name, {}).get("media_type", "application/octet-stream")
    return FileResponse(path, media_type=media_type, filename=artifact_name)


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
