"""Standalone Website Scraping and Analysis Module for BrandProof AI.

Extracts meaningful website content (single-page or limited crawl) and uses
the existing Gemini integration to analyze grammar, tone, brand consistency,
readability, marketing quality, and SEO-related factors.
"""

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

        return True, html_text, current_url

    return False, f"Exceeded maximum redirects limit of {max_redirects}.", current_url
