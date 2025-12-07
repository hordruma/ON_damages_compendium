#!/usr/bin/env python3
"""
Test script to verify section header parsing improvements.
Tests the _clean_section_header logic directly.
"""


def _clean_section_header(section_text: str) -> str:
    """
    Clean and validate section headers (copied from damages_parser_table.py).
    """
    if not section_text:
        return ""

    text = section_text.strip()

    # Reject if starts with $ or digits
    if text and (text[0] == '$' or text[0].isdigit()):
        return ""

    # Reject invalid patterns
    invalid_patterns = [
        "CONTRIBUTORILY",
        "P11:", "P12:",
        "SPECIAL",
        "DEFENDANT",
        "PLAINTIFF",
        "MOTION",
        "GENERAL DAMAGES",  # Column header
        "PECUNIARY",
        "NON-PECUNIARY",
        "DAMAGES",  # When standalone
        "AWARD",
        "TOTAL",
    ]
    text_upper = text.upper()
    for pattern in invalid_patterns:
        if pattern in text_upper:
            return ""

    # Whitelist: Only accept known sections
    valid_sections = [
        # General/common subsections
        "GENERAL", "MISCELLANEOUS", "MOST SEVERE", "FATAL",
        # Head/sensory
        "BRAIN", "SKULL", "HEAD",
        "EARS", "HEARING", "EYE", "SIGHT", "TEETH",
        # Spine
        "CERVICAL", "THORACIC", "LUMBAR", "SPINE", "SPINAL",
        "NECK", "BACK", "WHIPLASH",
        # Arms
        "SHOULDER", "ARM", "ELBOW", "FOREARM", "WRIST", "HAND", "FINGER", "WHOLE", "COLLAR",
        # Body/torso
        "CHEST", "THORAX", "ABDOMEN", "PELVIS", "BODY",
        "BUTTOCK", "THIGH", "INTERNAL", "REPRODUCTIVE", "RIBS",
        # Legs
        "HIP", "KNEE", "LEG", "ANKLE", "FOOT", "TOE", "LOWER", "LOSS",
        # Skin
        "SKIN", "BURNS", "SCARS", "LACERATIONS",
        # Severe injuries
        "PARAPLEGIA", "QUADRIPLEGIA",
        # Psychological
        "PSYCHOLOGICAL", "PSYCHIATRIC", "MENTAL", "TRAUMATIC", "NEUROSIS",
        "PAIN", "SUFFERING", "MINOR",
        # Other
        "MULTIPLE", "SOFT TISSUE",
        "PRE-EXISTING", "DISABILITY", "CONDITION",
        "SEXUAL", "ASSAULT", "ABUSE",
        "GUIDANCE", "CARE", "COMPANIONSHIP",
        # FLA relationships
        "FATHER", "MOTHER", "PARENT",
        "SON", "DAUGHTER", "CHILD",
        "BROTHER", "SISTER", "SIBLING",
        "SPOUSE", "HUSBAND", "WIFE",
        "GRANDFATHER", "GRANDMOTHER", "GRANDPARENT", "GRANDCHILD",
    ]

    # Check if text contains any valid section keyword
    found_valid = False
    for valid in valid_sections:
        if valid in text_upper:
            found_valid = True
            break

    if not found_valid:
        return ""  # Reject

    # Clean trailing " - $..." patterns
    import re
    text = re.sub(r'\s*-\s*\$[\d,\.]+', '', text)
    text = re.sub(r'\s*-\s*$', '', text)

    return text.strip()


def test_section_header_cleaning():
    """Test that GENERAL and other section headers are not rejected."""

    test_cases = [
        # (input, should_be_accepted, description)
        ("GENERAL", True, "GENERAL should be accepted"),
        ("HEAD", True, "HEAD should be accepted"),
        ("BRAIN & SKULL", True, "BRAIN & SKULL should be accepted"),
        ("MISCELLANEOUS", True, "MISCELLANEOUS should be accepted"),
        ("MOST SEVERE INJURIES", True, "MOST SEVERE INJURIES should be accepted"),
        ("FATAL INJURIES", True, "FATAL INJURIES should be accepted"),
        ("ELBOW", True, "ELBOW should be accepted"),
        ("WHIPLASH", True, "WHIPLASH should be accepted"),
        ("EARS/HEARING", True, "EARS/HEARING should be accepted"),
        ("SKIN", True, "SKIN should be accepted"),
        ("BURNS", True, "BURNS should be accepted"),
        ("PARAPLEGIA", True, "PARAPLEGIA should be accepted"),
        ("GENERAL DAMAGES", False, "GENERAL DAMAGES (column header) should be rejected"),
        ("NON-PECUNIARY", False, "NON-PECUNIARY (column header) should be rejected"),
        ("$85,000", False, "Money amounts should be rejected"),
        ("Defendant's motion", False, "Case text should be rejected"),
        ("DAUGHTER - $8,000.00", True, "DAUGHTER with money should be cleaned"),
        ("ARMS", True, "ARMS should be accepted"),
        ("LEGS", True, "LEGS should be accepted"),
        ("BODY", True, "BODY should be accepted"),
        ("SPINE", True, "SPINE should be accepted"),
    ]

    print("Testing section header cleaning...")
    print("=" * 70)

    passed = 0
    failed = 0

    for input_text, should_accept, description in test_cases:
        result = _clean_section_header(input_text)
        is_accepted = bool(result)

        if is_accepted == should_accept:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1

        print(f"{status}: {description}")
        print(f"  Input:  '{input_text}'")
        print(f"  Output: '{result}'")
        print(f"  Expected: {'Accepted' if should_accept else 'Rejected'}")
        print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False


if __name__ == "__main__":
    test_passed = test_section_header_cleaning()

    if test_passed:
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        exit(0)
    else:
        print("\n" + "=" * 70)
        print("✗ SOME TESTS FAILED")
        print("=" * 70)
        exit(1)
