#!/usr/bin/env python3
"""
Test script to verify category normalization works correctly.
"""
import sys
sys.path.insert(0, 'app')

from app.ui.category_analytics import get_all_categories, get_category_cases


def test_category_normalization():
    """Test that category normalization handles case variations correctly."""

    # Create test cases with mixed case
    test_cases = [
        {
            'id': '001',
            'region': 'ankle',  # lowercase
            'extended_data': {'regions': ['ankle']}
        },
        {
            'id': '002',
            'region': 'ANKLE',  # uppercase
            'extended_data': {'regions': ['ANKLE']}
        },
        {
            'id': '003',
            'region': 'Ankle',  # mixed case
            'extended_data': {'regions': ['Ankle']}
        },
        {
            'id': '004',
            'region': 'KNEE',
            'extended_data': {'regions': ['KNEE']}
        }
    ]

    # Test get_all_categories - should normalize all to uppercase
    print("Testing get_all_categories()...")
    categories_dict = get_all_categories(test_cases)
    injury_categories = categories_dict['injury_categories']

    print(f"  Found categories: {injury_categories}")

    # Should have exactly 2 unique categories (ANKLE and KNEE)
    assert len(injury_categories) == 2, f"Expected 2 categories, got {len(injury_categories)}"
    assert 'ANKLE' in injury_categories, "ANKLE not found in categories"
    assert 'KNEE' in injury_categories, "KNEE not found in categories"
    print("  ✓ Categories normalized correctly (2 unique categories)")

    # Test get_category_cases with different case inputs
    print("\nTesting get_category_cases() with case variations...")

    # Search for 'ankle' (lowercase) - should find all ankle cases
    ankle_cases_lower = get_category_cases(test_cases, 'ankle')
    assert len(ankle_cases_lower) == 3, f"Expected 3 ankle cases, got {len(ankle_cases_lower)}"
    print(f"  ✓ Search for 'ankle' found {len(ankle_cases_lower)} cases")

    # Search for 'ANKLE' (uppercase) - should find all ankle cases
    ankle_cases_upper = get_category_cases(test_cases, 'ANKLE')
    assert len(ankle_cases_upper) == 3, f"Expected 3 ankle cases, got {len(ankle_cases_upper)}"
    print(f"  ✓ Search for 'ANKLE' found {len(ankle_cases_upper)} cases")

    # Search for 'Ankle' (mixed case) - should find all ankle cases
    ankle_cases_mixed = get_category_cases(test_cases, 'Ankle')
    assert len(ankle_cases_mixed) == 3, f"Expected 3 ankle cases, got {len(ankle_cases_mixed)}"
    print(f"  ✓ Search for 'Ankle' found {len(ankle_cases_mixed)} cases")

    # Search for 'KNEE' - should find 1 case
    knee_cases = get_category_cases(test_cases, 'KNEE')
    assert len(knee_cases) == 1, f"Expected 1 knee case, got {len(knee_cases)}"
    print(f"  ✓ Search for 'KNEE' found {len(knee_cases)} case")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - Category normalization works correctly!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_category_normalization()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
