from fastapi import APIRouter, File, HTTPException, UploadFile

from app.storage.documents import DocumentStore

router = APIRouter(prefix="/documents", tags=["documents"])

store = DocumentStore()


@router.post("")
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    try:
        record = store.save(file.filename or "uploaded.txt", content, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "document_id": record.document_id,
        "filename": record.filename,
        "content_type": record.content_type,
    }


@router.get("/{document_id}")
def get_document(document_id: str):
    try:
        record = store.get(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="document not found") from exc
    return {
        "document_id": record.document_id,
        "filename": record.filename,
        "path": record.path,
        "content_type": record.content_type,
    }

