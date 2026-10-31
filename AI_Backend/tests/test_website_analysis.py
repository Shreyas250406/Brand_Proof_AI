"""Comprehensive Unit Tests for Website Scraping and Analysis Module.

Tests cover all 23 required scenarios:
1. Valid URL validation.
2. Invalid URL validation.
3. HTTP website fetching.
4. HTTPS website fetching.
5. Redirect handling.
6. Inaccessible website.
7. Invalid HTML.
8. HTML content extraction.
9. Heading extraction.
10. Paragraph extraction.
11. CTA extraction.
12. Image alt text extraction.
13. Duplicate content removal.
14. Internal link discovery.
15. Maximum page limit.
16. Crawl depth limit.
17. Cross-domain link rejection.
18. SSRF protection.
19. Gemini analysis.
20. Malformed Gemini response.
21. Large content chunking.
22. Duplicate finding removal.
23. Error handling.

All tests use mocked network/HTTP responses and mocked Gemini calls.
Zero external network calls or Gemini API quota consumed.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure AI_Backend is in Python sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.website_analysis import (
    validate_url,
    fetch_website,
    extract_website_content,
    clean_extracted_content,
    discover_internal_links,
    crawl_website,
    chunk_content_sections,
    combine_analysis_results,
    analyze_website_content,
    analyze_website,
)


class TestWebsiteAnalysis(unittest.TestCase):
    """Test suite covering the 23 specification requirements for website_analysis."""

    def setUp(self):
        self.sample_html = """<!DOCTYPE html>
<html>
<head>
    <title>BrandProof AI Platform</title>
    <meta name="description" content="AI-powered brand verification and copy proofing.">
    <script>console.log("analytics tracking");</script>
    <style>.header { color: blue; }</style>
</head>
<body>
    <h1>Welcome to BrandProof AI</h1>
    <p>Our platform helps enterprise teams ensure brand compliance across every channel.</p>
    <h2>Core Capabilities</h2>
    <p>Automated tone checking, vocabulary protection, and instant proofreading.</p>
    <h3>Detailed Specs</h3>
    <p>Real-time analysis with sub-second latency.</p>
    <button>Start Free Trial</button>
    <a class="btn btn-primary" href="/contact">Schedule Demo</a>
    <img src="/dashboard.png" alt="BrandProof Analytics Dashboard" />
    <img src="/banner.jpg" />
