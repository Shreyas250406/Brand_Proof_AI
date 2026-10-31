"""Standalone Website Scraping and Content Analysis Module for BrandProof AI.

Provides safe, SSRF-protected website fetching, structured HTML content extraction,
optional bounded multi-page crawling, content normalization, and Gemini AI analysis
for grammar, readability, tone, brand consistency, marketing copy, and SEO content recommendations.
"""

import copy
import ipaddress
import json
import logging
import re
import socket
import urllib.robotparser
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, Comment
import httpx

from app.core.config import settings
from app.core.exceptions import (
    BrandProofAIException,
    AIProviderConfigError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderResponseError,
)
from app.user_improvements import get_gemini_response

logger = logging.getLogger(__name__)

# Security & Scraping Bounds
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_USER_AGENT = "BrandProofAI-WebAudit/1.0 (+https://brandproof.ai/bot)"
MAX_CHUNK_CHARS = 12000

DISALLOWED_FILE_EXTENSIONS = {
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".webm",
    ".exe", ".dmg", ".iso", ".apk", ".bin",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
}

DISALLOWED_PATH_PATTERNS = [
    r"/(?:login|logout|signin|signout|signup|register|auth|oauth)",
    r"/(?:account|profile|settings|billing|subscription|orders)",
    r"/(?:cart|checkout|basket|pay|payment)",
    r"/(?:admin|dashboard|cpanel|portal|api)/",
    r"/(?:wp-admin|wp-login|user/login)",
]

ROBOTS_CACHE: Dict[str, urllib.robotparser.RobotFileParser] = {}


# ==============================================================================
# 1. SSRF Protection & URL Validation
# ==============================================================================

