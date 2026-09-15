"""
utils/ingestion.py

CurriculumIngestor: Cleans, normalizes, and aggregates raw curriculum input
from text strings, OpenStax chapters, or multiple webpage URLs into a unified session payload.
"""
import re
import socket
import ipaddress
import logging
from urllib.parse import urlparse, urljoin, urldefrag
from collections import OrderedDict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SEC = 12
MIN_CONTENT_LENGTH = 100
MAX_CRAWL_PAGES = 20
SECTION_SEPARATOR = "\n" + "=" * 60 + "\n"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

OPENSTAX_PAGE_RE = re.compile(r"(/books/[^/]+/pages/)(\d+)-([a-zA-Z0-9\-]+)")
NEXT_LINK_KEYWORDS = re.compile(r"\b(next|next section|next page|continue|→|>)\b", re.IGNORECASE)
PREV_LINK_KEYWORDS = re.compile(r"\b(prev|previous|back|←|<)\b", re.IGNORECASE)


class IngestionError(Exception):
    pass


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname or hostname.lower() in ("localhost", "127.0.0.1", "::1"):
            return False
        resolved_ip = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved_ip)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or resolved_ip.startswith("169.254."):
            return False
        return True
    except Exception:
        return False


def _clean_url(url: str) -> str:
    clean, _ = urldefrag(url)
    return clean.rstrip("/")


def _is_openstax_url(url: str) -> bool:
    return bool(OPENSTAX_PAGE_RE.search(url))


def _extract_chapter_number(url: str) -> str | None:
    match = OPENSTAX_PAGE_RE.search(url)
    return match.group(2) if match else None


def _extract_base_path(url: str) -> str | None:
    match = OPENSTAX_PAGE_RE.search(url)
    return match.group(1) if match else None


def _same_chapter(url: str, chapter: str, base_path: str) -> bool:
    match = OPENSTAX_PAGE_RE.search(url)
    return bool(match and match.group(1) == base_path and match.group(2) == chapter)


