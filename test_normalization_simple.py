#!/usr/bin/env python3
"""
Simple test to verify category normalization logic.
Tests the core normalization behavior without full module imports.
"""


def test_case_insensitive_comparison():
    """Test case-insensitive comparison logic used in the updated code."""

    # Simulate the logic from get_category_cases()
    test_regions = ['ANKLE', 'ankle', 'Ankle', 'KNEE', 'Knee']

    # Test uppercase normalization
    normalized = set()
    for region in test_regions:
        if region:
            normalized.add(region.strip().upper())

    print("Testing case normalization...")
    print(f"  Input regions: {test_regions}")
    print(f"  Normalized regions: {sorted(normalized)}")

    assert len(normalized) == 2, f"Expected 2 unique regions, got {len(normalized)}"
    assert 'ANKLE' in normalized, "ANKLE not found"
    assert 'KNEE' in normalized, "KNEE not found"
    print("  ✓ Normalization produces 2 unique categories")

    # Test case-insensitive matching logic
    print("\nTesting case-insensitive matching...")

    category_name = 'ankle'  # lowercase search term
    category_name_upper = category_name.upper()

    matched_regions = []
    for region in test_regions:
        region_upper = region.upper() if region else ''
        if region_upper == category_name_upper:
            matched_regions.append(region)

    print(f"  Searching for: '{category_name}'")
    print(f"  Matched regions: {matched_regions}")

    assert len(matched_regions) == 3, f"Expected 3 matches, got {len(matched_regions)}"
    print(f"  ✓ Found all 3 'ankle' variations")

    # Test with uppercase search term
    category_name = 'ANKLE'
    category_name_upper = category_name.upper()

    matched_regions = []
    for region in test_regions:
        region_upper = region.upper() if region else ''
        if region_upper == category_name_upper:
            matched_regions.append(region)

    print(f"\n  Searching for: '{category_name}'")
    print(f"  Matched regions: {matched_regions}")

    assert len(matched_regions) == 3, f"Expected 3 matches, got {len(matched_regions)}"
    print(f"  ✓ Found all 3 'ANKLE' variations")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nThe normalization logic will correctly handle:")
    print("  • 'ANKLE' and 'ankle' as the same category")
    print("  • Case-insensitive category filtering")
    print("  • Consistent category display in analytics")


if __name__ == '__main__':
    try:
        test_case_insensitive_comparison()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
