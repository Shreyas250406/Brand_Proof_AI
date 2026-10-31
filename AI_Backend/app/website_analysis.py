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

logger = logging.getLogger(__name__)

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
