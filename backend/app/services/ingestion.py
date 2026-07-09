"""Brand voice ingestion service.

Provides:
- scrape_website(url) — fetches and extracts clean text from a website
- extract_clean_text(html) — strips nav/footer/ads from HTML, returns text
- extract_file_text(file_bytes, filename) — extracts text from .txt/.md/.docx
- extract_voice_profile(combined_text, client_id, session) — calls Gemini with retry
"""

import asyncio
import io
import logging
import re
import uuid
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import sentry_sdk
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.clients import update_client
from app.integrations import gemini  # AR-19: only called from ingestion.py / generation.py

logger = logging.getLogger(__name__)

# Cost-control cap: max characters passed to Gemini
MAX_TEXT_CHARS = 50_000

# Heuristic path segments that indicate blog/article pages
_BLOG_PATH_PATTERNS = re.compile(
    r"(/blog/|/post/|/posts/|/article/|/articles/|/news/|/journal/)",
    re.IGNORECASE,
)
# URL date pattern: /YYYY/MM/ — strong signal for blog posts
_DATE_PATH_PATTERN = re.compile(r"/(\d{4})/(\d{2})/")

# HTML elements to strip (noise — nav, footer, ads, etc.)
_STRIP_TAGS = {"nav", "footer", "header", "aside", "script", "style", "noscript"}
_STRIP_CLASS_PATTERNS = re.compile(
    r"\b(menu|cookie|banner|ad|sidebar|social|widget|promo|popup|modal|overlay)\b",
    re.IGNORECASE,
)


class ScrapingError(Exception):
    """Raised when website scraping fails in a way that should be reported."""


class VoiceExtractionError(Exception):
    """Raised when Gemini voice extraction fails after all retries."""


def extract_clean_text(html_content: str) -> str:
    """Parse HTML and return clean readable text.

    Removes navigation, footers, headers, sidebars, ads, and cookie banners.
    Extracts text from article/main/p/h1-h3 elements.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove noisy structural tags
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    # Remove elements whose class attribute contains noise patterns.
    # Guard against detached Tag objects (parent already decomposed above) whose
    # .get() raises AttributeError in some BeautifulSoup versions.
    for tag in soup.find_all(class_=True):
        try:
            tag_classes = tag.get("class") or []
        except AttributeError:
            continue
        classes = " ".join(tag_classes)
        if _STRIP_CLASS_PATTERNS.search(classes):
            tag.decompose()

    # Remove elements with role="navigation" or role="banner"
    for tag in soup.find_all(attrs={"role": ["navigation", "banner", "complementary"]}):
        tag.decompose()

    # Prefer article/main content if present
    content_tags = soup.find_all(["article", "main"]) or [soup]

    parts: list[str] = []
    for container in content_tags:
        for el in container.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            text = el.get_text(separator=" ", strip=True)
            if text:
                parts.append(text)

    # Fallback: if nothing found, grab all text
    if not parts:
        parts = [soup.get_text(separator="\n", strip=True)]

    combined = "\n".join(parts)
    # Collapse multiple blank lines
    combined = re.sub(r"\n{3,}", "\n\n", combined)
    return combined.strip()


def _score_url_recency(url: str) -> tuple[int, int]:
    """Return (year, month) from URL date pattern, or (0, 0) if no date."""
    m = _DATE_PATH_PATTERN.search(url)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def _is_blog_url(url: str, base_domain: str) -> bool:
    """Return True if the URL looks like a blog post / article page."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    # Must be same domain
    if parsed.netloc and parsed.netloc != base_domain:
        return False
    path = parsed.path
    if _BLOG_PATH_PATTERNS.search(path):
        return True
    if _DATE_PATH_PATTERN.search(path):
        return True
    return False


