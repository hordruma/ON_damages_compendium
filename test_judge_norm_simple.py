#!/usr/bin/env python3
"""
Simple test for judge name normalization logic (no imports needed).
"""

import re


def normalize_judge_name(judge_name: str) -> str:
    """
    Normalize judge names to last name only.

    Examples:
        "Smith J." -> "Smith"
        "A. Smith J.A." -> "Smith"
        "Hon. John Smith J." -> "Smith"
        "Smith, J." -> "Smith"
        "Brown J.J.A." -> "Brown"

    Args:
        judge_name: Raw judge name

    Returns:
        Normalized last name only
    """
    if not judge_name:
        return ""

    name = judge_name.strip()

    # Remove trailing titles and suffixes (J., J.A., J.J.A., C.J., etc.)
    name = re.sub(r',?\s*(J\.J\.A\.|J\.A\.|J\.|C\.J\.|C\.J\.O\.|C\.J\.C\.)$', '', name, flags=re.IGNORECASE)

    # Remove "The Honourable", "Hon.", etc. at start
    name = re.sub(r'^(The\s+)?(Hon\.?|Honourable)\s+', '', name, flags=re.IGNORECASE)

    # Remove any remaining commas
    name = name.replace(',', '')

    # Standardize spacing
    name = re.sub(r'\s+', ' ', name).strip()

    # Extract last name (last word after splitting)
    # This handles "A. Smith", "John Smith", "A.B. Smith" -> "Smith"
    if name:
        parts = name.split()
        if parts:
            # Last part is the last name
            last_name = parts[-1]
            # Clean up any remaining periods
            last_name = last_name.rstrip('.')
            return last_name

    return ""


def test_normalize_judge_name():
    """Test various judge name formats."""

    test_cases = [
        # (input, expected_output)
        ("Smith J.", "Smith"),
        ("A. Smith J.", "Smith"),
        ("A. Smith J.A.", "Smith"),
        ("Brown J.J.A.", "Brown"),
        ("Hon. John Smith J.", "Smith"),
        ("The Honourable Jane Doe J.A.", "Doe"),
        ("Smith, J.", "Smith"),
        ("A.B. Jones J.", "Jones"),
        ("Wilson C.J.", "Wilson"),
        ("Taylor C.J.O.", "Taylor"),
        ("Anderson", "Anderson"),
        ("O'Brien J.A.", "O'Brien"),
        ("", ""),  # Empty string
        ("  Smith  J.  ", "Smith"),  # Extra whitespace
        ("M. Smith, J.", "Smith"),
        ("SMITH J.", "SMITH"),  # All caps (preserved)
    ]

    print("Testing judge name normalization...")
    print("=" * 70)

    passed = 0
    failed = 0

    for input_name, expected in test_cases:
        result = normalize_judge_name(input_name)

        if result == expected:
            status = "✓"
            passed += 1
        else:
            status = "✗"
            failed += 1

        input_display = f'"{input_name}"' if input_name else '""'
        print(f"{status} {input_display:40} -> '{result:15}' (expected: '{expected}')")

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("\n⚠️  Some tests failed!")
        return False
    else:
        print("\n✅ All tests passed!")
        return True


def main():
    """Run all tests."""
    success = test_normalize_judge_name()

    print("\nNOTE: The normalization extracts the LAST WORD as the last name.")
    print("Examples:")
    print("  'A. Smith J.'        -> 'Smith'")
    print("  'Hon. John Smith J.' -> 'Smith'")
    print("  'Brown J.J.A.'       -> 'Brown'")
    print("  'O'Connor J.A.'      -> 'O'Connor' (preserves apostrophe)")
    print("\nThis ensures consistent judge names for analytics!")

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
