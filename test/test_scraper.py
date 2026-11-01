"""Test Runner for Web Scraping in BrandProof AI.

Tests the extraction pipeline directly on test/index.html to verify
HTML parsing, title/meta extraction, heading hierarchy, CTA detection,
and image alt text auditing.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path so app modules are resolvable
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "AI_Backend"))

try:
    from app.website_analysis import extract_website_content, clean_extracted_content
except ImportError as err:
    print(f"Error importing website_analysis: {err}")
    print("Ensure you run this script from the workspace root or AI_Backend directory.")
    sys.exit(1)


def main():
    html_file = Path(__file__).parent / "index.html"
    if not html_file.exists():
        print(f"File not found: {html_file}")
        sys.exit(1)

    print("=" * 70)
    print("BrandProof AI - Web Scraping Test on Single Webpage")
    print("=" * 70)
    print(f"Target: {html_file}")

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 1. Extract content using BrandProof AI's extraction logic
    extracted = extract_website_content(html_content, url="https://novapulse.ai")
    cleaned = clean_extracted_content(extracted)

    print("\n[1] Extracted Page Metadata:")
    print(f"  * Title:            {cleaned.get('title')}")
    print(f"  * Meta Description: {cleaned.get('meta_description')}")
    print(f"  * Headings count:   {len(cleaned.get('headings', []))}")
    print(f"  * Sections count:   {len(cleaned.get('sections', []))}")
    print(f"  * Paragraphs count: {len(cleaned.get('paragraphs', []))}")
    print(f"  * CTAs detected:    {len(cleaned.get('cta_text', []))}")
    print(f"  * Image Alt Texts:  {len(cleaned.get('image_alt_texts', []))}")
    print(f"  * Missing Alt Imgs: {cleaned.get('missing_alt_images_count')}")

    print("\n[2] Headings Hierarchy:")
    for h in cleaned.get("headings", [])[:6]:
        print(f"  [{h['level'].upper()}] {h['text']}")

    print("\n[3] Detected Call-To-Action (CTA) Buttons:")
    for cta in cleaned.get("cta_text", []):
        print(f"  -> \"{cta}\"")

    print("\n[4] Image Accessibility Audit:")
    for alt in cleaned.get("image_alt_texts", []):
        print(f"  [OK] Alt found: \"{alt}\"")
    if cleaned.get("missing_alt_images_count", 0) > 0:
        print(f"  [ALERT] {cleaned.get('missing_alt_images_count')} image(s) missing alt text (accessibility gap detected).")

    print("\n[5] Full Extracted JSON Payload Preview (structured):")
    preview = {
        "title": cleaned.get("title"),
        "meta_description": cleaned.get("meta_description"),
        "headings": cleaned.get("headings")[:3],
        "sections": [s["heading"] for s in cleaned.get("sections", [])],
        "cta_text": cleaned.get("cta_text"),
        "missing_alt_images_count": cleaned.get("missing_alt_images_count"),
    }
    print(json.dumps(preview, indent=2))
    print("\n" + "=" * 70)
    print("Web scraping test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
