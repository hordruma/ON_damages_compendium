#!/usr/bin/env python3
"""
Test script to verify the sliding window prompt fix.
Tests parsing a small page range to ensure cases are being detected.
"""

import os
import sys
from damages_parser_azure import PDFTextExtractor, DamagesCompendiumParser

# Configuration - update these with your actual values
ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://your-resource.openai.azure.com/")
API_KEY = os.getenv("AZURE_API_KEY", "your-api-key")
MODEL = os.getenv("AZURE_MODEL", "gpt-4o")
PDF_PATH = "2024damagescompendium.pdf"

# Test with a small page range
TEST_START_PAGE = 50  # Adjust to a page you know has cases
TEST_END_PAGE = 52

def test_sliding_window():
    """Test the sliding window parsing on a few pages"""
    print(f"Testing sliding window fix on pages {TEST_START_PAGE}-{TEST_END_PAGE}")
    print(f"Using model: {MODEL}")
    print("-" * 60)

    # Create parser
    parser = DamagesCompendiumParser(
        endpoint=ENDPOINT,
        api_key=API_KEY,
        model=MODEL,
        verbose=True
    )

    # Create PDF extractor
    extractor = PDFTextExtractor(PDF_PATH)

    # Test page parsing with sliding window
    previous_page_text = None
    all_cases = []

    for page_num in range(TEST_START_PAGE, TEST_END_PAGE + 1):
        print(f"\n{'='*60}")
        print(f"Processing page {page_num}")
        print('='*60)

        # Extract text
        page_text = extractor.extract_page(page_num)
        if not page_text:
            print(f"⚠️  Page {page_num} has no text")
            previous_page_text = None
            continue

        print(f"Page text length: {len(page_text)} chars")
        print(f"Has previous context: {previous_page_text is not None}")

        # Parse with sliding window
        cases = parser.parse_page(page_num, page_text, previous_page_text)

        print(f"\n📊 Results:")
        print(f"   Cases found: {len(cases)}")

        if cases:
            for i, case in enumerate(cases):
                case_name = case.get('case_name', 'UNKNOWN')
                year = case.get('year', 'N/A')
                num_plaintiffs = len(case.get('plaintiffs', []))
                print(f"   {i+1}. {case_name} ({year}) - {num_plaintiffs} plaintiff(s)")
        else:
            print("   ⚠️  No cases found on this page!")
            print(f"   First 500 chars of page text:")
            print(f"   {page_text[:500]}")

        all_cases.extend(cases)

        # Update sliding window
        previous_page_text = page_text

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print('='*60)
    print(f"Total pages processed: {TEST_END_PAGE - TEST_START_PAGE + 1}")
    print(f"Total cases found: {len(all_cases)}")

    if len(all_cases) == 0:
        print("\n⚠️  WARNING: No cases found!")
        print("This could mean:")
        print("1. The pages selected don't contain case data")
        print("2. The API credentials are incorrect")
        print("3. There's still an issue with the parsing")
        print("\nTry adjusting TEST_START_PAGE and TEST_END_PAGE to pages")
        print("that you know contain case information.")
        return False
    else:
        print("\n✅ Success! Cases are being parsed correctly.")
        return True

if __name__ == "__main__":
    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: PDF not found at {PDF_PATH}")
        print("Please download the PDF first or update PDF_PATH")
        sys.exit(1)

    # Check if API credentials are set
    if "your-resource" in ENDPOINT or "your-api-key" in API_KEY:
        print("❌ Error: Please set your Azure credentials:")
        print("   export AZURE_ENDPOINT='https://your-resource.openai.azure.com/'")
        print("   export AZURE_API_KEY='your-actual-api-key'")
        print("   export AZURE_MODEL='gpt-4o'  # or your deployment name")
        sys.exit(1)

    success = test_sliding_window()
    sys.exit(0 if success else 1)
