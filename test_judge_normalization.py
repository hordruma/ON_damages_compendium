#!/usr/bin/env python3
"""
Test judge name normalization for table-based parser.

Ensures judge names are normalized to last name only for
consistent judge analytics.
"""

from damages_parser_table import TableBasedParser


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
        ("St. Pierre J.", "Pierre"),  # Handles "St." prefix
        ("van der Berg J.", "Berg"),  # Last word is last name
        ("", ""),  # Empty string
        (None, ""),  # None
        ("  Smith  J.  ", "Smith"),  # Extra whitespace
    ]

    print("Testing judge name normalization...")
    print("=" * 70)

    passed = 0
    failed = 0

    for input_name, expected in test_cases:
        result = TableBasedParser.normalize_judge_name(input_name)

        if result == expected:
            status = "✓"
            passed += 1
        else:
            status = "✗"
            failed += 1

        input_display = f'"{input_name}"' if input_name else "None"
        print(f"{status} {input_display:35} -> {result:15} (expected: {expected})")

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("\n⚠️  Some tests failed!")
        return False
    else:
        print("\n✅ All tests passed!")
        return True


def test_edge_cases():
    """Test edge cases and unusual formats."""

    print("\nTesting edge cases...")
    print("=" * 70)

    edge_cases = [
        # Multiple judges (should only get last name of the string)
        ("Smith and Jones JJ.", "JJ"),  # This is tricky - "JJ" for multiple judges
        ("Smith J. (dissenting)", "Smith"),  # Extra text
        ("M. Smith, J.", "Smith"),
        ("SMITH J.", "SMITH"),  # All caps
        ("smith j.", "smith"),  # All lowercase
        ("Mac Donald J.", "Donald"),  # Space in last name (treats as separate words)
        ("O'Connor J.A.", "O'Connor"),  # Apostrophe in name
        ("Jean-Pierre J.", "Jean-Pierre"),  # Hyphenated name
    ]

    for input_name, note in edge_cases:
        result = TableBasedParser.normalize_judge_name(input_name)
        print(f"  {input_name:30} -> {result:20} (note: {note})")

    print("=" * 70)


def main():
    """Run all tests."""
    success = test_normalize_judge_name()
    test_edge_cases()

    print("\nNOTE: The normalization extracts the LAST WORD as the last name.")
    print("This means:")
    print("  - 'Mac Donald J.' -> 'Donald' (not 'Mac Donald')")
    print("  - 'van der Berg J.' -> 'Berg' (not 'van der Berg')")
    print("  - 'O'Connor J.' -> 'O'Connor' ✓ (keeps apostrophe)")
    print("  - 'Jean-Pierre J.' -> 'Jean-Pierre' ✓ (keeps hyphen)")
    print("\nIf multi-word last names are common, we may need to enhance the logic.")

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
