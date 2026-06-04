"""
utils/ingestor.py

UniversalIngestor: extracts clean text from a URL, raw text paste,
uploaded PDF, or uploaded DOCX file.
"""
import urllib.parse
import requests
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SEC = 10
REQUEST_HEADERS     = {"User-Agent": "Mozilla/5.0"}


class IngestorError(Exception):
    """Raised when ingestion fails in a way the caller should handle."""


class UniversalIngestor:
    """Extract plain text from a URL, raw paste, PDF, or DOCX file object.

    Usage:
        ingestor = UniversalIngestor(source_input)
        payload  = ingestor.get_ingest_payload(file_object=uploaded_file)

    Returns a dict:
        {
            "raw_text":  str,   # clean, whitespace-normalised text
            "metadata":  {
                "source_type": "url" | "raw_text" | "pdf" | "docx",
                "length":      int,
                "url":         str  # only present for URL sources
            }
        }

    Raises:
        IngestorError: on any failure — callers should catch this and show
                       a user-facing error rather than receiving error strings
                       disguised as valid content.
    """

    def __init__(self, source_input: str) -> None:
        self.source_input = source_input.strip()
        self._content  = ""
        self._metadata: dict = {"source_type": "unknown", "length": 0}

    # -----------------------------------------------------------------------
    # PUBLIC
    # -----------------------------------------------------------------------

    def get_ingest_payload(self, file_object=None) -> dict:
        """Detect source type, extract text, and return a clean payload."""
        if file_object is not None:
            self._ingest_file(file_object)
        elif self._is_valid_url(self.source_input):
            self._ingest_url(self.source_input)
        else:
            self._ingest_raw_text(self.source_input)

        self._content  = self._normalise_whitespace(self._content)
        self._metadata["length"] = len(self._content)

        if not self._content:
            raise IngestorError("Ingestion produced empty content. Check the source and try again.")

        return {"raw_text": self._content, "metadata": self._metadata}

    # -----------------------------------------------------------------------
    # PRIVATE — source handlers
    # -----------------------------------------------------------------------

    def _ingest_file(self, file_object) -> None:
        """Dispatch to the correct file handler based on file name extension."""
        name = getattr(file_object, "name", "").lower()
        if name.endswith(".pdf"):
            self._ingest_pdf(file_object)
        elif name.endswith(".docx"):
            self._ingest_docx(file_object)
        else:
            raise IngestorError(
                f"Unsupported file type: '{name}'. Please upload a PDF or DOCX file."
            )

    def _ingest_pdf(self, file_object) -> None:
        try:
            reader = PyPDF2.PdfReader(file_object)
            pages  = [page.extract_text() or "" for page in reader.pages]
            self._content = "\n".join(pages)
            self._metadata["source_type"] = "pdf"
        except Exception as e:
            raise IngestorError(f"Failed to read PDF: {e}") from e

    def _ingest_docx(self, file_object) -> None:
        try:
            doc = Document(file_object)
            self._content = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            self._metadata["source_type"] = "docx"
        except Exception as e:
            raise IngestorError(f"Failed to read DOCX: {e}") from e

    def _ingest_url(self, url: str) -> None:
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SEC)
            response.raise_for_status()
            response.encoding = response.apparent_encoding  # handle non-UTF-8 pages

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.extract()

            self._content = soup.get_text(separator=" ")
            self._metadata["source_type"] = "url"
            self._metadata["url"] = url

        except requests.exceptions.Timeout:
            raise IngestorError(f"Request timed out after {REQUEST_TIMEOUT_SEC}s: {url}")
        except requests.exceptions.HTTPError as e:
            raise IngestorError(f"HTTP error scraping URL: {e}")
        except Exception as e:
            raise IngestorError(f"Failed to scrape URL: {e}") from e

    def _ingest_raw_text(self, text: str) -> None:
        self._content = text
        self._metadata["source_type"] = "raw_text"

    # -----------------------------------------------------------------------
    # PRIVATE — utilities
    # -----------------------------------------------------------------------

    @staticmethod
    def _is_valid_url(value: str) -> bool:
        try:
            result = urllib.parse.urlparse(value)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except ValueError:
            return False

    @staticmethod
    def _normalise_whitespace(text: str) -> str:
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())
