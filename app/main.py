from fastapi import FastAPI

from app.api.research import router as research_router
from app.api.runs import router as runs_router

app = FastAPI(title="A-Share Factor Research Agent")
app.include_router(research_router)
app.include_router(runs_router)


@app.get("/health")
def health():
    return {"status": "ok"}