</body>
</html>"""

    # -------------------------------------------------------------------------
    # 1. Valid URL validation
    # -------------------------------------------------------------------------
    def test_01_valid_url_validation(self):
        """Test validation of well-formed HTTP and HTTPS URLs."""
        valid, norm = validate_url("https://example.com/products", check_dns=False)
        self.assertTrue(valid)
        self.assertEqual(norm, "https://example.com/products")

        valid_http, norm_http = validate_url("http://sub.example.org:8080/path?q=1", check_dns=False)
        self.assertTrue(valid_http)
        self.assertIn("http://sub.example.org:8080/path", norm_http)

    # -------------------------------------------------------------------------
    # 2. Invalid URL validation
    # -------------------------------------------------------------------------
    def test_02_invalid_url_validation(self):
        """Test rejection of invalid schemes, missing hostnames, or empty strings."""
        for invalid_url in [
            "ftp://files.example.com/doc",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "data:text/html,<h1>bad</h1>",
            "gopher://example.com",
            "",
            None,
            "http://",
        ]:
            valid, err = validate_url(invalid_url, check_dns=False)
            self.assertFalse(valid, f"Expected invalid for {invalid_url}")

    # -------------------------------------------------------------------------
    # 3. HTTP website fetching
    # -------------------------------------------------------------------------
    def test_03_http_website_fetching(self):
        """Test fetching content from a valid HTTP website."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.iter_content.return_value = [b"<html><body><h1>HTTP Page</h1></body></html>"]
        mock_resp.encoding = "utf-8"
        mock_session.get.return_value = mock_resp

        success, html, url = fetch_website(
            "http://example.com/page",
            check_dns=False,
            session=mock_session,
        )
        self.assertTrue(success)
        self.assertIn("HTTP Page", html)
        self.assertEqual(url, "http://example.com/page")

    # -------------------------------------------------------------------------
    # 4. HTTPS website fetching
    # -------------------------------------------------------------------------
    def test_04_https_website_fetching(self):
        """Test fetching content from a secure HTTPS website."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.iter_content.return_value = [b"<html><body><h1>HTTPS Page</h1></body></html>"]
        mock_resp.encoding = "utf-8"
        mock_session.get.return_value = mock_resp

        success, html, url = fetch_website(
            "https://secure.example.com",
            check_dns=False,
            session=mock_session,
        )
        self.assertTrue(success)
        self.assertIn("HTTPS Page", html)
        self.assertEqual(url, "https://secure.example.com/")

    # -------------------------------------------------------------------------
    # 5. Redirect handling
    # -------------------------------------------------------------------------
    def test_05_redirect_handling(self):
        """Test following valid HTTP 301/302 redirects to the final destination."""
        mock_session = MagicMock()

        # Hop 1: 301 Redirect
        r1 = MagicMock()
        r1.status_code = 301
        r1.headers = {"Location": "https://example.com/new-home"}

        # Hop 2: 200 OK
        r2 = MagicMock()
        r2.status_code = 200
        r2.headers = {"Content-Type": "text/html"}
        r2.iter_content.return_value = [b"<html><body><h1>Redirected Page</h1></body></html>"]
        r2.encoding = "utf-8"

        mock_session.get.side_effect = [r1, r2]

        success, html, final_url = fetch_website(
            "https://example.com/old-home",
            check_dns=False,
            session=mock_session,
        )
        self.assertTrue(success)
        self.assertEqual(final_url, "https://example.com/new-home")
        self.assertIn("Redirected Page", html)

    # -------------------------------------------------------------------------
    # 6. Inaccessible website
    # -------------------------------------------------------------------------
    def test_06_inaccessible_website(self):
        """Test graceful handling of inaccessible websites (404, 500, or connection errors)."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_session.get.return_value = mock_resp

        success, err, _ = fetch_website(
            "https://example.com/nonexistent",
            check_dns=False,
            session=mock_session,
        )
        self.assertFalse(success)
        self.assertIn("404", err)

    # -------------------------------------------------------------------------
    # 7. Invalid HTML
    # -------------------------------------------------------------------------
    def test_07_invalid_html(self):
        """Test extracting content from malformed, incomplete, or unclosed HTML tags."""
        malformed = "<title>Broken Page</title><h1>Unclosed Header<p>Paragraph without closing body"
        result = extract_website_content(malformed, "https://broken.com")
        self.assertEqual(result["title"], "Broken Page")
        self.assertTrue(any(h["text"] == "Unclosed Header" for h in result["headings"]))
        self.assertIn("Paragraph without closing body", result["paragraphs"])

    # -------------------------------------------------------------------------
    # 8. HTML content extraction
    # -------------------------------------------------------------------------
    def test_08_html_content_extraction(self):
        """Test full extraction of title, meta description, and sections."""
        result = extract_website_content(self.sample_html, "https://brandproof.ai")
        self.assertEqual(result["title"], "BrandProof AI Platform")
        self.assertEqual(result["meta_description"], "AI-powered brand verification and copy proofing.")
        self.assertGreater(len(result["sections"]), 0)
        self.assertNotIn("analytics tracking", " ".join(result["paragraphs"]))

    # -------------------------------------------------------------------------
    # 9. Heading extraction
    # -------------------------------------------------------------------------
    def test_09_heading_extraction(self):
        """Test extraction of H1, H2, and H3 headings preserving level and text."""
        result = extract_website_content(self.sample_html, "https://brandproof.ai")
        headings = result["headings"]
        levels = [h["level"] for h in headings]
        texts = [h["text"] for h in headings]

        self.assertIn("h1", levels)
        self.assertIn("h2", levels)
        self.assertIn("h3", levels)
        self.assertIn("Welcome to BrandProof AI", texts)
        self.assertIn("Core Capabilities", texts)
        self.assertIn("Detailed Specs", texts)

    # -------------------------------------------------------------------------
    # 10. Paragraph extraction
    # -------------------------------------------------------------------------
    def test_10_paragraph_extraction(self):
        """Test extraction of paragraph text associated with headings."""
        result = extract_website_content(self.sample_html, "https://brandproof.ai")
        paras = result["paragraphs"]
        self.assertTrue(any("enterprise teams" in p for p in paras))
        self.assertTrue(any("Automated tone checking" in p for p in paras))

    # -------------------------------------------------------------------------
    # 11. CTA extraction
    # -------------------------------------------------------------------------
    def test_11_cta_extraction(self):
        """Test extraction of button and anchor CTA text."""
        result = extract_website_content(self.sample_html, "https://brandproof.ai")
        ctas = result["cta_text"]
        self.assertIn("Start Free Trial", ctas)
        self.assertIn("Schedule Demo", ctas)

    # -------------------------------------------------------------------------
    # 12. Image alt text extraction
    # -------------------------------------------------------------------------
    def test_12_image_alt_text_extraction(self):
        """Test extraction of alt attributes from image tags."""
        result = extract_website_content(self.sample_html, "https://brandproof.ai")
        alts = result["image_alt_texts"]
        self.assertIn("BrandProof Analytics Dashboard", alts)
        # Empty alt tags should not create blank items
        self.assertNotIn("", alts)

    # -------------------------------------------------------------------------
    # 13. Duplicate content removal
    # -------------------------------------------------------------------------
    def test_13_duplicate_content_removal(self):
        """Test cleaning and deduplication of repeated headings and paragraphs."""
        raw = {
            "title": "Dup Test",
            "meta_description": "",
            "headings": [
                {"level": "h2", "text": "Repeated Heading"},
                {"level": "h2", "text": "Repeated Heading"},
            ],
            "paragraphs": [
                "Repeated paragraph content.",
                "Repeated paragraph content.",
                "Unique paragraph content.",
            ],
            "cta_text": ["Click", "Click"],
            "image_alt_texts": ["Logo", "Logo"],
            "sections": [
                {"heading": "Repeated Heading", "level": "h2", "content": "Repeated paragraph content."},
                {"heading": "Repeated Heading", "level": "h2", "content": "Repeated paragraph content."},
            ],
        }
        cleaned = clean_extracted_content(raw)
        self.assertEqual(len(cleaned["headings"]), 1)
        self.assertEqual(len(cleaned["paragraphs"]), 2)
        self.assertEqual(len(cleaned["cta_text"]), 1)
        self.assertEqual(len(cleaned["image_alt_texts"]), 1)
        self.assertEqual(len(cleaned["sections"]), 1)

    # -------------------------------------------------------------------------
    # 14. Internal link discovery
    # -------------------------------------------------------------------------
    def test_14_internal_link_discovery(self):
        """Test discovery of internal same-domain links from HTML anchor tags."""
        html = """
        <a href="/about">About Us</a>
        <a href="/pricing">Pricing</a>
        <a href="https://example.com/features">Features</a>
        """
        links = discover_internal_links("https://example.com/home", html)
        self.assertIn("https://example.com/about", links)
        self.assertIn("https://example.com/pricing", links)
        self.assertIn("https://example.com/features", links)

    # -------------------------------------------------------------------------
    # 15. Maximum page limit
    # -------------------------------------------------------------------------
    def test_15_maximum_page_limit(self):
        """Test that website crawler strictly stops after reaching max_pages."""
        pages_store = {
            "https://example.com/": (True, '<a href="/p1">P1</a><a href="/p2">P2</a>', "https://example.com/"),
            "https://example.com/p1": (True, '<a href="/p3">P3</a>', "https://example.com/p1"),
            "https://example.com/p2": (True, '<p>P2</p>', "https://example.com/p2"),
            "https://example.com/p3": (True, '<p>P3</p>', "https://example.com/p3"),
        }
        crawl_res = crawl_website(
            "https://example.com",
            max_pages=2,
            check_dns=False,
            fetch_fn=lambda u: pages_store.get(u, (False, "404", u)),
        )
        self.assertEqual(crawl_res["pages_crawled"], 2)
        self.assertEqual(len(crawl_res["pages"]), 2)

    # -------------------------------------------------------------------------
    # 16. Crawl depth limit
    # -------------------------------------------------------------------------
    def test_16_crawl_depth_limit(self):
        """Test that crawler respects max_depth and does not traverse deeper links."""
        # Level 0 -> Level 1 -> Level 2
        pages_store = {
            "https://example.com/": (True, '<a href="/level1">L1</a>', "https://example.com/"),
            "https://example.com/level1": (True, '<a href="/level2">L2</a>', "https://example.com/level1"),
            "https://example.com/level2": (True, '<p>End</p>', "https://example.com/level2"),
        }
        # With max_depth=0, only level 0 is fetched
        crawl_depth_0 = crawl_website(
            "https://example.com",
            max_pages=10,
            max_depth=0,
            check_dns=False,
            fetch_fn=lambda u: pages_store.get(u, (False, "404", u)),
        )
        self.assertEqual(crawl_depth_0["pages_crawled"], 1)

    # -------------------------------------------------------------------------
    # 17. Cross-domain link rejection
    # -------------------------------------------------------------------------
    def test_17_cross_domain_link_rejection(self):
        """Test that links pointing to external domains are strictly filtered out."""
        html = """
        <a href="https://other-domain.com/page">External</a>
        <a href="https://evil.org">External 2</a>
        <a href="/internal-page">Internal</a>
        """
        links = discover_internal_links("https://mybrand.com/home", html)
        self.assertEqual(links, ["https://mybrand.com/internal-page"])

    # -------------------------------------------------------------------------
    # 18. SSRF protection
    # -------------------------------------------------------------------------
    def test_18_ssrf_protection(self):
        """Test blocking of localhost, private IPs, cloud metadata, and malicious redirects."""
        blocked_targets = [
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://10.0.0.1/admin",
            "http://192.168.1.1/setup",
            "http://172.16.0.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal",
        ]
        for target in blocked_targets:
            valid, err = validate_url(target, check_dns=False)
            self.assertFalse(valid, f"Expected SSRF block for {target}")
            self.assertIn("SSRF", err)

        # Test redirect to private IP is blocked during fetch
        mock_session = MagicMock()
        mock_r = MagicMock()
        mock_r.status_code = 302
        mock_r.headers = {"Location": "http://127.0.0.1/secret"}
        mock_session.get.return_value = mock_r

        success, err, _ = fetch_website(
            "https://example.com",
            check_dns=False,
            session=mock_session,
        )
        self.assertFalse(success)
        self.assertIn("unsafe destination blocked", err)

    # -------------------------------------------------------------------------
    # 19. Gemini analysis
    # -------------------------------------------------------------------------
    def test_19_gemini_analysis(self):
        """Test structured analysis output generation across all categories."""
        def mock_gemini(prompt, system_prompt):
            self.assertIn("EXTRACTED WEBSITE CONTENT", prompt)
            return {
                "status": "success",
                "website_url": "https://brandproof.ai",
                "website_metadata": {"title": "BrandProof", "meta_description": "Proofing"},
                "content_summary": "Brand compliance platform.",
                "findings": [
                    {
                        "page_url": "https://brandproof.ai",
                        "section": "Core Capabilities",
                        "original_text": "We provides tools",
                        "suggested_text": "We provide tools",
                        "category": "Grammar",
                        "severity": "medium",
                        "explanation": "Subject-verb agreement.",
                    }
                ],
                "tone_analysis": {"identified_tone": "Professional", "consistency": "High", "recommendations": []},
                "readability_analysis": {"observations": ["Clear copy"], "recommendations": []},
                "brand_analysis": {"issues": [], "recommendations": []},
                "seo_content_analysis": {
                    "title_analysis": "Concise title",
                    "meta_description_analysis": "Good description",
                    "heading_analysis": ["H1 is well-placed"],
                    "alt_text_issues": [],
                    "recommendations": [],
                },
                "overall_recommendations": ["Fix grammar error in capabilities section."],
                "summary": {
                    "total_issues": 1,
                    "grammar_issues": 1,
                    "spelling_issues": 0,
                    "brand_issues": 0,
                    "readability_issues": 0,
                    "seo_content_issues": 0,
                },
            }

        content = extract_website_content(self.sample_html, "https://brandproof.ai")
        result = analyze_website_content(content, gemini_client=mock_gemini)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["category"], "Grammar")
        self.assertEqual(result["summary"]["grammar_issues"], 1)

    # -------------------------------------------------------------------------
    # 20. Malformed Gemini response
    # -------------------------------------------------------------------------
    def test_20_malformed_gemini_response(self):
        """Test error handling when Gemini returns invalid JSON string or bad format."""
        def mock_bad_gemini(prompt, system_prompt):
            return "NOT_JSON_CONTENT {bad"

        content = extract_website_content(self.sample_html, "https://brandproof.ai")
        result = analyze_website_content(content, gemini_client=mock_bad_gemini)

        self.assertEqual(result["status"], "error")
        self.assertIn("Gemini analysis error", result["message"])

    # -------------------------------------------------------------------------
    # 21. Large content chunking
    # -------------------------------------------------------------------------
    def test_21_large_content_chunking(self):
        """Test splitting large website sections into chunks under size threshold."""
        large_sections = [
            {"heading": f"Section {i}", "level": "h2", "content": f"Content paragraph for section {i}. " * 50}
            for i in range(20)
        ]
        content = {
            "url": "https://example.com",
            "title": "Large Site",
            "meta_description": "Description",
            "sections": large_sections,
        }
        chunks = chunk_content_sections(content, max_chars_per_chunk=3000)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertEqual(chunk["url"], "https://example.com")
            self.assertTrue(len(chunk["sections"]) > 0)

    # -------------------------------------------------------------------------
    # 22. Duplicate finding removal
    # -------------------------------------------------------------------------
    def test_22_duplicate_finding_removal(self):
        """Test that identical findings from multiple chunks are deduplicated."""
        dup_finding = {
            "page_url": "https://example.com",
            "section": "Intro",
            "original_text": "We is",
            "suggested_text": "We are",
            "category": "Grammar",
            "severity": "medium",
            "explanation": "Grammar error",
        }
        res1 = {
            "website_url": "https://example.com",
            "content_summary": "Part 1",
            "findings": [dup_finding],
            "overall_recommendations": ["Recommendation A"],
        }
        res2 = {
            "website_url": "https://example.com",
            "content_summary": "Part 2",
            "findings": [dup_finding],  # Duplicate
            "overall_recommendations": ["Recommendation A"],  # Duplicate
        }
        combined = combine_analysis_results([res1, res2])
        self.assertEqual(len(combined["findings"]), 1)
        self.assertEqual(len(combined["overall_recommendations"]), 1)
        self.assertEqual(combined["summary"]["total_issues"], 1)

    # -------------------------------------------------------------------------
    # 23. Error handling
    # -------------------------------------------------------------------------
    def test_23_error_handling(self):
        """Test end-to-end analyze_website handles errors cleanly without throwing."""
        # Case A: Invalid URL
        res_invalid = analyze_website("not_a_valid_url", check_dns=False)
        self.assertEqual(res_invalid["status"], "error")
        self.assertIn("Invalid or unsafe URL", res_invalid["message"])

        # Case B: Fetch failure
        res_failed_fetch = analyze_website(
            "https://example.com",
            check_dns=False,
            fetch_fn=lambda u: (False, "Connection reset by peer", u),
        )
        self.assertEqual(res_failed_fetch["status"], "error")
        self.assertIn("Connection reset", res_failed_fetch["message"])


if __name__ == "__main__":
    unittest.main()
