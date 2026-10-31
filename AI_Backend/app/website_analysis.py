"""Standalone Website Scraping and Analysis Module for BrandProof AI.

Extracts meaningful website content (single-page or limited crawl) and uses
the existing Gemini integration to analyze grammar, tone, brand consistency,
readability, marketing quality, and SEO-related factors.
"""

from html.parser import HTMLParser
import ipaddress
import json
import logging
import re
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
import urllib.robotparser

import requests

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "BrandProofAI-Bot/1.0 (+https://brandproof.ai)"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_REDIRECTS = 5

# Blocked hostnames associated with local/internal environments or cloud metadata
BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
}

# Sensitive path keywords to avoid crawling
SENSITIVE_PATH_PATTERNS = [
    r"/login",
    r"/logout",
    r"/signin",
    r"/signout",
    r"/register",
    r"/signup",
    r"/account",
    r"/admin",
    r"/auth",
    r"/cart",
    r"/checkout",
    r"/password",
    r"/reset-password",
]


def is_safe_ip(ip_str: str) -> bool:
    """Checks whether an IP address is a safe, publicly routable address."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
        # Specific check for AWS/GCP/Azure link-local metadata (169.254.169.254)
        if str(ip) == "169.254.169.254":
            return False
        return True
    except ValueError:
        return False


def resolve_and_validate_host(hostname: str) -> Tuple[bool, str]:
    """Resolves a hostname to IP addresses and verifies none are private or blocked."""
    cleaned_host = hostname.strip().lower()
    if not cleaned_host:
        return False, "Empty hostname."

    if cleaned_host in BLOCKED_HOSTNAMES:
        return False, f"Access to '{cleaned_host}' is blocked for security reasons."

    # If it's already an IP literal
    try:
        ip_obj = ipaddress.ip_address(cleaned_host)
        if not is_safe_ip(str(ip_obj)):
            return False, f"Access to IP address '{cleaned_host}' is blocked."
        return True, str(ip_obj)
    except ValueError:
        pass

    # Resolve hostname via DNS
    try:
        addr_info = socket.getaddrinfo(cleaned_host, None)
        if not addr_info:
            return False, f"Could not resolve hostname '{cleaned_host}'."
        for item in addr_info:
            sockaddr = item[4]
            ip_candidate = sockaddr[0]
            if not is_safe_ip(ip_candidate):
                return False, f"Resolved IP '{ip_candidate}' is private or blocked."
        return True, "Host is valid and safe."
    except socket.gaierror as exc:
        return False, f"DNS resolution failed for '{cleaned_host}': {str(exc)}"
    except Exception as exc:
        return False, f"Host validation error: {str(exc)}"


def validate_url(url: str, check_dns: bool = True) -> Tuple[bool, str]:
    """Validates that a URL is well-formed, uses HTTP/HTTPS, and passes SSRF checks.

    Returns:
        (True, normalized_url) if valid, or (False, error_message) if invalid.
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string."

    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme '{scheme}'. Only HTTP and HTTPS are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname."

    # Always check IP literals even if DNS check is skipped
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if not is_safe_ip(str(ip_obj)):
            return False, f"SSRF Protection: Access to private/loopback IP '{hostname}' is blocked."
    except ValueError:
        pass

    # Validate hostname and SSRF
    if check_dns:
        safe, msg = resolve_and_validate_host(hostname)
        if not safe:
            return False, f"SSRF Protection: {msg}"
    else:
        # Check hostname literal against blocked set
        if hostname.lower() in BLOCKED_HOSTNAMES:
            return False, f"SSRF Protection: Access to '{hostname}' is blocked."

    # Normalize URL (keep scheme, netloc, path, query; discard fragment)
    normalized = urlunparse((
        scheme,
        parsed.netloc,
        parsed.path or "/",
        "",
        parsed.query,
        "",
    ))
    return True, normalized


