from io import BytesIO

import requests
from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


class PublicSourceFetcher:
    def fetch_text(self, url: str, timeout: int = 15) -> str:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "A-Share-Factor-Agent/0.1"},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type:
            return html_to_text(response.text)
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return pdf_bytes_to_text(response.content)
        return response.text


def pdf_bytes_to_text(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