def is_safe_ip(ip_str: str) -> bool:
    """Verifies that an IP address is a publicly routable global address.

    Rejects private, loopback, link-local, reserved, multicast, unspecified,
    and cloud metadata IP addresses.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback:
            return False
        if ip.is_private:
            return False
        if ip.is_link_local:
            return False
        if ip.is_reserved:
            return False
        if ip.is_multicast:
            return False
        if ip.is_unspecified:
            return False
        # Block cloud metadata addresses (AWS, GCP, Azure, DigitalOcean)
        if str(ip) == "169.254.169.254":
            return False
        if str(ip) == "fd00:ec2::254":
            return False
        return True
    except ValueError:
        return False


def validate_url(url: str) -> Tuple[bool, str]:
    """Validates URL format, permitted schemes, and ensures destination is safe from SSRF.

    Returns:
        (is_valid: bool, normalized_url_or_error: str)
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Invalid URL syntax: {str(exc)}"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme '{scheme}'. Only HTTP and HTTPS are permitted."

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False, "URL must contain a valid domain or hostname."

    # Immediate check for localhost / cloud metadata hostname strings
    if hostname in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
        return False, f"Access to restricted hostname '{hostname}' is prohibited."

    # Check for direct numeric IP in hostname
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if not is_safe_ip(str(ip_obj)):
            return False, f"Access to private/restricted IP address '{hostname}' is prohibited."
    except ValueError:
        pass

    # Resolve hostname via DNS and check every resolved IP address
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(hostname, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        if not addr_info:
            return False, f"Hostname '{hostname}' could not be resolved."

        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            if not is_safe_ip(ip_str):
                return False, f"Access to resolved destination '{ip_str}' is prohibited (SSRF protection)."
    except socket.gaierror:
        return False, f"Could not resolve hostname '{hostname}' via DNS."
    except Exception as exc:
        return False, f"Network validation failed: {str(exc)}"

    # Normalize URL: scheme and hostname lowercase, default path '/'
    normalized_path = parsed.path if parsed.path else "/"
    normalized = urlunparse((
        scheme,
        parsed.netloc.lower(),
        normalized_path,
        parsed.params,
        parsed.query,
        "",  # Strip fragment
    ))

    return True, normalized


# ==============================================================================
# 2. Robots.txt Compliance
# ==============================================================================

def can_fetch_url(url: str, user_agent: str = DEFAULT_USER_AGENT) -> bool:
    """Checks robots.txt for the target domain and verifies access is allowed."""
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in ROBOTS_CACHE:
            rp = ROBOTS_CACHE[base]
            return rp.can_fetch(user_agent, url)

        robots_url = f"{base}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)

        # Quick safe fetch for robots.txt
        is_safe, _ = validate_url(robots_url)
        if not is_safe:
            return False

        try:
            with httpx.Client(timeout=4.0, follow_redirects=False) as client:
                res = client.get(robots_url, headers={"User-Agent": user_agent})
                if res.status_code == 200:
                    rp.parse(res.text.splitlines())
                else:
                    # 404 or other: assume allowed per standard robots convention
                    rp.allow_all = True
        except Exception:
            rp.allow_all = True

        ROBOTS_CACHE[base] = rp
        return rp.can_fetch(user_agent, url)
    except Exception:
        # Default to allowed if robots check fails non-critically
        return True


# ==============================================================================
# 3. HTTP Website Fetching
# ==============================================================================

def fetch_website(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    user_agent: str = DEFAULT_USER_AGENT,
) -> Tuple[str, str]:
    """Fetches public HTML content from a URL with SSRF protection on all redirects.

    Returns:
        (html_content: str, final_url: str)

    Raises:
        ValueError: For validation failures or policy violations.
        ConnectionError: For network or server connectivity failures.
        TimeoutError: When requests exceed timeout duration.
    """
    current_url = url
    visited_redirects: Set[str] = set()

    for _ in range(max_redirects + 1):
        is_valid, validated_url = validate_url(current_url)
        if not is_valid:
            raise ValueError(f"URL validation failed: {validated_url}")

        if not can_fetch_url(validated_url, user_agent):
            raise ValueError(f"Access to '{validated_url}' is disallowed by website robots.txt.")

        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                response = client.get(validated_url, headers=headers)

            # Handle Redirects manually to re-verify destination IP against SSRF
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise ConnectionError(f"HTTP {response.status_code} redirect received with no Location header.")
                next_url = urljoin(validated_url, location)
                if next_url in visited_redirects:
                    raise ConnectionError(f"Circular redirect loop detected: {next_url}")
                visited_redirects.add(next_url)
                current_url = next_url
                continue

            if response.status_code != 200:
                raise ConnectionError(f"Website returned HTTP error {response.status_code}.")

            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not any(ct in content_type for ct in ("text/html", "application/xhtml", "text/plain")):
                raise ValueError(f"Unsupported content type '{content_type}'. Only HTML content is analyzed.")

            raw_bytes = response.content
            if len(raw_bytes) > max_bytes:
                raise ValueError(f"Response size ({len(raw_bytes)} bytes) exceeds maximum limit ({max_bytes} bytes).")

            encoding = response.encoding or "utf-8"
            html_text = raw_bytes.decode(encoding, errors="replace")
            return html_text, validated_url

        except httpx.TimeoutException:
            raise TimeoutError(f"Request to '{validated_url}' timed out after {timeout}s.")
        except httpx.RequestError as exc:
            raise ConnectionError(f"Failed to connect to website: {str(exc)}")

    raise ConnectionError(f"Exceeded maximum redirect limit of {max_redirects}.")


# ==============================================================================
# 4. Content Extraction (HTML Parsing)
# ==============================================================================

def extract_website_content(html: str, url: str) -> Dict[str, Any]:
    """Parses raw HTML and extracts title, meta description, headings, sections, CTAs, and alt text."""
    if not html or not html.strip():
        return {
            "url": url,
            "title": "",
            "meta_description": "",
            "headings": [],
            "sections": [],
            "cta_text": [],
            "image_alt_texts": [],
            "paragraphs": [],
            "missing_alt_images_count": 0,
        }

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements and scripts
    for elem in soup.find_all(["script", "style", "noscript", "svg", "iframe", "canvas", "object", "embed", "template"]):
        elem.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("meta", property="og:title"):
        title = str(soup.find("meta", property="og:title").get("content") or "").strip()

    # Meta Description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if not meta_tag:
        meta_tag = soup.find("meta", attrs={"property": "og:description"})
    if meta_tag:
        meta_desc = str(meta_tag.get("content") or "").strip()

    # Headings hierarchy
    headings: List[Dict[str, str]] = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        level = h.name.lower()
        h_text = h.get_text(separator=" ", strip=True)
        if h_text:
            headings.append({"level": level, "text": h_text})

    # Hierarchical Sections (grouped under headings)
    sections: List[Dict[str, str]] = []
    current_heading = title or "Overview"
    current_paragraphs: List[str] = []

    # Iterate block elements to group paragraphs under nearest preceding heading
    for elem in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        tag_name = elem.name.lower()
        text = elem.get_text(separator=" ", strip=True)
        if not text:
            continue

        if tag_name in ("h1", "h2", "h3"):
            if current_paragraphs:
                sections.append({
                    "heading": current_heading,
                    "content": " ".join(current_paragraphs),
                })
                current_paragraphs = []
            current_heading = text
        elif tag_name in ("p", "li"):
            if len(text) > 10:  # filter negligible labels
                current_paragraphs.append(text)

    if current_paragraphs:
        sections.append({
            "heading": current_heading,
            "content": " ".join(current_paragraphs),
        })

    # Paragraphs list
    paragraphs: List[str] = []
    for p in soup.find_all("p"):
        p_text = p.get_text(separator=" ", strip=True)
        if p_text and len(p_text) > 15 and p_text not in paragraphs:
            paragraphs.append(p_text)

    # Call-To-Action (CTA) text
    cta_texts: List[str] = []
    cta_candidates = soup.find_all(["button", "a", "input"])
    for cand in cta_candidates:
        cand_text = ""
        if cand.name == "input" and cand.get("type") in ("button", "submit"):
            cand_text = str(cand.get("value") or "").strip()
        else:
            # Check classes or roles
            classes = " ".join(cand.get("class", [])) if isinstance(cand.get("class"), list) else str(cand.get("class") or "")
            role = str(cand.get("role") or "")
            if cand.name == "button" or any(k in classes.lower() for k in ("btn", "button", "cta")) or role == "button":
                cand_text = cand.get_text(separator=" ", strip=True)

        if cand_text and 2 <= len(cand_text) <= 50 and cand_text not in cta_texts:
            cta_texts.append(cand_text)

    # Image Alt Texts & Missing Alt Audit
    image_alts: List[str] = []
    missing_alt_count = 0
    for img in soup.find_all("img"):
        alt = img.get("alt")
        if alt is not None and str(alt).strip():
            alt_clean = str(alt).strip()
            if alt_clean not in image_alts:
                image_alts.append(alt_clean)
        else:
            missing_alt_count += 1

    return {
        "url": url,
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "sections": sections,
        "cta_text": cta_texts[:15],
        "image_alt_texts": image_alts[:20],
        "paragraphs": paragraphs[:30],
        "missing_alt_images_count": missing_alt_count,
    }


# ==============================================================================
# 5. Internal Link Discovery & Bounded Crawling
# ==============================================================================

def discover_internal_links(url: str, html: str) -> List[str]:
    """Finds unique internal links belonging strictly to the same domain."""
    if not html:
        return []

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    base_parsed = urlparse(url)
    base_domain = base_parsed.netloc.lower()
    discovered: Set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue

        resolved = urljoin(url, href)
        parsed = urlparse(resolved)

        # Must have same scheme & domain
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower() != base_domain:
            continue

        # Reject static file extensions
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in DISALLOWED_FILE_EXTENSIONS):
            continue

        # Reject sensitive / auth paths
        if any(re.search(pat, path, re.I) for pat in DISALLOWED_PATH_PATTERNS):
            continue

        # Strip tracking queries
        query_params = parse_qs(parsed.query)
        cleaned_params = {k: v for k, v in query_params.items() if not k.lower().startswith("utm_") and k.lower() not in ("ref", "fbclid")}
        cleaned_query = urlencode(cleaned_params, doseq=True)

        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path if parsed.path else "/",
            "",
            cleaned_query,
            "",
        ))

        if normalized != url:
            discovered.add(normalized)

    return sorted(list(discovered))