def is_robots_allowed(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = 3.0,
    check_dns: bool = True,
    session: Optional[requests.Session] = None,
) -> bool:
    """Checks robots.txt for the given URL to verify access permissions."""
    try:
        parsed = urlparse(url)
        robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
        valid, _ = validate_url(robots_url, check_dns=check_dns)
        if not valid:
            return False

        http = session or requests.Session()
        resp = http.get(
            robots_url,
            headers={"User-Agent": user_agent},
            timeout=timeout,
            allow_redirects=False,
        )
        if resp.status_code == 200 and resp.text:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(resp.text.splitlines())
            return rp.can_fetch(user_agent, url)
        # If 404 or other non-200, assume allowed
        return True
    except Exception:
        # On error reading robots.txt, default to allowed for public sites
        return True


def fetch_website(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_redirects: int = MAX_REDIRECTS,
    max_bytes: int = MAX_RESPONSE_BYTES,
    check_dns: bool = True,
    check_robots: bool = False,
    session: Optional[requests.Session] = None,
) -> Tuple[bool, str, str]:
    """Fetches public HTML content from a website with SSRF protection and redirect safety.

    Args:
        url: Target web page URL.
        timeout: Network timeout in seconds.
        max_redirects: Maximum allowable redirect hops.
        max_bytes: Maximum allowed HTML size in bytes.
        check_dns: Whether to perform DNS resolution checks for SSRF.
        check_robots: Whether to check robots.txt policy prior to fetching.
        session: Optional pre-configured requests.Session (useful for mocking/testing).

    Returns:
        (success: bool, html_or_error: str, final_url: str)
    """
    valid, norm_url = validate_url(url, check_dns=check_dns)
    if not valid:
        return False, norm_url, url

    current_url = norm_url
    http = session or requests.Session()
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    if check_robots and not is_robots_allowed(
        current_url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=min(timeout, 3.0),
        check_dns=check_dns,
        session=http,
    ):
        return False, "Access disallowed by website robots.txt policy.", current_url

    redirect_count = 0
    while redirect_count <= max_redirects:
        try:
            resp = http.get(
                current_url,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )
        except requests.exceptions.Timeout:
            return False, f"Request to '{current_url}' timed out after {timeout}s.", current_url
        except requests.exceptions.SSLError:
            return False, f"SSL verification failed for '{current_url}'.", current_url
        except requests.exceptions.ConnectionError:
            return False, f"Failed to connect to website at '{current_url}'.", current_url
        except Exception as exc:
            return False, f"Request failed: {str(exc)}", current_url

        # Check for redirects
        if resp.status_code in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                return False, f"Exceeded maximum redirects limit of {max_redirects}.", current_url

            loc = resp.headers.get("Location")
            if not loc:
                return False, f"HTTP {resp.status_code} redirect without Location header.", current_url

            next_url = urljoin(current_url, loc)
            valid_next, norm_next = validate_url(next_url, check_dns=check_dns)
            if not valid_next:
                return False, f"Redirect to unsafe destination blocked: {norm_next}", next_url

            current_url = norm_next
            continue

        # Non-redirect status codes
        if resp.status_code != 200:
            return False, f"HTTP error {resp.status_code} occurred while loading page.", current_url

        # Read content safely with size limit
        content_type = resp.headers.get("Content-Type", "").lower()
        if content_type and "html" not in content_type and "text" not in content_type:
            return False, f"Unsupported Content-Type '{content_type}'. Expected HTML/text.", current_url

        chunks = []
        downloaded = 0
        try:
            for chunk in resp.iter_content(chunk_size=16384):
                if chunk:
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        return (
                            False,
                            f"Downloaded content exceeded limit of {max_bytes} bytes.",
                            current_url,
                        )
        except Exception as exc:
            return False, f"Error reading response body: {str(exc)}", current_url

        raw_bytes = b"".join(chunks)
        # Decode HTML
        encoding = resp.encoding or "utf-8"
        try:
            html_text = raw_bytes.decode(encoding, errors="replace")
        except Exception:
            html_text = raw_bytes.decode("utf-8", errors="replace")

