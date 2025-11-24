"""
Tests for Anatomical Mappings
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from anatomical_mappings import map_anatomical_term_to_regions


def test_anatomical_mappings():
    """Test anatomical term to region mapping"""
    print("=" * 70)
    print("Anatomical Mappings - Test Suite")
    print("=" * 70)
    print()

    # Test cases
    test_cases = [
        ("comminuted tibial fracture", "The patient sustained a comminuted left tibial fracture in the MVA"),
        ("rotator cuff tear", "MRI reveals a full-thickness right rotator cuff tear"),
        ("C5-C6 disc herniation", "Cervical spine imaging shows C5-C6 disc herniation with cord compression"),
        ("ACL tear", "Examination reveals bilateral ACL tears"),
    ]

    print("Testing anatomical term mappings:")
    print("-" * 70)

    for term, context in test_cases:
        regions = map_anatomical_term_to_regions(term, context)
        print(f"\nTerm: '{term}'")
        print(f"Context: {context}")
        print(f"Mapped regions: {regions}")

    print()
    print("✅ All anatomical mapping tests completed")


if __name__ == "__main__":
    test_anatomical_mappings()
