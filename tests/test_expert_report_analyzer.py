"""
Tests for Expert Report Analyzer
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from expert_report_analyzer import analyze_expert_report


def test_expert_report_analysis():
    """Test expert report analysis with sample PDF"""
    print("=" * 70)
    print("Expert Report Analyzer - Test Suite")
    print("=" * 70)
    print()

    # Check if test PDF exists
    test_pdf = Path(__file__).parent / "fixtures" / "sample_report.pdf"

    if not test_pdf.exists():
        print("⚠️  No test PDF found at:", test_pdf)
        print("Skipping PDF analysis test.")
        print()
        print("To run this test:")
        print("1. Create tests/fixtures/ directory")
        print("2. Place a sample medical report PDF as 'sample_report.pdf'")
        print("3. Run this test again")
        return

    # Test with regex extraction (no API key needed)
    print("Testing regex-based extraction (no LLM)...")
    result = analyze_expert_report(str(test_pdf), use_llm=False)

    print("\n=== Expert Report Analysis Results ===\n")
    print(json.dumps(result, indent=2))

    print("\n✅ Expert report analysis test completed")


if __name__ == "__main__":
    test_expert_report_analysis()
