from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

router = APIRouter(tags=["ui"])


@router.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(WEB_DIR / "index.html")

