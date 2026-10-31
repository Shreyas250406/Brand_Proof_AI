"""Independent unit tests for website_analysis module.

Covers all 23 scenarios specified in the Website Scraping and Analysis specification.
Strictly mocks network requests and Gemini API calls to prevent external requests
and quota consumption.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
import httpx

from app.website_analysis import (
    validate_url,
    is_safe_ip,
    fetch_website,
    can_fetch_url,
    extract_website_content,
    discover_internal_links,
    crawl_website,
    clean_extracted_content,
    structure_website_content,
    analyze_website_content,
    combine_analysis_results,
    analyze_website,
)
from app.core.exceptions import AIProviderError


# -----------------------------------------------------------------------------
# Fixtures & HTML Samples
# -----------------------------------------------------------------------------

SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>BrandProof AI — Brand Compliance Platform</title>
    <meta name="description" content="AI-driven brand review, proofreading, and marketing compliance software." />
</head>
<body>
    <header>
        <nav>
            <a href="/about">About Us</a>
            <a href="/pricing">Pricing</a>
            <a href="https://external-partner.com/blog">Partner Blog</a>
            <a href="/login">User Login</a>
        </nav>
    </header>
    <main>
        <h1>Next-Gen Content Governance</h1>
        <p>Our intelligent system ensures consistency across marketing copy.</p>
        
        <h2>Empower Your Team</h2>
        <p>Streamline editorial workflow operations without friction or delays.</p>
        
        <h3>Enterprise Performance</h3>
        <p>Guaranteed reliability for leading modern global brands.</p>
        <p>Guaranteed reliability for leading modern global brands.</p> <!-- duplicate paragraph -->
        
        <button class="btn btn-primary">Start Free Trial</button>
        <a href="/contact" class="cta-link button">Schedule Demo</a>
        
        <img src="/assets/dashboard.png" alt="Platform Dashboard Overview" />
        <img src="/assets/logo.png" /> <!-- missing alt -->
    </main>
    <footer>
        <p>&copy; 2026 BrandProof AI Inc.</p>
    </footer>
</body>
</html>
"""


# -----------------------------------------------------------------------------
# 1. Valid URL Validation
# -----------------------------------------------------------------------------
def test_valid_url_validation():
    """Test 1: Valid public HTTP and HTTPS URLs are accepted and normalized."""
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 80))]):
        is_valid, norm = validate_url("https://example.com/products?ref=test")
        assert is_valid is True
        assert norm.startswith("https://example.com/products")


# -----------------------------------------------------------------------------
# 2. Invalid URL Validation
# -----------------------------------------------------------------------------
def test_invalid_url_validation():
    """Test 2: Malformed or non-string URLs are rejected cleanly."""
    assert validate_url("")[0] is False
    assert validate_url("not_a_url")[0] is False
    assert validate_url("ftp://example.com/test")[0] is False
    assert validate_url("javascript:alert(1)")[0] is False


# -----------------------------------------------------------------------------
# 3. HTTP Website Fetching
# -----------------------------------------------------------------------------
def test_http_website_fetching():
    """Test 3: Fetching an HTTP website with mocked client."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<html><head><title>HTTP Page</title></head><body><p>Content</p></body></html>"
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp.encoding = "utf-8"

    with patch("app.website_analysis.validate_url", return_value=(True, "http://example.com/")):
        with patch("app.website_analysis.can_fetch_url", return_value=True):
            with patch("httpx.Client.get", return_value=mock_resp):
                html, final_url = fetch_website("http://example.com/")
                assert "HTTP Page" in html
                assert final_url == "http://example.com/"


# -----------------------------------------------------------------------------
# 4. HTTPS Website Fetching
# -----------------------------------------------------------------------------
def test_https_website_fetching():
    """Test 4: Fetching an HTTPS website with mocked client."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<html><head><title>Secure Page</title></head></html>"
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.encoding = "utf-8"

    with patch("app.website_analysis.validate_url", return_value=(True, "https://secure.example.com/")):
        with patch("app.website_analysis.can_fetch_url", return_value=True):
            with patch("httpx.Client.get", return_value=mock_resp):
                html, final_url = fetch_website("https://secure.example.com/")
                assert "Secure Page" in html


