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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

class CurriculumIngestor:
    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def normalize_text(self, raw_text: str) -> str:
        """Cleans and standardizes raw text input."""
        if not raw_text or not raw_text.strip():
            raise ValueError("Input text is empty.")
        
        # Remove extra whitespace and standardized linebreaks
        cleaned = re.sub(r"\r\n|\r", "\n", raw_text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def fetch_url_content(self, url: str) -> str:
        """Scrapes core text content from a single web page (optimized for OpenStax)."""
        url = url.strip()
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL provided: '{url}'")

        try:
            response = requests.get(url, headers=HEADERS, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch content from URL '{url}': {e}") from e

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove irrelevant tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        # Prioritize main content containers (OpenStax specific selectors included)
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find("div", {"data-type": "page"}) or 
            soup.find("div", class_="main-content") or 
            soup.body
        )

        if not main_content:
            raise RuntimeError(f"Could not extract readable main text from URL '{url}'.")

        text = main_content.get_text(separator="\n", strip=True)
        return self.normalize_text(text)

    def fetch_batch_urls(self, url_list: list[str]) -> str:
        """Scrapes multiple URLs and stitches them into a single aggregated payload."""
        valid_urls = [u.strip() for u in url_list if u.strip()]
        if not valid_urls:
            raise ValueError("No valid URLs provided for batch ingestion.")

        aggregated_payload = []
        errors = []

        for idx, url in enumerate(valid_urls, start=1):
            try:
                content = self.fetch_url_content(url)
                aggregated_payload.append(f"=== CHAPTER SECTION {idx}: {url} ===")
                aggregated_payload.append(content)
                aggregated_payload.append("\n" + "="*50 + "\n")
            except Exception as e:
                logger.error("Error fetching URL %s: %s", url, e)
                errors.append(f"URL {idx} ({url}): {e}")

        if not aggregated_payload:
            raise RuntimeError(f"Batch processing failed for all URLs. Errors:\n" + "\n".join(errors))

        return "\n\n".join(aggregated_payload)