class WebsiteContentExtractor(HTMLParser):
    """HTML Parser that extracts structured content, hierarchy, and metadata."""

    IGNORE_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe"}

    def __init__(self):
        super().__init__()
        self.title: str = ""
        self.meta_description: str = ""
        self.headings: List[Dict[str, str]] = []
        self.paragraphs: List[str] = []
        self.cta_text: List[str] = []
        self.image_alt_texts: List[str] = []
        self.lists: List[str] = []

        # Current section tracking
        self.sections: List[Dict[str, Any]] = []
        self.current_section_heading = "Introduction"
        self.current_section_level = "h1"
        self.current_section_paragraphs: List[str] = []

        # State tracking
        self._in_ignore = 0
        self._in_title = False
        self._current_tag = ""
        self._buffer: List[str] = []
        self._current_attrs: Dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()
        self._current_tag = tag_lower
        self._current_attrs = attr_dict

        if tag_lower in self.IGNORE_TAGS:
            self._in_ignore += 1
            return

        if self._in_ignore > 0:
            return

        # Title
        if tag_lower == "title":
            self._in_title = True
            self._buffer = []
            return

        # Meta description
        if tag_lower == "meta":
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            if name == "description" or prop in ("og:description", "twitter:description"):
                content = attr_dict.get("content", "").strip()
                if content and not self.meta_description:
                    self.meta_description = content
            return

        # Image alt attributes
        if tag_lower == "img":
            alt = attr_dict.get("alt", "").strip()
            if alt:
                self.image_alt_texts.append(alt)
            return

        # Buttons or CTA links
        if tag_lower == "button" or (tag_lower == "input" and attr_dict.get("type", "").lower() in ("button", "submit")):
            val = attr_dict.get("value", "").strip()
            if val:
                self.cta_text.append(val)
            self._buffer = []
            return

        if tag_lower == "a":
            classes = attr_dict.get("class", "").lower()
            rel = attr_dict.get("rel", "").lower()
            is_cta = any(k in classes for k in ("btn", "button", "cta", "action"))
            if is_cta:
                self._buffer = []
            return

        # Headings (h1, h2, h3)
        if tag_lower in ("h1", "h2", "h3"):
            # Close previous section if it had content
            if self.current_section_paragraphs:
                self.sections.append({
                    "heading": self.current_section_heading,
                    "level": self.current_section_level,
                    "content": " ".join(self.current_section_paragraphs),
                })
                self.current_section_paragraphs = []
            self._buffer = []
            return

        # Paragraphs & list items
        if tag_lower in ("p", "li"):
            self._buffer = []
            return

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()

        if tag_lower in self.IGNORE_TAGS:
            if self._in_ignore > 0:
                self._in_ignore -= 1
            return

        if self._in_ignore > 0:
            return

        text = " ".join("".join(self._buffer).split()).strip()

        if tag_lower == "title":
            self._in_title = False
            if text and not self.title:
                self.title = text
            self._buffer = []
            return

        if tag_lower in ("h1", "h2", "h3"):
            if text:
                self.headings.append({"level": tag_lower, "text": text})
                self.current_section_heading = text
                self.current_section_level = tag_lower
            self._buffer = []
            return

        if tag_lower == "button":
            if text and text not in self.cta_text:
                self.cta_text.append(text)
            self._buffer = []
            return

        if tag_lower == "a":
            classes = self._current_attrs.get("class", "").lower()
            if any(k in classes for k in ("btn", "button", "cta", "action")) and text:
                if text not in self.cta_text:
                    self.cta_text.append(text)
            self._buffer = []
            return

        if tag_lower == "p":
            if text:
                self.paragraphs.append(text)
                self.current_section_paragraphs.append(text)
            self._buffer = []
            return

        if tag_lower == "li":
            if text:
                self.lists.append(text)
                self.current_section_paragraphs.append(text)
            self._buffer = []
            return

    def handle_data(self, data: str):
        if self._in_ignore == 0:
            self._buffer.append(data)

    def finalize(self):
        """Closes the final open section if any."""
        if self.current_section_paragraphs:
            self.sections.append({
                "heading": self.current_section_heading,
                "level": self.current_section_level,
                "content": " ".join(self.current_section_paragraphs),
            })
            self.current_section_paragraphs = []