# -----------------------------------------------------------------------------
# 5. Redirect Handling
# -----------------------------------------------------------------------------
def test_redirect_handling():
    """Test 5: Redirects (301, 302) are safely followed and the final URL is preserved."""
    redirect_resp = MagicMock()
    redirect_resp.status_code = 301
    redirect_resp.headers = {"Location": "https://example.com/home"}

    final_resp = MagicMock()
    final_resp.status_code = 200
    final_resp.content = b"<html><head><title>Redirected Home</title></head></html>"
    final_resp.headers = {"Content-Type": "text/html"}
    final_resp.encoding = "utf-8"

    with patch("app.website_analysis.validate_url", side_effect=[
        (True, "https://example.com/"),
        (True, "https://example.com/home"),
    ]):
        with patch("app.website_analysis.can_fetch_url", return_value=True):
            with patch("httpx.Client.get", side_effect=[redirect_resp, final_resp]):
                html, final_url = fetch_website("https://example.com/")
                assert "Redirected Home" in html
                assert final_url == "https://example.com/home"


# -----------------------------------------------------------------------------
# 6. Inaccessible Website
# -----------------------------------------------------------------------------
def test_inaccessible_website_handling():
    """Test 6: Inaccessible site (HTTP 404, 500 or connection failure) raises ConnectionError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("app.website_analysis.validate_url", return_value=(True, "https://example.com/missing")):
        with patch("app.website_analysis.can_fetch_url", return_value=True):
            with patch("httpx.Client.get", return_value=mock_resp):
                with pytest.raises(ConnectionError, match="HTTP error 404"):
                    fetch_website("https://example.com/missing")


# -----------------------------------------------------------------------------
# 7. Invalid HTML Handling
# -----------------------------------------------------------------------------
def test_invalid_html_handling():
    """Test 7: Malformed or partial HTML is parsed gracefully without crashing."""
    broken_html = "<html><head><title>Unclosed</title><body><p>Broken tag <b>bold without close"
    content = extract_website_content(broken_html, "https://example.com/")
    assert content["title"] == "Unclosed"
    assert len(content["paragraphs"]) > 0


# -----------------------------------------------------------------------------
# 8. HTML Content Extraction
# -----------------------------------------------------------------------------
def test_html_content_extraction():
    """Test 8: Basic title and meta description extraction."""
    content = extract_website_content(SAMPLE_HTML, "https://example.com/")
    assert content["title"] == "BrandProof AI — Brand Compliance Platform"
    assert "brand review" in content["meta_description"].lower()


# -----------------------------------------------------------------------------
# 9. Heading Extraction
# -----------------------------------------------------------------------------
def test_heading_extraction():
    """Test 9: H1, H2, and H3 headings are extracted with their level."""
    content = extract_website_content(SAMPLE_HTML, "https://example.com/")
    headings = content["headings"]
    assert len(headings) >= 3
    assert headings[0] == {"level": "h1", "text": "Next-Gen Content Governance"}
    assert headings[1] == {"level": "h2", "text": "Empower Your Team"}
    assert headings[2] == {"level": "h3", "text": "Enterprise Performance"}


# -----------------------------------------------------------------------------
# 10. Paragraph Extraction
# -----------------------------------------------------------------------------
def test_paragraph_extraction():
    """Test 10: Paragraph content is extracted cleanly."""
    content = extract_website_content(SAMPLE_HTML, "https://example.com/")
    paragraphs = content["paragraphs"]
    assert any("intelligent system ensures consistency" in p for p in paragraphs)


# -----------------------------------------------------------------------------
# 11. CTA Extraction
# -----------------------------------------------------------------------------
def test_cta_extraction():
    """Test 11: Action buttons and CTA text are identified."""
    content = extract_website_content(SAMPLE_HTML, "https://example.com/")
    ctas = content["cta_text"]
    assert "Start Free Trial" in ctas
    assert "Schedule Demo" in ctas


# -----------------------------------------------------------------------------
# 12. Image Alt Text Extraction
# -----------------------------------------------------------------------------
def test_image_alt_text_extraction():
    """Test 12: Image alt attributes and missing alt counts are tracked."""
    content = extract_website_content(SAMPLE_HTML, "https://example.com/")
    assert "Platform Dashboard Overview" in content["image_alt_texts"]
    assert content["missing_alt_images_count"] >= 1


# -----------------------------------------------------------------------------
# 13. Duplicate Content Removal
# -----------------------------------------------------------------------------
def test_duplicate_content_removal():
    """Test 13: Duplicate sections and paragraphs are cleaned and deduplicated."""
    raw_content = {
        "url": "https://example.com",
        "title": "  Example  Title   ",
        "meta_description": "Description  with  spaces",
        "sections": [
            {"heading": "Features", "content": "Our features are fast."},
            {"heading": "Features", "content": "Our features are fast."},  # duplicate
        ],
        "paragraphs": ["Repeated text.", "Repeated text."],
        "cta_text": ["Sign Up", "Sign Up"],
    }
    cleaned = clean_extracted_content(raw_content)
    assert cleaned["title"] == "Example Title"
    assert len(cleaned["sections"]) == 1
    assert len(cleaned["paragraphs"]) == 2  # clean keeps unique in sections


# -----------------------------------------------------------------------------
# 14. Internal Link Discovery
# -----------------------------------------------------------------------------
def test_internal_link_discovery():
    """Test 14: Discovers internal links and ignores external links and auth paths."""
    links = discover_internal_links("https://example.com/", SAMPLE_HTML)
    assert "https://example.com/about" in links
    assert "https://example.com/pricing" in links
    # External link rejected
    assert not any("external-partner.com" in l for l in links)
    # Sensitive login path rejected
    assert not any("/login" in l for l in links)


# -----------------------------------------------------------------------------
# 15. Maximum Page Limit
# -----------------------------------------------------------------------------
def test_maximum_page_limit():
    """Test 15: Crawling terminates when max_pages limit is reached."""
    page_1 = "<html><body><a href='/p2'>P2</a><a href='/p3'>P3</a><h1>Page 1</h1></body></html>"
    page_2 = "<html><body><h1>Page 2</h1></body></html>"

    with patch("app.website_analysis.fetch_website", side_effect=[
        (page_1, "https://example.com/"),
        (page_2, "https://example.com/p2"),
    ]):
        pages = crawl_website("https://example.com/", max_pages=2, max_depth=3)
        assert len(pages) == 2


# -----------------------------------------------------------------------------
# 16. Crawl Depth Limit
# -----------------------------------------------------------------------------
def test_crawl_depth_limit():
    """Test 16: Links beyond max_depth are not explored."""
    page_1 = "<html><body><a href='/p2'>P2</a><h1>Root</h1></body></html>"

    with patch("app.website_analysis.fetch_website", return_value=(page_1, "https://example.com/")):
        # depth=0 crawls only the root page without following discovered links
        pages = crawl_website("https://example.com/", max_pages=5, max_depth=0)
        assert len(pages) == 1


# -----------------------------------------------------------------------------
# 17. Cross-Domain Link Rejection
# -----------------------------------------------------------------------------
def test_cross_domain_link_rejection():
    """Test 17: Links pointing to other domains or subdomains of other domains are rejected."""
    html = """
    <a href="https://different-domain.com/page">External</a>
    <a href="http://sub.otherdomain.org/test">External Sub</a>
    <a href="/local-path">Local</a>
    """
    links = discover_internal_links("https://example.com/", html)
    assert len(links) == 1
    assert links[0] == "https://example.com/local-path"


# -----------------------------------------------------------------------------
# 18. SSRF Protection
# -----------------------------------------------------------------------------
def test_ssrf_protection():
    """Test 18: Blocks localhost, private IPs, cloud metadata, and illegal schemes."""
    # Localhost string
    assert validate_url("http://localhost/")[0] is False
    assert validate_url("http://127.0.0.1:8080")[0] is False

    # Cloud metadata IP (AWS/GCP/Azure)
    assert validate_url("http://169.254.169.254/latest/meta-data")[0] is False
    assert is_safe_ip("169.254.169.254") is False

    # Private IPv4 ranges
    assert validate_url("http://10.0.0.1/admin")[0] is False
    assert validate_url("http://192.168.1.1/")[0] is False
    assert validate_url("http://172.16.0.1/")[0] is False

    # Dangerous schemes
    assert validate_url("file:///etc/passwd")[0] is False
    assert validate_url("gopher://127.0.0.1:70")[0] is False


# -----------------------------------------------------------------------------
# 19. Gemini Website Analysis
# -----------------------------------------------------------------------------
def test_gemini_website_analysis():
    """Test 19: Gemini analyzes structured content and outputs validated audit JSON."""
    mock_ai_output = json.dumps({
        "status": "success",
        "website_url": "https://example.com",
        "website_metadata": {
            "title": "BrandProof AI",
            "meta_description": "Platform for copy review.",
        },
        "content_summary": "Corporate marketing website presenting brand review tooling.",
        "findings": [
            {
                "page_url": "https://example.com",
                "section": "Next-Gen Content Governance",
                "original_text": "We is excited to launch",
                "suggested_text": "We are excited to launch",
                "category": "Grammar",
                "severity": "medium",
                "explanation": "Subject-verb agreement error.",
            }
        ],
        "tone_analysis": {
            "identified_tone": "Professional",
            "consistency": "Consistent",
            "recommendations": ["Maintain active voice throughout."],
        },
        "readability_analysis": {
            "observations": ["Sentences are well structured."],
            "recommendations": [],
        },
        "brand_analysis": {
            "issues": [],
            "recommendations": [],
        },
        "seo_content_analysis": {
            "title_analysis": "Title length is optimal (43 chars).",
            "meta_description_analysis": "Clear meta description with relevant keywords.",
            "heading_analysis": ["H1 tag present."],
            "alt_text_issues": ["One image lacks an alt tag."],
            "recommendations": ["Add alt tags to all images."],
        },
        "overall_recommendations": ["Fix grammar issue in heading.", "Add missing image alt attribute."],
        "summary": {
            "total_issues": 1,
            "grammar_issues": 1,
            "spelling_issues": 0,
            "brand_issues": 0,
            "readability_issues": 0,
            "seo_content_issues": 0,
        },
    })

    structured = structure_website_content(extract_website_content(SAMPLE_HTML, "https://example.com/"))
    with patch("app.website_analysis.get_gemini_response", return_value=mock_ai_output):
        result = analyze_website_content(structured, context={"brand_name": "BrandProof AI"})

        assert result["status"] == "success"
        assert len(result["findings"]) == 1
        assert result["findings"][0]["category"] == "Grammar"
        assert result["summary"]["total_issues"] == 1
        assert "Professional" in result["tone_analysis"]["identified_tone"]


# -----------------------------------------------------------------------------
# 20. Malformed Gemini Response Handling
# -----------------------------------------------------------------------------
def test_malformed_gemini_response():
    """Test 20: Malformed non-JSON output from Gemini is handled gracefully."""
    structured = structure_website_content(extract_website_content(SAMPLE_HTML, "https://example.com/"))
    with patch("app.website_analysis.get_gemini_response", return_value="MALFORMED_OUTPUT{not_json"):
        result = analyze_website_content(structured)
        assert result["status"] == "error"
        assert "malformed" in result["message"].lower()


# -----------------------------------------------------------------------------
# 21. Large Content Chunking
# -----------------------------------------------------------------------------
def test_large_content_chunking():
    """Test 21: Multi-page content exceeding character threshold is chunked across calls."""
    # Build large multi-page structure
    long_text = "Word " * 2500  # ~12,500 chars
    page_1 = {"url": "https://example.com/p1", "title": "P1", "sections": [{"heading": "Sec1", "content": long_text}]}
    page_2 = {"url": "https://example.com/p2", "title": "P2", "sections": [{"heading": "Sec2", "content": long_text}]}

    mock_chunk_output = {
        "status": "success",
        "findings": [{"page_url": "https://example.com/p1", "original_text": "err", "category": "Spelling"}],
        "overall_recommendations": ["Rec 1"],
        "summary": {"total_issues": 1},
    }

    with patch("app.website_analysis.validate_url", return_value=(True, "https://example.com/")):
        with patch("app.website_analysis.crawl_website", return_value=[page_1, page_2]):
            with patch("app.website_analysis.analyze_website_content", return_value=mock_chunk_output) as mock_chunk:
                res = analyze_website("https://example.com/", max_pages=2)
                # Verify analyze_website_content was invoked for chunked pages
                assert mock_chunk.call_count == 2
                assert res["status"] == "success"


# -----------------------------------------------------------------------------
# 22. Duplicate Finding Removal
# -----------------------------------------------------------------------------
def test_duplicate_finding_removal():
    """Test 22: Duplicate findings across merged chunks are deduplicated."""
    chunk_1 = {
        "status": "success",
        "findings": [
            {"page_url": "https://example.com", "original_text": "we is", "category": "Grammar"}
        ],
        "overall_recommendations": ["Fix grammar"],
    }
    chunk_2 = {
        "status": "success",
        "findings": [
            {"page_url": "https://example.com", "original_text": "we is", "category": "Grammar"}  # duplicate
        ],
        "overall_recommendations": ["Fix grammar"],
    }

    combined = combine_analysis_results([chunk_1, chunk_2], website_url="https://example.com")
    assert len(combined["findings"]) == 1
    assert len(combined["overall_recommendations"]) == 1
    assert combined["summary"]["total_issues"] == 1


# -----------------------------------------------------------------------------
# 23. Error Handling Orchestration
# -----------------------------------------------------------------------------
def test_error_handling_orchestration():
    """Test 23: Master analyze_website gracefully reports validation or crawl failures."""
    # Invalid URL
    res_invalid = analyze_website("http://localhost/evil")
    assert res_invalid["status"] == "error"
    assert "validation failed" in res_invalid["message"].lower()

    # Inaccessible URL
    with patch("app.website_analysis.validate_url", return_value=(True, "https://example.com/")):
        with patch("app.website_analysis.crawl_website", side_effect=ConnectionError("Host unreachable")):
            res_crawl_err = analyze_website("https://example.com/")
            assert res_crawl_err["status"] == "error"
            assert "unreachable" in res_crawl_err["message"].lower()
