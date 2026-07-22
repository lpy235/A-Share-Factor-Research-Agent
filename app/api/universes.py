from fastapi import APIRouter, File, HTTPException, UploadFile

from app.storage.universes import HistoricalUniverseStore


router = APIRouter(prefix="/universes", tags=["universes"])
universe_store = HistoricalUniverseStore()


@router.post("")
async def upload_historical_universe(file: UploadFile = File(...)) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Historical universe must be a CSV file")
    try:
        universe_id = universe_store.register(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"historical_universe_id": universe_id}