def clean_extracted_content(content_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Cleans and deduplicates extracted content while preserving order."""
    cleaned = dict(content_dict)

    # Clean title and meta
    cleaned["title"] = " ".join(str(content_dict.get("title", "")).split()).strip()
    cleaned["meta_description"] = " ".join(str(content_dict.get("meta_description", "")).split()).strip()

    # Deduplicate headings while preserving structure
    seen_headings = set()
    cleaned_headings = []
    for h in content_dict.get("headings", []):
        text = " ".join(str(h.get("text", "")).split()).strip()
        level = str(h.get("level", "h2")).lower()
        key = (level, text.lower())
        if text and key not in seen_headings:
            seen_headings.add(key)
            cleaned_headings.append({"level": level, "text": text})
    cleaned["headings"] = cleaned_headings

    # Deduplicate paragraphs
    seen_paras = set()
    cleaned_paras = []
    for p in content_dict.get("paragraphs", []):
        text = " ".join(str(p).split()).strip()
        if text and text.lower() not in seen_paras:
            seen_paras.add(text.lower())
            cleaned_paras.append(text)
    cleaned["paragraphs"] = cleaned_paras

    # Deduplicate CTAs
    seen_ctas = set()
    cleaned_ctas = []
    for cta in content_dict.get("cta_text", []):
        text = " ".join(str(cta).split()).strip()
        if text and text.lower() not in seen_ctas:
            seen_ctas.add(text.lower())
            cleaned_ctas.append(text)
    cleaned["cta_text"] = cleaned_ctas

    # Deduplicate image alt texts
    seen_alts = set()
    cleaned_alts = []
    for alt in content_dict.get("image_alt_texts", []):
        text = " ".join(str(alt).split()).strip()
        if text and text.lower() not in seen_alts:
            seen_alts.add(text.lower())
            cleaned_alts.append(text)
    cleaned["image_alt_texts"] = cleaned_alts

    # Deduplicate sections
    seen_sections = set()
    cleaned_sections = []
    for s in content_dict.get("sections", []):
        h = " ".join(str(s.get("heading", "")).split()).strip()
        c = " ".join(str(s.get("content", "")).split()).strip()
        key = (h.lower(), c.lower())
        if c and key not in seen_sections:
            seen_sections.add(key)
            cleaned_sections.append({
                "heading": h or "General Content",
                "level": s.get("level", "h2"),
                "content": c,
            })
    cleaned["sections"] = cleaned_sections

    return cleaned


def structure_website_content(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures consistent, well-formed schema for extracted website content."""
    cleaned = clean_extracted_content(raw_data)
    return {
        "url": cleaned.get("url", ""),
        "title": cleaned.get("title", ""),
        "meta_description": cleaned.get("meta_description", ""),
        "headings": cleaned.get("headings", []),
        "sections": cleaned.get("sections", []),
        "paragraphs": cleaned.get("paragraphs", []),
        "cta_text": cleaned.get("cta_text", []),
        "image_alt_texts": cleaned.get("image_alt_texts", []),
        "lists": cleaned.get("lists", []),
    }


def extract_website_content(html: str, url: str) -> Dict[str, Any]:
    """Extracts meaningful website content from HTML string for the given URL.

    Identifies title, meta description, headings (H1-H3), paragraphs, lists,
    CTAs, image alt texts, and groups content into hierarchical sections.
    Removes scripts, styles, boilerplate, and comments.
    """
    if not html or not isinstance(html, str):
        return structure_website_content({"url": url})

    parser = WebsiteContentExtractor()
    try:
        parser.feed(html)
        parser.finalize()
    except Exception as exc:
        logger.warning("HTML parsing warning on %s: %s", url, str(exc))

    raw_extracted = {
        "url": url,
        "title": parser.title,
        "meta_description": parser.meta_description,
        "headings": parser.headings,
        "sections": parser.sections,
        "paragraphs": parser.paragraphs,
        "cta_text": parser.cta_text,
        "image_alt_texts": parser.image_alt_texts,
        "lists": parser.lists,
    }

    return structure_website_content(raw_extracted)


def discover_internal_links(base_url: str, html: str) -> List[str]:
    """Discovers internal, same-domain links from an HTML document.

    Filters out external domains, sensitive authentication/checkout paths,
    non-HTML binary files, and duplicate links.
    """
    if not html or not base_url:
        return []

    parsed_base = urlparse(base_url)
    base_netloc = parsed_base.netloc.lower()
    if not base_netloc:
        return []

    # Extract all href attributes
    raw_hrefs = re.findall(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']+)["\']', html, re.IGNORECASE)

    non_html_extensions = (
        ".pdf", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg",
        ".gif", ".svg", ".css", ".js", ".mp4", ".mp3", ".wav",
        ".avi", ".mov", ".exe", ".dmg", ".iso", ".xml", ".json",
    )

    discovered: List[str] = []
    seen: Set[str] = set()

    for href in raw_hrefs:
        href_clean = href.strip()
        if not href_clean:
            continue

        # Skip anchor links, mailto, tel, javascript, etc.
        if href_clean.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue

        # Resolve relative URL against base_url
        full_url = urljoin(base_url, href_clean)
        parsed = urlparse(full_url)

        # Must be http or https
        if parsed.scheme.lower() not in ("http", "https"):
            continue

        # Must be strictly the same domain
        link_netloc = parsed.netloc.lower()
        if link_netloc != base_netloc and link_netloc != f"www.{base_netloc}" and f"www.{link_netloc}" != base_netloc:
            continue

        # Check for non-HTML file extensions
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in non_html_extensions):
            continue

        # Check for sensitive path patterns (login, logout, admin, cart, etc.)
        if any(re.search(pat, path_lower) for pat in SENSITIVE_PATH_PATTERNS):
            continue

        # Normalize URL (remove fragment, keep normalized path)
        norm_path = parsed.path or "/"
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            norm_path,
            "",
            parsed.query,
            "",
        ))

        if normalized not in seen:
            seen.add(normalized)
            discovered.append(normalized)

    return discovered