async def scrape_website(url: str) -> str:
    """Scrape a website and return clean combined text from up to 10 blog posts.

    Args:
        url: The root URL of the website to scrape.

    Returns:
        Combined clean text from all extracted pages (capped at MAX_TEXT_CHARS).

    Raises:
        ScrapingError: When the site is unreachable or returns a non-200 response.
    """
    parsed_root = urlparse(url)
    base_domain = parsed_root.netloc

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "PersonnaPress/1.0 (+https://personnapress.com/bot)"},
    ) as client:
        # 1. Fetch root page
        try:
            root_resp = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ScrapingError(f"Could not reach {url}: request timed out") from exc
        except httpx.ConnectError as exc:
            raise ScrapingError(f"Could not reach {url}: connection refused") from exc

        if root_resp.status_code != 200:
            raise ScrapingError(
                f"Could not reach {url}: HTTP {root_resp.status_code}"
            )

        root_html = root_resp.text
        root_text = extract_clean_text(root_html)

        # 2. Discover blog post URLs from root page
        soup = BeautifulSoup(root_html, "html.parser")
        candidate_urls: list[str] = []
        seen: set[str] = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            # Resolve relative URLs
            absolute = urljoin(url, href)
            # Strip query/fragment for deduplication
            clean = urlparse(absolute)._replace(query="", fragment="").geturl()
            if clean in seen:
                continue
            seen.add(clean)
            if _is_blog_url(clean, base_domain):
                candidate_urls.append(clean)

        # Sort by recency (date in URL is strongest signal)
        candidate_urls.sort(key=lambda u: _score_url_recency(u), reverse=True)
        post_urls = candidate_urls[:10]

        # 3. Fetch blog posts concurrently (max 5 at a time)
        sem = asyncio.Semaphore(5)

        async def fetch_post(post_url: str) -> str:
            async with sem:
                try:
                    resp = await client.get(post_url)
                    if resp.status_code == 200:
                        return extract_clean_text(resp.text)
                except Exception:
                    logger.warning("Failed to fetch post: %s", post_url)
                return ""

        if post_urls:
            post_texts = await asyncio.gather(*[fetch_post(u) for u in post_urls])
        else:
            post_texts = []

        # 4. Combine root page + post texts
        all_texts = [root_text] + [t for t in post_texts if t]
        combined = "\n\n---\n\n".join(all_texts)
        return combined[:MAX_TEXT_CHARS]


def extract_file_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from uploaded file bytes.

    Supports .txt, .md (UTF-8 decoded), and .docx (via python-docx).
    Unknown extensions return an empty string (files are validated on upload).
    """
    lower = filename.lower()
    if lower.endswith(".txt") or lower.endswith(".md"):
        return file_bytes.decode("utf-8", errors="replace")

    if lower.endswith(".docx"):
        try:
            from docx import Document  # python-docx

            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        except Exception as exc:
            logger.warning("Failed to extract text from %s: %s", filename, exc)
            return ""

    # Unknown extension — safety fallback (upload validation should prevent this)
    logger.warning("extract_file_text: unsupported extension for %s", filename)
    return ""


async def extract_voice_profile(
    combined_text: str,
    client_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> dict:
    """Extract a brand voice profile from combined text using Gemini.

    Calls integrations/gemini.py → extract_brand_voice() with up to 3 attempts.
    Exponential backoff: 1 s after attempt 1, 2 s after attempt 2.

    On success:
      - Updates clients.brand_voice_profile via the repository (if session provided).
      - Returns the BVP dict.

    On 3 consecutive failures:
      - Logs to Sentry.
      - Raises VoiceExtractionError.

    Args:
        combined_text: Content to analyse (caller is responsible for capping length).
        client_id: UUID of the client whose BVP is being extracted.
        session: Optional async DB session; if provided, updates client record on success.

    Raises:
        VoiceExtractionError: When all 3 Gemini call attempts fail.
    """
    logger.info(
        "extract_voice_profile: starting extraction for client %s (%d chars)",
        client_id,
        len(combined_text),
    )

    last_error: Optional[Exception] = None
    for attempt in range(3):
        try:
            bvp = await gemini.extract_brand_voice(combined_text, thinking_tokens=1024)

            if session is not None:
                await update_client(session, client_id, brand_voice_profile=bvp)
                logger.info(
                    "extract_voice_profile: client %s BVP updated in DB",
                    client_id,
                )

            logger.info(
                "extract_voice_profile: success for client %s on attempt %d",
                client_id,
                attempt + 1,
            )
            return bvp

        except ValueError:
            # Non-transient: Gemini returned unparseable JSON — no point retrying
            raise
        except Exception as exc:
            last_error = exc
            logger.warning(
                "extract_voice_profile: attempt %d failed for client %s: %s",
                attempt + 1,
                client_id,
                exc,
            )
            if attempt < 2:
                await asyncio.sleep(2**attempt)  # 1 s, 2 s

    sentry_sdk.capture_exception(last_error)
    raise VoiceExtractionError(str(last_error))
