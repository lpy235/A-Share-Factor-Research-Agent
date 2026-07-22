from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.documents import router as documents_router
from app.api.research import router as research_router
from app.api.runs import router as runs_router
from app.api.ui import WEB_DIR, router as ui_router
from app.api.universes import router as universes_router

app = FastAPI(title="A股因子研究智能体")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
app.include_router(documents_router)
app.include_router(research_router)
app.include_router(runs_router)
app.include_router(universes_router)
app.include_router(ui_router)


@app.get("/health")
def health():
    return {"status": "ok"}
