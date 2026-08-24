"""
utils/ingestion.py

CurriculumIngestor: Cleans, normalizes, and aggregates raw curriculum input
from text strings or multiple webpage URLs into a unified session payload.

Smart crawl modes:
  - Method 1: Same-chapter pattern crawler — detects chapter number from seed
    URL and auto-discovers all sibling section URLs matching the same pattern.
  - Method 2: Next-page follower — follows "Next Section" / "→" links
    sequentially until the chapter boundary is crossed or no next link exists.
  - Manual batch: user supplies explicit list of URLs (existing behaviour).
"""
import re
import logging
from urllib.parse import urlparse, urljoin, urldefrag
from collections import OrderedDict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SEC = 10
MIN_CONTENT_LENGTH  = 100      # chars — below this a scrape is considered empty
MAX_CRAWL_PAGES     = 20       # safety ceiling for both smart crawl methods
SECTION_SEPARATOR   = "\n" + "=" * 60 + "\n"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# OpenStax URL pattern: /books/<book-slug>/pages/<chapter>-<section>-<slug>
# Capture groups: (1) book slug, (2) chapter number, (3) full section slug
OPENSTAX_PAGE_RE = re.compile(
    r"(/books/[^/]+/pages/)(\d+)-(.+)"
)

# Keywords that signal a "next page" link
NEXT_LINK_KEYWORDS = re.compile(
    r"\b(next|next section|next page|continue|→|>)\b",
    re.IGNORECASE,
)

