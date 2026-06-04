from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedDocument:
    source_title: str
    source_type: str
    text: str
    source_url: str | None = None


class DocumentParser:
    def parse_file(self, path: str) -> ParsedDocument:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(file_path)
        if suffix in {".md", ".txt"}:
            return ParsedDocument(
                source_title=file_path.name,
                source_type="user_upload",
                text=file_path.read_text(encoding="utf-8"),
            )
        raise ValueError(f"Unsupported file type: {suffix}")

    def _parse_pdf(self, path: Path) -> ParsedDocument:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return ParsedDocument(path.name, "user_upload", "\n".join(pages))