def crawl_website(
    start_url: str,
    max_pages: int = 1,
    max_depth: int = 2,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    check_dns: bool = True,
    check_robots: bool = False,
    session: Optional[requests.Session] = None,
    fetch_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """Crawls a website starting at start_url with bounded page and depth limits.

    Supports Mode A (single-page analysis when max_pages=1) and Mode B (limited
    crawling when max_pages > 1).
    """
    valid, norm_start_url = validate_url(start_url, check_dns=check_dns)
    if not valid:
        return {
            "start_url": start_url,
            "pages_crawled": 0,
            "pages": [],
            "failed_urls": [{"url": start_url, "error": norm_start_url}],
        }

    fetcher = fetch_fn or (
        lambda u: fetch_website(
            u,
            timeout=timeout,
            check_dns=check_dns,
            check_robots=check_robots,
            session=session,
        )
    )

    visited_urls: Set[str] = set()
    queue: List[Tuple[str, int]] = [(norm_start_url, 0)]
    pages: List[Dict[str, Any]] = []
    failed_urls: List[Dict[str, str]] = []

    limit = max(1, max_pages)

    while queue and len(pages) < limit:
        current_url, depth = queue.pop(0)

        if current_url in visited_urls:
            continue
        visited_urls.add(current_url)

        try:
            success, content_or_err, final_url = fetcher(current_url)
        except Exception as exc:
            failed_urls.append({"url": current_url, "error": str(exc)})
            continue

        if not success:
            failed_urls.append({"url": current_url, "error": content_or_err})
            continue

        # Extract structured content for this page
        page_content = extract_website_content(content_or_err, final_url)
        pages.append(page_content)

        # If we can still crawl more pages and depth permits, discover internal links
        if len(pages) < limit and depth < max_depth:
            discovered = discover_internal_links(final_url, content_or_err)
            for link in discovered:
                if link not in visited_urls and not any(item[0] == link for item in queue):
                    queue.append((link, depth + 1))

    return {
        "start_url": norm_start_url,
        "pages_crawled": len(pages),
        "pages": pages,
        "failed_urls": failed_urls,
    }
