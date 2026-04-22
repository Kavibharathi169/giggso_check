import logging
import os
import random
import time
import uuid
from collections import deque
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 OPR/102.0.0.0",
]

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif",
    ".zip", ".xlsx", ".docx", ".pptx", ".mp4",
    ".mp3", ".css", ".js", ".svg", ".ico",
)


def _get_robot_parser(base_url: str) -> RobotFileParser:
    """Create and load a robots.txt parser for the given base URL."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception as e:
        logger.warning(f"Could not read robots.txt from {robots_url}: {e}")
    return rp


def _should_skip_url(url: str) -> bool:
    """Check if URL should be skipped based on extension or fragment."""
    parsed = urlparse(url)
    if parsed.fragment:
        return True
    return any(parsed.path.lower().endswith(ext) for ext in SKIP_EXTENSIONS)


def _is_same_domain(base_url: str, link_url: str) -> bool:
    """Check if link belongs to the same domain as base URL."""
    return urlparse(base_url).netloc == urlparse(link_url).netloc


def _fetch_with_retry(
    session: requests.Session,
    url: str,
    max_retries: int = 3
) -> str | None:
    """Fetch a URL with exponential backoff retry. Returns HTML or None."""
    for attempt in range(1, max_retries + 1):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        try:
            response = session.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Non-200 response ({response.status_code}) for {url} — attempt {attempt}/{max_retries}")
        except Exception as e:
            logger.warning(f"Fetch failed for {url} — attempt {attempt}/{max_retries}: {e}")
        if attempt < max_retries:
            time.sleep(2 ** attempt)
    return None


def _extract_table_text(table_tag) -> str:
    """Convert a BeautifulSoup table to pipe-delimited text."""
    rows = []
    for tr in table_tag.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _extract_blocks(url: str, html: str, org_name: str, doc_type: str) -> list[dict]:
    """Extract structured content blocks from a single HTML page."""
    blocks = []

    clean_text = trafilatura.extract(html)
    whitelist = clean_text if clean_text else None
    if not whitelist:
        logger.warning(f"trafilatura returned None for {url} — falling back to BeautifulSoup")

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("title")
    doc_title = title_tag.get_text(strip=True) if title_tag else ""

    section_title = ""
    block_index = 0

    for element in soup.find_all(["h1", "h2", "h3", "p", "li", "table"]):
        tag_name = element.name
        is_heading = tag_name in ["h1", "h2", "h3"]
        is_table = tag_name == "table"

        if is_table:
            text = _extract_table_text(element)
            has_table = True
        else:
            text = element.get_text(separator=" ", strip=True)
            has_table = False

        if not text or len(text) < 10:
            continue

        if is_heading:
            section_title = text

        # For paragraphs/list items, filter against trafilatura whitelist
        if not is_heading and not is_table and whitelist:
            if text not in whitelist:
                logger.debug(f"Discarding noise: {text[:60]}")
                continue

        if len(text) < 50 and not is_heading:
            continue

        blocks.append({
            "text"         : text,
            "source"       : url,
            "section_title": section_title or doc_title or "Unknown",
            "page_number"  : 0,
            "block_index"  : block_index,
            "format"       : "webpage",
            "org_name"     : org_name,
            "doc_type"     : doc_type,
            "char_count"   : len(text),
            "word_count"   : len(text.split()),
            "has_table"    : has_table,
            "is_heading"   : is_heading,
        })
        block_index += 1

    return blocks


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract all internal links from a page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a_tag in soup.find_all("a", href=True):
        full_url = urljoin(base_url, a_tag["href"]).split("#")[0]
        if (
            full_url
            and _is_same_domain(base_url, full_url)
            and full_url.startswith("http")
            and not _should_skip_url(full_url)
        ):
            links.append(full_url)
    return list(set(links))


def scrape_url(
    url      : str,
    org_name : str,
    doc_type : str,
    max_pages: int = 10
) -> list[dict]:
    """BFS crawl from seed URL. Returns list of content blocks."""
    logger.info(f"Starting scrape: {url} (max_pages={max_pages})")

    robot_parser = _get_robot_parser(url)
    session      = requests.Session()
    queue        : deque      = deque([(url, 0)])
    visited      : set        = set()
    all_blocks   : list[dict] = []

    while queue and len(visited) < max_pages:
        current_url, depth = queue.popleft()

        if current_url in visited:
            continue

        if not robot_parser.can_fetch("*", current_url) and \
           not robot_parser.can_fetch("Mozilla/5.0", current_url):
            logger.warning(f"Blocked by robots.txt: {current_url}")
            continue

        visited.add(current_url)
        logger.info(f"Crawling [{len(visited)}/{max_pages}]: {current_url}")

        time.sleep(random.uniform(2, 3))

        html = _fetch_with_retry(session, current_url)
        if html is None:
            continue

        try:
            blocks = _extract_blocks(current_url, html, org_name, doc_type)
            all_blocks.extend(blocks)
            logger.info(f"Extracted {len(blocks)} blocks from {current_url}")
        except Exception as e:
            logger.error(f"Extraction failed for {current_url}: {e}")
            continue

        try:
            links = _extract_links(html, current_url)
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1))
        except Exception as e:
            logger.warning(f"Link extraction failed for {current_url}: {e}")

    logger.info(f"Scrape complete. Blocks: {len(all_blocks)}, Pages: {len(visited)}")
    return all_blocks


# Legacy alias used by existing router.py
def scrape(
    seed_url     : str,
    document_type: str,
    org_name     : str,
    max_depth    : int = 2
) -> list[dict]:
    """Legacy BFS scraper — delegates to scrape_url."""
    return scrape_url(
        url      = seed_url,
        org_name = org_name,
        doc_type = document_type,
        max_pages= 10
    )