# Keywords that signal a "previous" link (used to avoid going backwards)
PREV_LINK_KEYWORDS = re.compile(
    r"\b(prev|previous|back|←|<)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# CUSTOM EXCEPTIONS
# ---------------------------------------------------------------------------

class IngestionError(Exception):
    """Raised when ingestion fails in a way the caller should handle visibly."""


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _is_openstax_url(url: str) -> bool:
    return bool(OPENSTAX_PAGE_RE.search(url))


def _extract_chapter_number(url: str) -> str | None:
    """Return the chapter number string from an OpenStax URL, or None."""
    match = OPENSTAX_PAGE_RE.search(url)
    return match.group(2) if match else None


def _extract_base_path(url: str) -> str | None:
    """Return the /books/<slug>/pages/ prefix from an OpenStax URL, or None."""
    match = OPENSTAX_PAGE_RE.search(url)
    return match.group(1) if match else None


def _same_chapter(url: str, chapter: str, base_path: str) -> bool:
    """Return True if url belongs to the same chapter as the seed."""
    match = OPENSTAX_PAGE_RE.search(url)
    if not match:
        return False
    return match.group(1) == base_path and match.group(2) == chapter


def _clean_url(url: str) -> str:
    """Strip fragments (#) from a URL."""
    clean, _ = urldefrag(url)
    return clean


# ---------------------------------------------------------------------------
# MAIN CLASS
# ---------------------------------------------------------------------------

class CurriculumIngestor:
    """Scrapes, cleans, and aggregates curriculum content from URLs or raw text.

    Smart crawl methods (Methods 1 & 2) are invoked automatically based on
    the seed URL structure. Falls back to single-page fetch for non-OpenStax
    or unrecognised URL patterns.

    Args:
        timeout:   HTTP request timeout in seconds.
        max_pages: Maximum pages to crawl in smart modes (safety ceiling).
    """

    def __init__(
        self,
        timeout:   int = REQUEST_TIMEOUT_SEC,
        max_pages: int = MAX_CRAWL_PAGES,
    ) -> None:
        self.timeout   = timeout
        self.max_pages = max_pages

    # -----------------------------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------------------------

    def normalize_text(self, raw_text: str) -> str:
        """Clean and standardise raw text input.

        Raises:
            IngestionError: if input is empty or too short after cleaning.
        """
        if not raw_text or not raw_text.strip():
            raise IngestionError("Input text is empty.")

        cleaned = re.sub(r"\r\n|\r", "\n", raw_text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

        result = cleaned.strip()
        if len(result) < MIN_CONTENT_LENGTH:
            raise IngestionError(
                f"Normalized text is too short ({len(result)} chars). "
                "Please provide more substantial curriculum content."
            )
        return result

    def fetch_url_content(self, url: str) -> str:
        """Scrape core text from a single web page.

        Raises:
            IngestionError: on invalid URL, HTTP error, or near-empty content.
        """
        url    = url.strip()
        parsed = urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            raise IngestionError(f"Invalid URL: '{url}'")
        if parsed.scheme not in ("http", "https"):
            raise IngestionError(f"Only http/https URLs supported. Got: '{url}'")

        response = self._get(url)
        soup     = self._parse_soup(response)
        content  = self._extract_main_text(soup, url)
        return content

    def fetch_batch_urls(self, url_list: list[str]) -> str:
        """Scrape an explicit list of URLs and aggregate into one payload.

        Partial failures are logged and prepended as warnings; the batch
        succeeds as long as at least one URL is fetched successfully.

        Raises:
            IngestionError: if ALL URLs fail.
        """
        valid_urls = [u.strip() for u in url_list if u.strip()]
        if not valid_urls:
            raise IngestionError("No valid URLs provided for batch ingestion.")
        return self._aggregate(valid_urls, label="BATCH")

    def smart_crawl(self, seed_url: str) -> tuple[str, list[str]]:
        """Auto-discover and fetch all sections related to the seed URL.

        Strategy selection:
          1. If the seed is an OpenStax URL → Method 1 (chapter pattern crawler)
             followed by Method 2 (next-page follower) as a completeness check.
          2. Otherwise → Method 2 only (next-page follower).

        Returns:
            (aggregated_payload: str, discovered_urls: list[str])
            The discovered_urls list lets the UI show the user exactly what
            was crawled before consuming the payload.

        Raises:
            IngestionError: if no content could be retrieved at all.
        """
        seed_url = seed_url.strip()

        if _is_openstax_url(seed_url):
            logger.info("OpenStax URL detected — using Method 1 (chapter pattern crawler).")
            urls = self._method1_chapter_pattern(seed_url)

            # Method 2 as completeness check: find any pages Method 1 missed
            method2_urls = self._method2_next_page_follower(seed_url)
            for u in method2_urls:
                if u not in urls:
                    logger.info("Method 2 found additional URL not in pattern set: %s", u)
                    urls.append(u)
        else:
            logger.info("Non-OpenStax URL — using Method 2 (next-page follower).")
            urls = self._method2_next_page_follower(seed_url)

        if not urls:
            raise IngestionError(
                "Smart crawl could not discover any related pages from the seed URL. "
                "Try pasting the URLs manually in Batch mode."
            )

        payload = self._aggregate(urls, label="SMART CRAWL")
        return payload, urls

    # -----------------------------------------------------------------------
    # METHOD 1 — SAME-CHAPTER PATTERN CRAWLER
    # -----------------------------------------------------------------------

    def _method1_chapter_pattern(self, seed_url: str) -> list[str]:
        """Discover all sibling section URLs sharing the same chapter number.

        How it works:
          1. Extract chapter number and base path from the seed URL.
          2. Fetch the seed page and collect all href links.
          3. Filter links to those matching /books/<slug>/pages/<chapter>-*
          4. De-duplicate, sort by section number, and return ordered list.

        The seed URL is always included as the first entry even if not
        found in the page's own link set.
        """
        chapter   = _extract_chapter_number(seed_url)
        base_path = _extract_base_path(seed_url)

        if not chapter or not base_path:
            logger.warning("Could not extract chapter info from: %s", seed_url)
            return [seed_url]

        logger.info(
            "Method 1: scanning for chapter %s pages under %s", chapter, base_path
        )

        try:
            response = self._get(seed_url)
            soup     = BeautifulSoup(response.text, "html.parser")
        except IngestionError as e:
            logger.error("Method 1: could not fetch seed URL: %s", e)
            return [seed_url]

        # Collect all absolute URLs from the page that belong to this chapter
        discovered: OrderedDict[str, None] = OrderedDict()
        discovered[_clean_url(seed_url)] = None  # seed always first

        base_domain = f"{urlparse(seed_url).scheme}://{urlparse(seed_url).netloc}"

        for tag in soup.find_all("a", href=True):
            href     = tag["href"].strip()
            full_url = _clean_url(urljoin(base_domain, href))

            if _same_chapter(full_url, chapter, base_path):
                discovered[full_url] = None

        urls = list(discovered.keys())

        # Sort by section number: chapter-SECTION-slug → sort on SECTION int
        def _section_sort_key(url: str) -> int:
            match = OPENSTAX_PAGE_RE.search(url)
            if not match:
                return 0
            slug  = match.group(3)          # e.g. "2-special-interest-politics"
            parts = slug.split("-")
            try:
                return int(parts[0])        # section number
            except (ValueError, IndexError):
                return 0

        # Keep seed first, sort the rest
        seed_clean = _clean_url(seed_url)
        rest       = [u for u in urls if u != seed_clean]
        rest.sort(key=_section_sort_key)

        ordered = [seed_clean] + rest

        # Enforce page ceiling
        if len(ordered) > self.max_pages:
            logger.warning(
                "Method 1 discovered %d pages — truncating to %d (MAX_CRAWL_PAGES).",
                len(ordered), self.max_pages,
            )
            ordered = ordered[: self.max_pages]

        logger.info("Method 1 discovered %d chapter pages.", len(ordered))
        return ordered

    # -----------------------------------------------------------------------
    # METHOD 2 — NEXT-PAGE FOLLOWER
    # -----------------------------------------------------------------------

    def _method2_next_page_follower(self, seed_url: str) -> list[str]:
        """Follow 'Next Section' links sequentially until chapter boundary.

        How it works:
          1. Fetch the current page.
          2. Find all anchor tags whose visible text matches NEXT_LINK_KEYWORDS
             and whose text does NOT match PREV_LINK_KEYWORDS.
          3. Resolve the href to an absolute URL.
          4. If the next URL crosses the chapter boundary (different chapter
             number on OpenStax, or different path prefix elsewhere), stop.
          5. Add to the ordered list and repeat from step 1.
          6. Stop when no next link is found or MAX_CRAWL_PAGES is reached.

        Returns ordered list starting from seed_url.
        """
        visited:  list[str]     = []
        seen_set: set[str]      = set()
        current   = _clean_url(seed_url)

        seed_chapter   = _extract_chapter_number(seed_url)
        seed_base_path = _extract_base_path(seed_url)

        logger.info("Method 2: following next-page links from %s", seed_url)

        while current and len(visited) < self.max_pages:
            if current in seen_set:
                logger.warning("Method 2: cycle detected at %s — stopping.", current)
                break

            visited.append(current)
            seen_set.add(current)

            try:
                response = self._get(current)
                soup     = BeautifulSoup(response.text, "html.parser")
            except IngestionError as e:
                logger.error("Method 2: failed to fetch %s: %s", current, e)
                break

            next_url = self._find_next_link(soup, current)

            if not next_url:
                logger.info("Method 2: no next link found at %s — end of chapter.", current)
                break

            next_url = _clean_url(next_url)

            # Chapter boundary check for OpenStax
            if seed_chapter and seed_base_path:
                if not _same_chapter(next_url, seed_chapter, seed_base_path):
                    logger.info(
                        "Method 2: next link %s crosses chapter boundary — stopping.",
                        next_url,
                    )
                    break

            current = next_url

        logger.info("Method 2 followed %d pages.", len(visited))
        return visited

    def _find_next_link(self, soup: BeautifulSoup, current_url: str) -> str | None:
        """Find the best candidate 'next page' anchor on the current page.

        Scoring logic:
          - Anchor text matches NEXT_LINK_KEYWORDS: candidate
          - Anchor text also matches PREV_LINK_KEYWORDS: disqualified
          - Aria-label or title attribute matching next keywords: secondary candidate
          - rel="next" attribute: highest priority

        Returns the absolute URL of the best candidate, or None.
        """
        base_domain = f"{urlparse(current_url).scheme}://{urlparse(current_url).netloc}"
        best: str | None = None

        # Highest priority: rel="next" link tag in <head>
        rel_next = soup.find("link", rel="next")
        if rel_next and rel_next.get("href"):
            return _clean_url(urljoin(base_domain, rel_next["href"]))

        for tag in soup.find_all("a", href=True):
            href    = tag["href"].strip()
            text    = tag.get_text(strip=True)
            aria    = tag.get("aria-label", "")
            title   = tag.get("title", "")
            combined = f"{text} {aria} {title}"

            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            if PREV_LINK_KEYWORDS.search(text):
                continue
            if NEXT_LINK_KEYWORDS.search(combined):
                full_url = urljoin(base_domain, href)
                best     = _clean_url(full_url)
                break   # first matching candidate wins

        return best

    # -----------------------------------------------------------------------
    # SHARED INTERNAL UTILITIES
    # -----------------------------------------------------------------------

    def _get(self, url: str) -> requests.Response:
        """Execute a GET request with consistent error handling."""
        try:
            response = requests.get(url, headers=HEADERS, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response
        except requests.exceptions.Timeout:
            raise IngestionError(f"Request timed out after {self.timeout}s: '{url}'")
        except requests.exceptions.HTTPError as e:
            raise IngestionError(
                f"HTTP {e.response.status_code} error fetching '{url}': {e}"
            )
        except requests.RequestException as e:
            raise IngestionError(f"Network error fetching '{url}': {e}") from e

    def _parse_soup(self, response: requests.Response) -> BeautifulSoup:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        return soup

    def _extract_main_text(self, soup: BeautifulSoup, url: str) -> str:
        """Pull the main readable text block from a parsed page."""
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"data-type": "page"})
            or soup.find("div", class_="main-content")
            or soup.body
        )

        if not main_content:
            raise IngestionError(f"Could not locate main content container in '{url}'.")

        raw     = main_content.get_text(separator="\n", strip=True)
        content = self.normalize_text(raw)

        if len(content) < MIN_CONTENT_LENGTH:
            raise IngestionError(
                f"Page returned near-empty content ({len(content)} chars). "
                f"It may require JavaScript rendering: '{url}'"
            )
        return content

    def _aggregate(self, urls: list[str], label: str = "SECTION") -> str:
        """Fetch each URL and stitch results into one payload string.

        Partial failures are logged and prepended as warnings.
        Raises IngestionError if ALL URLs fail.
        """
        sections: list[str] = []
        errors:   list[str] = []

        for idx, url in enumerate(urls, start=1):
            try:
                response = self._get(url)
                soup     = self._parse_soup(response)
                content  = self._extract_main_text(soup, url)
                sections.append(f"=== {label} {idx}/{len(urls)}: {url} ===")
                sections.append(content)
                sections.append(SECTION_SEPARATOR)
                logger.info("%s %d/%d fetched OK: %s", label, idx, len(urls), url)
            except IngestionError as e:
                logger.error("%s %d/%d failed (%s): %s", label, idx, len(urls), url, e)
                errors.append(f"⚠️ {label} {idx} failed ({url}): {e}")

        if not sections:
            raise IngestionError(
                f"All {len(urls)} URL(s) failed to load:\n" + "\n".join(errors)
            )

        if errors:
            notice = (
                "⚠️ PARTIAL RESULTS — the following pages could not be fetched:\n"
                + "\n".join(errors)
                + "\n\nSuccessfully retrieved sections below:\n"
                + SECTION_SEPARATOR
            )
            sections.insert(0, notice)

        return "\n\n".join(sections)