class CurriculumIngestor:
    def __init__(self, timeout: int = REQUEST_TIMEOUT_SEC, max_pages: int = MAX_CRAWL_PAGES):
        self.timeout = timeout
        self.max_pages = max_pages

    def normalize_text(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            raise IngestionError("Input curriculum text is empty.")
        cleaned = re.sub(r"\r\n|\r", "\n", raw_text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        result = cleaned.strip()
        if len(result) < MIN_CONTENT_LENGTH:
            raise IngestionError(f"Content too brief ({len(result)} chars).")
        return result

    def fetch_url_content(self, url: str) -> str:
        clean_target = _clean_url(url)
        parsed = urlparse(clean_target)
        if not parsed.scheme or not parsed.netloc:
            raise IngestionError(f"Invalid URL: '{url}'")
        if parsed.scheme not in ("http", "https"):
            raise IngestionError(f"Only http/https supported: '{url}'")
        resp = self._get(clean_target)
        soup = self._parse_soup(resp)
        return self._extract_main_text(soup, clean_target)

    def fetch_batch_urls(self, url_list: list[str]) -> str:
        valid_urls = [_clean_url(u) for u in url_list if u.strip()]
        if not valid_urls:
            raise IngestionError("No valid URLs provided.")
        return self._aggregate(valid_urls, label="BATCH")

    def smart_crawl(self, seed_url: str) -> tuple[str, list[str]]:
        seed_clean = _clean_url(seed_url)
        if not _is_safe_url(seed_clean):
            raise IngestionError(f"Security Alert: Blocked restricted destination: '{seed_url}'")

        if _is_openstax_url(seed_clean):
            urls = self._method1_chapter_pattern(seed_clean)
            for u in self._method2_next_page_follower(seed_clean):
                if u not in urls:
                    urls.append(u)
        else:
            urls = self._method2_next_page_follower(seed_clean)

        if not urls:
            urls = [seed_clean]

        payload = self._aggregate(urls, label="OPENSTAX SECTION" if _is_openstax_url(seed_clean) else "CHAPTER SECTION")
        return payload, urls
      def _method1_chapter_pattern(self, seed_url: str) -> list[str]:
        chapter = _extract_chapter_number(seed_url)
        base_path = _extract_base_path(seed_url)
        if not chapter or not base_path:
            return [seed_url]

        try:
            resp = self._get(seed_url)
            soup = BeautifulSoup(resp.text, "html.parser")
        except IngestionError:
            return [seed_url]

        discovered: OrderedDict[str, None] = OrderedDict()
        discovered[seed_url] = None
        base_domain = f"{urlparse(seed_url).scheme}://{urlparse(seed_url).netloc}"

        for tag in soup.find_all("a", href=True):
            full_url = _clean_url(urljoin(base_domain, tag["href"].strip()))
            if _same_chapter(full_url, chapter, base_path) and _is_safe_url(full_url):
                discovered[full_url] = None

        urls = list(discovered.keys())

        def _sort_key(url: str) -> int:
            match = OPENSTAX_PAGE_RE.search(url)
            if not match:
                return 0
            try:
                return int(match.group(3).split("-")[0])
            except (ValueError, IndexError):
                return 0

        rest = [u for u in urls if u != seed_url]
        rest.sort(key=_sort_key)
        return ([seed_url] + rest)[: self.max_pages]

    def _method2_next_page_follower(self, seed_url: str) -> list[str]:
        visited: list[str] = []
        seen_set: set[str] = set()
        current = seed_url
        seed_chapter = _extract_chapter_number(seed_url)
        seed_base_path = _extract_base_path(seed_url)

        while current and len(visited) < self.max_pages:
            if current in seen_set or not _is_safe_url(current):
                break
            visited.append(current)
            seen_set.add(current)

            try:
                resp = self._get(current)
                soup = BeautifulSoup(resp.text, "html.parser")
            except IngestionError:
                break

            next_url = self._find_next_link(soup, current)
            if not next_url:
                break

            next_url = _clean_url(next_url)
            if seed_chapter and seed_base_path:
                if not _same_chapter(next_url, seed_chapter, seed_base_path):
                    break
            current = next_url

        return visited

    def _find_next_link(self, soup: BeautifulSoup, current_url: str) -> str | None:
        base_domain = f"{urlparse(current_url).scheme}://{urlparse(current_url).netloc}"
        rel_next = soup.find("link", rel="next")
        if rel_next and rel_next.get("href"):
            cand = _clean_url(urljoin(base_domain, rel_next["href"]))
            if _is_safe_url(cand):
                return cand

        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            text = tag.get_text(strip=True)
            comb = f"{text} {tag.get('aria-label', '')} {tag.get('title', '')}"
            if not href or href.startswith("#") or href.startswith("mailto:") or PREV_LINK_KEYWORDS.search(text):
                continue
            if NEXT_LINK_KEYWORDS.search(comb):
                target = _clean_url(urljoin(base_domain, href))
                if _is_safe_url(target):
                    return target
        return None

    def _get(self, url: str) -> requests.Response:
        if not _is_safe_url(url):
            raise IngestionError(f"Restricted address blocked: '{url}'")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=self.timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp
        except requests.exceptions.Timeout:
            raise IngestionError(f"Timeout on '{url}' ({self.timeout}s).")
        except requests.exceptions.HTTPError as e:
            raise IngestionError(f"HTTP {e.response.status_code} on '{url}'.")
        except requests.RequestException as e:
            raise IngestionError(f"Connection failed for '{url}': {e}") from e

    def _parse_soup(self, response: requests.Response) -> BeautifulSoup:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg", "math", "annotation"]):
            tag.decompose()
        return soup

    def _extract_main_text(self, soup: BeautifulSoup, url: str) -> str:
        main_content = (
            soup.find("div", {"data-type": "page"})
            or soup.find("div", class_="os-raise-ib-content")
            or soup.find("main")
            or soup.find("article")
            or soup.find("div", class_="main-content")
            or soup.find("div", id="main-content")
            or soup.body
        )
        if not main_content:
            raise IngestionError(f"Could not find textbook container in '{url}'.")
        raw = main_content.get_text(separator="\n", strip=True)
        content = self.normalize_text(raw)
        if len(content) < MIN_CONTENT_LENGTH:
            raise IngestionError(f"Content too short ({len(content)} chars): '{url}'")
        return content

    def _aggregate(self, urls: list[str], label: str = "SECTION") -> str:
        sections, errors = [], []
        for idx, url in enumerate(urls, start=1):
            try:
                resp = self._get(url)
                soup = self._parse_soup(resp)
                content = self._extract_main_text(soup, url)
                sections.extend([f"=== {label} {idx}/{len(urls)}: {url} ===", content, SECTION_SEPARATOR])
            except IngestionError as e:
                errors.append(f"- {url}: {e}")

        if not sections:
            raise IngestionError(f"Failed all {len(urls)} URLs:\n" + "\n".join(errors))

        if errors:
            warning_header = "⚠️ PARTIAL EXTRACTION:\n" + "\n".join(errors) + "\n\nRetrieved sections:\n" + SECTION_SEPARATOR
            sections.insert(0, warning_header)

        return "\n\n".join(sections)
