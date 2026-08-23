"""
utils/ingestion.py

CurriculumIngestor: Cleans, normalizes, and aggregates raw curriculum input
from text strings or multiple webpage URLs into a unified session payload.
"""
import re
import logging
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SEC  = 10
MIN_CONTENT_LENGTH   = 100   # chars — below this a scrape is considered empty
SECTION_SEPARATOR    = "\n" + "=" * 60 + "\n"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class IngestionError(Exception):
    """Raised when ingestion fails in a way the caller should handle visibly."""


class CurriculumIngestor:
    """Scrapes, cleans, and aggregates curriculum content from URLs or raw text.

    Args:
        timeout: HTTP request timeout in seconds. Defaults to REQUEST_TIMEOUT_SEC.
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT_SEC) -> None:
        self.timeout = timeout

    # -----------------------------------------------------------------------
    # PUBLIC
    # -----------------------------------------------------------------------

    def normalize_text(self, raw_text: str) -> str:
        """Clean and standardize raw text input.

        Raises:
            IngestionError: if input is empty or produces no content after cleaning.
        """
        if not raw_text or not raw_text.strip():
            raise IngestionError("Input text is empty.")

        # Normalize line endings
        cleaned = re.sub(r"\r\n|\r", "\n", raw_text)
        # Collapse 3+ blank lines to 2
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Collapse runs of spaces/tabs within a line to a single space
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

        result = cleaned.strip()
        if len(result) < MIN_CONTENT_LENGTH:
            raise IngestionError(
                f"Normalized text is too short ({len(result)} chars). "
                "Please provide more substantial curriculum content."
            )
        return result

    def fetch_url_content(self, url: str) -> str:
        """Scrape core text from a single web page (optimized for OpenStax).

        Raises:
            IngestionError: on invalid URL, HTTP error, or empty content.
        """
        url = url.strip()
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise IngestionError(f"Invalid URL: '{url}'")
        if parsed.scheme not in ("http", "https"):
            raise IngestionError(f"Only http/https URLs are supported. Got: '{url}'")

        try:
            response = requests.get(url, headers=HEADERS, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding  # handle non-UTF-8 pages
        except requests.exceptions.Timeout:
            raise IngestionError(f"Request timed out after {self.timeout}s: '{url}'")
        except requests.exceptions.HTTPError as e:
            raise IngestionError(f"HTTP {e.response.status_code} error fetching '{url}': {e}")
        except requests.RequestException as e:
            raise IngestionError(f"Network error fetching '{url}': {e}") from e

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        # Prioritize main content containers — OpenStax-specific selectors included
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"data-type": "page"})
            or soup.find("div", class_="main-content")
            or soup.body
        )

        if not main_content:
            raise IngestionError(f"Could not locate main content container in '{url}'.")

        raw = main_content.get_text(separator="\n", strip=True)
        content = self.normalize_text(raw)

        if len(content) < MIN_CONTENT_LENGTH:
            raise IngestionError(
                f"Page scraped but returned almost no text ({len(content)} chars). "
                f"The page may require JavaScript rendering: '{url}'"
            )
        return content

    def fetch_batch_urls(self, url_list: list[str]) -> str:
        """Scrape multiple URLs and stitch them into one aggregated payload.

        Partial failures are logged and included in the output as error notices
        so the caller knows which URLs failed without aborting the whole batch.

        Raises:
            IngestionError: if ALL URLs fail (nothing useful was retrieved).

        Returns:
            Aggregated payload string with section headers and any error notices.
        """
        valid_urls = [u.strip() for u in url_list if u.strip()]
        if not valid_urls:
            raise IngestionError("No valid URLs provided for batch ingestion.")

        sections: list[str] = []
        errors:   list[str] = []

        for idx, url in enumerate(valid_urls, start=1):
            try:
                content = self.fetch_url_content(url)
                sections.append(f"=== CHAPTER SECTION {idx}: {url} ===")
                sections.append(content)
                sections.append(SECTION_SEPARATOR)
                logger.info("Section %d/%d fetched successfully: %s", idx, len(valid_urls), url)
            except IngestionError as e:
                logger.error("Section %d/%d failed (%s): %s", idx, len(valid_urls), url, e)
                errors.append(f"⚠️ Section {idx} failed ({url}): {e}")

        if not sections:
            raise IngestionError(
                f"Batch ingestion failed for all {len(valid_urls)} URL(s):\n"
                + "\n".join(errors)
            )

        # Warn caller about partial failures by prepending them to the payload
        if errors:
            error_notice = (
                "⚠️ PARTIAL BATCH — the following URLs could not be fetched:\n"
                + "\n".join(errors)
                + "\n\nSuccessfully retrieved sections are below:\n"
                + SECTION_SEPARATOR
            )
            sections.insert(0, error_notice)

        return "\n\n".join(sections)
