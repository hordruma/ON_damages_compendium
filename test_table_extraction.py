#!/usr/bin/env python3
"""
Test and compare table-based extraction vs full-page extraction.

This script demonstrates the efficiency gains of table extraction:
- Processes rows instead of full pages
- Cheaper (smaller prompts)
- Faster (less token processing)
- More reliable (structured input)
"""

import os
import sys
import time
import pdfplumber
from damages_parser_table import TableBasedParser, RateLimiter

# Configuration
ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://your-resource.openai.azure.com/")
API_KEY = os.getenv("AZURE_API_KEY", "your-api-key")
MODEL = os.getenv("AZURE_MODEL", "gpt-5-nano")  # Try with cheaper model!
PDF_PATH = "2024damagescompendium.pdf"

# Test range - adjust to pages with tables
TEST_START_PAGE = 50
TEST_END_PAGE = 52


def inspect_tables(pdf_path: str, page_num: int):
    """Inspect tables on a specific page."""
    print(f"\n{'='*70}")
    print(f"INSPECTING PAGE {page_num}")
    print('='*70)

    with pdfplumber.open(pdf_path) as pdf:
        if page_num < 1 or page_num > len(pdf.pages):
            print(f"Invalid page number: {page_num}")
            return

        page = pdf.pages[page_num - 1]

        # Get page text
        page_text = page.extract_text() or ""
        print(f"\nPage text length: {len(page_text)} chars")

        # Show first 300 chars
        print(f"\nFirst 300 chars:")
        print("-" * 70)
        print(page_text[:300])
        print("-" * 70)

        # Extract tables
        tables = page.extract_tables()

        if not tables:
            print("\n⚠️  No tables found on this page!")
            return

        print(f"\n✓ Found {len(tables)} table(s)")

        for table_idx, table in enumerate(tables):
            print(f"\n--- Table {table_idx + 1} ---")
            print(f"Rows: {len(table)}")

            if not table:
                continue

            # Show header
            header = table[0]
            print(f"\nHeader ({len(header)} columns):")
            for i, col in enumerate(header):
                print(f"  {i+1}. {col}")

            # Show first 3 data rows
            print(f"\nFirst 3 data rows:")
            for row_idx, row in enumerate(table[1:4]):
                print(f"\n  Row {row_idx + 1}:")
                for col_idx, (col_name, cell) in enumerate(zip(header, row)):
                    cell_val = str(cell).strip() if cell else "(empty)"
                    if len(cell_val) > 60:
                        cell_val = cell_val[:57] + "..."
                    print(f"    {col_name}: {cell_val}")


def test_table_extraction():
    """Test table-based extraction."""
    print(f"\n{'='*70}")
    print(f"TESTING TABLE-BASED EXTRACTION")
    print('='*70)
    print(f"Model: {MODEL}")
    print(f"Pages: {TEST_START_PAGE}-{TEST_END_PAGE}")

    # Create parser
    rate_limiter = RateLimiter(200)
    parser = TableBasedParser(
        endpoint=ENDPOINT,
        api_key=API_KEY,
        model=MODEL,
        verbose=True,
        rate_limiter=rate_limiter
    )

    # Parse
    start_time = time.time()
    cases = parser.parse_pdf(
        pdf_path=PDF_PATH,
        start_page=TEST_START_PAGE,
        end_page=TEST_END_PAGE,
        output_json="test_table_output.json"
    )
    elapsed = time.time() - start_time

    print(f"\n{'='*70}")
    print(f"RESULTS")
    print('='*70)
    print(f"Total cases: {len(cases)}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print(f"Cases per second: {len(cases)/elapsed:.2f}")

    if cases:
        print(f"\n--- Sample Case ---")
        sample = cases[0]
        print(f"Case name: {sample.get('case_name')}")
        print(f"Year: {sample.get('year')}")
        print(f"Category: {sample.get('category')}")
        print(f"Court: {sample.get('court')}")
        print(f"Damages: ${sample.get('non_pecuniary_damages'):,}" if sample.get('non_pecuniary_damages') else "Damages: N/A")
        print(f"Injuries: {len(sample.get('injuries', []))}")
        print(f"Source page: {sample.get('source_page')}")

        if sample.get('injuries'):
            print(f"\nInjuries:")
            for inj in sample.get('injuries', [])[:3]:
                print(f"  - {inj}")

    return cases


def compare_approaches():
    """Show comparison between table vs full-page extraction."""
    print(f"\n{'='*70}")
    print(f"APPROACH COMPARISON")
    print('='*70)

    print("\n1. FULL-PAGE EXTRACTION (damages_parser_azure.py)")
    print("   Pros:")
    print("   - Flexible, handles varying formats")
    print("   - Can capture narrative text outside tables")
    print("   Cons:")
    print("   - EXPENSIVE: Sends full page text (3000-5000 tokens/page)")
    print("   - Slower processing")
    print("   - Needs sliding window for multi-page cases")
    print("   - Requires powerful models (5-chat, 4o)")
    print("   - Complex merging logic")
    print("   Estimated cost for 655 pages: $4-6 with GPT-5")

    print("\n2. TABLE-BASED EXTRACTION (damages_parser_table.py)")
    print("   Pros:")
    print("   - CHEAP: Sends only row text (100-300 tokens/row)")
    print("   - 10-50x cost reduction")
    print("   - Faster processing (smaller prompts)")
    print("   - Works with cheaper models (5-nano, 4o-mini)")
    print("   - Pre-labeled columns (plaintiff, defendant, etc.)")
    print("   - Deterministic merging (rows without citations → previous case)")
    print("   - Body region from section headers")
    print("   Cons:")
    print("   - Depends on pdfplumber table detection (good for this PDF)")
    print("   Estimated cost for 655 pages: $0.20-0.50 with GPT-5-nano")

    print("\n📊 COST COMPARISON:")
    print("   Full-page: $4-6")
    print("   Table-based: $0.20-0.50")
    print("   Savings: 90-95% cheaper! 🎉")


def main():
    """Run tests."""
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: PDF not found at {PDF_PATH}")
        sys.exit(1)

    if "your-resource" in ENDPOINT or "your-api-key" in API_KEY:
        print("❌ Error: Please set Azure credentials:")
        print("   export AZURE_ENDPOINT='https://your-resource.openai.azure.com/'")
        print("   export AZURE_API_KEY='your-actual-api-key'")
        print("   export AZURE_MODEL='gpt-5-nano'")
        sys.exit(1)

    print(f"{'='*70}")
    print(f"TABLE-BASED EXTRACTION TEST")
    print('='*70)

    # Show comparison
    compare_approaches()

    # Inspect sample page
    print(f"\nInspecting page {TEST_START_PAGE} to understand table structure...")
    inspect_tables(PDF_PATH, TEST_START_PAGE)

    # Ask user if they want to proceed
    print(f"\n{'='*70}")
    response = input(f"Proceed with parsing pages {TEST_START_PAGE}-{TEST_END_PAGE}? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        sys.exit(0)

    # Test table extraction
    cases = test_table_extraction()

    print(f"\n✅ Test complete!")
    print(f"   Results saved to: test_table_output.json")

    return cases


if __name__ == "__main__":
    main()
