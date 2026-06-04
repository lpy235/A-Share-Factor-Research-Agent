import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    filename: str
    path: str
    content_type: str | None = None


class DocumentStore:
    def __init__(self, root: str = "uploaded_docs") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"

    def save(self, filename: str, content: bytes, content_type: str | None = None) -> DocumentRecord:
        suffix = Path(filename).suffix.lower()
        if suffix not in {".md", ".txt", ".pdf"}:
            raise ValueError(f"Unsupported document type: {suffix}")
        document_id = f"doc_{uuid4().hex[:12]}"
        safe_name = Path(filename).name
        document_dir = self.root / document_id
        document_dir.mkdir(parents=True, exist_ok=True)
        stored_path = document_dir / safe_name
        stored_path.write_bytes(content)

        record = DocumentRecord(document_id, safe_name, str(stored_path), content_type)
        index = self._load_index()
        index[document_id] = record.__dict__
        self._save_index(index)
        return record

    def get(self, document_id: str) -> DocumentRecord:
        index = self._load_index()
        if document_id not in index:
            raise KeyError(document_id)
        return DocumentRecord(**index[document_id])

    def list(self) -> list[DocumentRecord]:
        return [DocumentRecord(**item) for item in self._load_index().values()]

    def _load_index(self) -> dict:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save_index(self, index: dict) -> None:
        self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