def crawl_website(
    url: str,
    max_pages: int = 1,
    max_depth: int = 2,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    """Crawls up to max_pages internal URLs starting from url, respecting depth and domain boundaries."""
    max_pages = max(1, min(max_pages, 10))  # bounded safe ceiling
    queue: List[Tuple[str, int]] = [(url, 0)]
    visited: Set[str] = set()
    pages_content: List[Dict[str, Any]] = []

    while queue and len(pages_content) < max_pages:
        current_url, depth = queue.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            html, final_url = fetch_website(current_url, timeout=timeout)
            content = extract_website_content(html, final_url)
            pages_content.append(content)

            if depth < max_depth and len(pages_content) < max_pages:
                links = discover_internal_links(final_url, html)
                for link in links:
                    if link not in visited:
                        queue.append((link, depth + 1))
        except Exception as exc:
            logger.warning("Could not crawl URL '%s': %s", current_url, exc)
            continue

    return pages_content


# ==============================================================================
# 6. Content Cleaning & Structuring
# ==============================================================================

def clean_extracted_content(content: Dict[str, Any]) -> Dict[str, Any]:
    """Cleans text, strips excessive whitespace, and removes duplicate sections."""
    cleaned = copy.deepcopy(content)

    def _normalize_text(s: str) -> str:
        s = s.replace("\xa0", " ")
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    cleaned["title"] = _normalize_text(cleaned.get("title", ""))
    cleaned["meta_description"] = _normalize_text(cleaned.get("meta_description", ""))

    seen_sections = set()
    deduped_sections = []
    for sec in cleaned.get("sections", []):
        heading = _normalize_text(sec.get("heading", ""))
        text = _normalize_text(sec.get("content", ""))
        if not text:
            continue
        key = (heading, text[:80])
        if key not in seen_sections:
            seen_sections.add(key)
            deduped_sections.append({"heading": heading, "content": text})
    cleaned["sections"] = deduped_sections

    cleaned["paragraphs"] = [_normalize_text(p) for p in cleaned.get("paragraphs", []) if _normalize_text(p)]
    cleaned["cta_text"] = [_normalize_text(c) for c in cleaned.get("cta_text", []) if _normalize_text(c)]

    return cleaned


def structure_website_content(
    pages_content: Union[Dict[str, Any], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Aggregates and formats one or more scraped pages into a unified audit payload."""
    if isinstance(pages_content, dict):
        pages_list = [clean_extracted_content(pages_content)]
    else:
        pages_list = [clean_extracted_content(p) for p in pages_content]

    if not pages_list:
        return {
            "website_url": "",
            "pages_count": 0,
            "primary_metadata": {},
            "pages": [],
            "combined_text": "",
        }

    primary = pages_list[0]
    all_text_blocks: List[str] = []

    for p in pages_list:
        if p.get("title"):
            all_text_blocks.append(f"PAGE TITLE: {p['title']}")
        if p.get("meta_description"):
            all_text_blocks.append(f"META DESCRIPTION: {p['meta_description']}")
        for sec in p.get("sections", []):
            all_text_blocks.append(f"SECTION [{sec['heading']}]: {sec['content']}")

    combined_text = "\n\n".join(all_text_blocks)

    return {
        "website_url": primary.get("url", ""),
        "pages_count": len(pages_list),
        "primary_metadata": {
            "title": primary.get("title", ""),
            "meta_description": primary.get("meta_description", ""),
        },
        "pages": pages_list,
        "combined_text": combined_text,
    }


# ==============================================================================
# 7. Gemini AI Prompt & Content Analysis
# ==============================================================================

WEBSITE_AUDIT_SYSTEM_PROMPT = (
    "You are an expert website brand auditor, senior content strategist, copy editor, and SEO copy specialist.\n"
    "Your objective is to thoroughly audit publicly accessible website content extracted from web scraping.\n\n"
    "CRITICAL AUDIT RULES:\n"
    "1. High Precision Grammar & Spelling: Identify real grammar, spelling, punctuation, capitalization, and syntax errors.\n"
    "   For each issue specify exact original text, proposed correction, category, severity, source URL, and section.\n"
    "2. Readability & Tone: Assess whether tone is consistent, audience-appropriate, clear, and professional.\n"
    "3. Brand Consistency: Evaluate alignment with any provided brand guidelines or terminology. Do not fabricate brand rules.\n"
    "4. Marketing Copy Quality: Review clarity of value proposition, customer benefits, and calls to action (CTAs).\n"
    "5. Content SEO: Analyze title quality, meta description length/impact, heading hierarchy, keyword relevance, and missing image alt text.\n"
    "   DO NOT fabricate rankings, backlinks, traffic, or indexing stats.\n"
    "6. Output: Produce strictly valid JSON matching the exact schema."
)


def _build_audit_user_prompt(
    structured_content: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> str:
    ctx = context or {}
    brand_name = ctx.get("brand_name", "")
    brand_guidelines = ctx.get("brand_guidelines", [])
    preferred_terminology = ctx.get("preferred_terminology", [])
    preserved_entities = ctx.get("preserved_entities", [])
    target_audience = ctx.get("target_audience", "General / Business Audience")
    content_type = ctx.get("content_type", "Public Corporate Website")
    language = ctx.get("language", "English")
    custom_instructions = ctx.get("custom_instructions", [])

    guidelines_str = "\n".join(f"- {g}" for g in brand_guidelines) if brand_guidelines else "None specified"
    terms_str = ", ".join(preferred_terminology) if preferred_terminology else "None specified"
    entities_str = ", ".join(preserved_entities) if preserved_entities else "None specified"
    instructions_str = "\n".join(f"- {i}" for i in custom_instructions) if custom_instructions else "None specified"

    pages_summary = []
    for idx, page in enumerate(structured_content.get("pages", [])):
        headings_str = ", ".join([f"[{h['level']}] {h['text']}" for h in page.get("headings", [])[:8]])
        ctas_str = ", ".join(page.get("cta_text", [])) or "None detected"
        alts_str = ", ".join(page.get("image_alt_texts", [])) or "None detected"
        sections_str = "\n".join([f"  * {s['heading']}: {s['content'][:300]}" for s in page.get("sections", [])[:6]])

        pages_summary.append(
            f"--- PAGE {idx + 1}: {page.get('url')} ---\n"
            f"Title: {page.get('title')}\n"
            f"Meta Description: {page.get('meta_description')}\n"
            f"Headings: {headings_str}\n"
            f"CTAs: {ctas_str}\n"
            f"Image Alt Texts: {alts_str}\n"
            f"Missing Alt Images Count: {page.get('missing_alt_images_count', 0)}\n"
            f"Key Sections Content:\n{sections_str}\n"
        )

    all_pages_text = "\n".join(pages_summary)

    parts = [
        "--- BRAND & AUDIT CONTEXT ---",
        f"Brand Name: {brand_name or 'Not specified'}",
        f"Target Audience: {target_audience}",
        f"Content Type: {content_type}",
        f"Language: {language}",
        f"Brand Guidelines:\n{guidelines_str}",
        f"Preferred Terminology: {terms_str}",
        f"Preserved Entities (MUST PRESERVE VERBATIM): {entities_str}",
        f"Custom Instructions:\n{instructions_str}",
        "",
        "--- EXTRACTED WEBSITE DATA ---",
        f"Website Base URL: {structured_content.get('website_url')}",
        f"Pages Crawled: {structured_content.get('pages_count')}",
        "",
        all_pages_text,
        "",
        "--- REQUIRED JSON SCHEMA OUTPUT ---",
        "Produce a valid JSON object matching this exact structure:",
        "{",
        '  "status": "success",',
        f'  "website_url": "{structured_content.get("website_url")}",',
        '  "website_metadata": {',
        f'    "title": "{structured_content.get("primary_metadata", {}).get("title", "")}",',
        f'    "meta_description": "{structured_content.get("primary_metadata", {}).get("meta_description", "")}"',
        '  },',
        '  "content_summary": "Comprehensive overview of the website content and purpose.",',
        '  "findings": [',
        '    {',
        '      "page_url": "URL where finding was detected",',
        '      "section": "Section heading",',
        '      "original_text": "Exact problematic snippet",',
        '      "suggested_text": "Improved replacement text",',
        '      "category": "Grammar | Spelling | Punctuation | Clarity | Brand | Marketing | SEO",',
        '      "severity": "low | medium | high",',
        '      "explanation": "Clear explanation of the finding and recommended correction."',
        '    }',
        '  ],',
        '  "tone_analysis": {',
        '    "identified_tone": "Identified voice (e.g. Professional, Casual, Academic)",',
        '    "consistency": "Consistent | Mostly consistent | Inconsistent",',
        '    "recommendations": ["Recommendation 1"]',
        '  },',
        '  "readability_analysis": {',
        '    "observations": ["Observation 1"],',
        '    "recommendations": ["Recommendation 1"]',
        '  },',
        '  "brand_analysis": {',
        '    "issues": ["Issue 1"],',
        '    "recommendations": ["Recommendation 1"]',
        '  },',
        '  "seo_content_analysis": {',
        '    "title_analysis": "Critique of title length, keywords, and relevance",',
        '    "meta_description_analysis": "Critique of meta description length, appeal, and clarity",',
        '    "heading_analysis": ["Observation on H1/H2 structure"],',
        '    "alt_text_issues": ["Observation on image accessibility and alt text"],',
        '    "recommendations": ["SEO copy recommendation 1"]',
        '  },',
        '  "overall_recommendations": ["Top priority action 1", "Top priority action 2"],',
        '  "summary": {',
        '    "total_issues": 0,',
        '    "grammar_issues": 0,',
        '    "spelling_issues": 0,',
        '    "brand_issues": 0,',
        '    "readability_issues": 0,',
        '    "seo_content_issues": 0',
        '  }',
        "}",
    ]

    return "\n".join(parts)


def _clean_markdown_json(text: str) -> str:
    """Strips markdown code fences from JSON output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def analyze_website_content(
    structured_content: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sends structured website content to Gemini and parses the structured analysis."""
    if not structured_content or not structured_content.get("pages"):
        return {
            "status": "error",
            "message": "No structured website content available for analysis.",
            "findings": [],
        }

    prompt = _build_audit_user_prompt(structured_content, context)

    try:
        raw_response = get_gemini_response(prompt=prompt, system_prompt=WEBSITE_AUDIT_SYSTEM_PROMPT)
    except BrandProofAIException as exc:
        logger.error("AI provider error during website analysis: %s", exc)
        return {
            "status": "error",
            "message": f"AI provider error: {str(exc)}",
            "findings": [],
        }
    except Exception as exc:
        logger.error("Unexpected error during website analysis: %s", exc)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(exc)}",
            "findings": [],
        }

    if isinstance(raw_response, dict):
        parsed = raw_response
    elif isinstance(raw_response, str):
        cleaned = _clean_markdown_json(raw_response)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON from Gemini website analysis: %s", raw_response[:200])
            return {
                "status": "error",
                "message": f"Malformed JSON from Gemini response: {str(exc)}",
                "findings": [],
            }
    else:
        return {
            "status": "error",
            "message": "Unsupported Gemini response format.",
            "findings": [],
        }

    # Ensure required top-level keys exist and counts match findings
    findings = parsed.get("findings", [])
    if not isinstance(findings, list):
        findings = []

    grammar_count = sum(1 for f in findings if str(f.get("category", "")).lower() == "grammar")
    spelling_count = sum(1 for f in findings if str(f.get("category", "")).lower() == "spelling")
    brand_count = sum(1 for f in findings if str(f.get("category", "")).lower() == "brand")
    readability_count = sum(1 for f in findings if str(f.get("category", "")).lower() in ("readability", "clarity"))
    seo_count = sum(1 for f in findings if str(f.get("category", "")).lower() == "seo")

    summary = parsed.get("summary", {})
    if not isinstance(summary, dict) or not summary.get("total_issues"):
        summary = {
            "total_issues": len(findings),
            "grammar_issues": grammar_count,
            "spelling_issues": spelling_count,
            "brand_issues": brand_count,
            "readability_issues": readability_count,
            "seo_content_issues": seo_count,
        }

    parsed["status"] = "success"
    parsed["findings"] = findings
    parsed["summary"] = summary
    if not parsed.get("website_url"):
        parsed["website_url"] = structured_content.get("website_url", "")
    if not parsed.get("website_metadata"):
        parsed["website_metadata"] = structured_content.get("primary_metadata", {})

    return parsed


# ==============================================================================
# 8. Combining Multiple Chunk Results
# ==============================================================================

def combine_analysis_results(
    results: List[Dict[str, Any]],
    website_url: str = "",
) -> Dict[str, Any]:
    """Merges multiple analysis results from chunked content into a single cohesive response."""
    successful = [r for r in results if r.get("status") == "success"]
    if not successful:
        return {
            "status": "error",
            "website_url": website_url,
            "message": "All chunk analyses failed.",
            "findings": [],
        }

    merged_findings: List[Dict[str, Any]] = []
    seen_finding_keys = set()
    recommendations: List[str] = []
    readability_obs: List[str] = []
    brand_issues: List[str] = []
    seo_recs: List[str] = []

    base = copy.deepcopy(successful[0])

    for res in successful:
        for f in res.get("findings", []):
            key = (str(f.get("page_url", "")), str(f.get("original_text", "")).strip().lower())
            if key not in seen_finding_keys:
                seen_finding_keys.add(key)
                merged_findings.append(f)

        for rec in res.get("overall_recommendations", []):
            if rec and rec not in recommendations:
                recommendations.append(rec)

        read_ana = res.get("readability_analysis", {})
        for obs in read_ana.get("observations", []):
            if obs and obs not in readability_obs:
                readability_obs.append(obs)

        br_ana = res.get("brand_analysis", {})
        for iss in br_ana.get("issues", []):
            if iss and iss not in brand_issues:
                brand_issues.append(iss)

        seo_ana = res.get("seo_content_analysis", {})
        for srec in seo_ana.get("recommendations", []):
            if srec and srec not in seo_recs:
                seo_recs.append(srec)

    base["findings"] = merged_findings
    base["overall_recommendations"] = recommendations[:10]
    if "readability_analysis" in base:
        base["readability_analysis"]["observations"] = readability_obs[:8]
    if "brand_analysis" in base:
        base["brand_analysis"]["issues"] = brand_issues[:8]
    if "seo_content_analysis" in base:
        base["seo_content_analysis"]["recommendations"] = seo_recs[:8]

    # Recompute summary totals
    base["summary"] = {
        "total_issues": len(merged_findings),
        "grammar_issues": sum(1 for f in merged_findings if str(f.get("category", "")).lower() == "grammar"),
        "spelling_issues": sum(1 for f in merged_findings if str(f.get("category", "")).lower() == "spelling"),
        "brand_issues": sum(1 for f in merged_findings if str(f.get("category", "")).lower() == "brand"),
        "readability_issues": sum(1 for f in merged_findings if str(f.get("category", "")).lower() in ("readability", "clarity")),
        "seo_content_issues": sum(1 for f in merged_findings if str(f.get("category", "")).lower() == "seo"),
    }

    return base


# ==============================================================================
# 9. Master Orchestration Entrypoint
# ==============================================================================

def analyze_website(
    url: str,
    context: Optional[Dict[str, Any]] = None,
    max_pages: int = 1,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Primary entrypoint: validates URL, scrapes website, and runs complete Gemini analysis."""
    is_valid, validated_url = validate_url(url)
    if not is_valid:
        return {
            "status": "error",
            "website_url": url,
            "message": f"URL validation failed: {validated_url}",
            "findings": [],
        }

    try:
        pages_content = crawl_website(validated_url, max_pages=max_pages, timeout=timeout)
    except Exception as exc:
        logger.error("Failed to crawl website '%s': %s", validated_url, exc)
        return {
            "status": "error",
            "website_url": validated_url,
            "message": f"Website fetch/crawl failed: {str(exc)}",
            "findings": [],
        }

    if not pages_content:
        return {
            "status": "error",
            "website_url": validated_url,
            "message": "No accessible pages could be extracted from the target website.",
            "findings": [],
        }

    structured = structure_website_content(pages_content)

    # Content Chunking: if text is within bounds, execute in one call
    if len(structured["combined_text"]) <= MAX_CHUNK_CHARS:
        return analyze_website_content(structured, context)

    # Chunking by page for large sites
    chunk_results = []
    for page in structured.get("pages", []):
        single_structured = structure_website_content(page)
        chunk_res = analyze_website_content(single_structured, context)
        chunk_results.append(chunk_res)

    return combine_analysis_results(chunk_results, website_url=validated_url)
