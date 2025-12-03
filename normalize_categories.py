#!/usr/bin/env python3
"""
Normalize injury categories to uppercase across all data files.
This ensures consistent category naming (e.g., "ANKLE" not "ankle").
"""
import json
from pathlib import Path
from typing import Dict, List, Any


def normalize_category_string(category: Any) -> Any:
    """Normalize a category string to uppercase."""
    if isinstance(category, str) and category.strip():
        return category.strip().upper()
    return category


def normalize_case_categories(case: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize all category-related fields in a case."""
    # Normalize top-level category field
    if 'category' in case and isinstance(case['category'], str):
        case['category'] = normalize_category_string(case['category'])

    # Normalize top-level region field
    if 'region' in case and isinstance(case['region'], str):
        case['region'] = normalize_category_string(case['region'])

    # Normalize regions array in extended_data
    if 'extended_data' in case and isinstance(case['extended_data'], dict):
        extended_data = case['extended_data']

        # Normalize regions array
        if 'regions' in extended_data and isinstance(extended_data['regions'], list):
            extended_data['regions'] = [
                normalize_category_string(r) if isinstance(r, str) else r
                for r in extended_data['regions']
            ]

    # Also normalize the legacy 'regions' field at top level if it exists
    if 'regions' in case and isinstance(case['regions'], list):
        case['regions'] = [
            normalize_category_string(r) if isinstance(r, str) else r
            for r in case['regions']
        ]

    return case


def normalize_json_file(file_path: Path) -> tuple[int, int]:
    """
    Normalize categories in a JSON file.

    Returns:
        Tuple of (total_cases, modified_cases)
    """
    print(f"\nProcessing: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"  ⚠️  File not found, skipping")
        return 0, 0
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON: {e}")
        return 0, 0

    # Handle different data structures
    cases = []
    if isinstance(data, list):
        cases = data
    elif isinstance(data, dict):
        # Could be a dict with a 'cases' key or other structure
        if 'cases' in data:
            cases = data['cases']
        elif 'data' in data:
            cases = data['data']
        else:
            # Treat the whole dict as a single item
            cases = [data]

    total_cases = len(cases)
    modified_cases = 0

    # Normalize each case
    for case in cases:
        if not isinstance(case, dict):
            continue

        # Store original values to detect changes
        original_category = case.get('category')
        original_region = case.get('region')
        original_regions = case.get('extended_data', {}).get('regions', [])

        # Normalize
        normalize_case_categories(case)

        # Check if anything changed
        if (case.get('category') != original_category or
            case.get('region') != original_region or
            case.get('extended_data', {}).get('regions', []) != original_regions):
            modified_cases += 1

    # Write back to file
    if modified_cases > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Normalized {modified_cases}/{total_cases} cases")
    else:
        print(f"  ℹ️  No changes needed (all {total_cases} cases already normalized)")

    return total_cases, modified_cases


def main():
    """Main function to normalize all data files."""
    print("=" * 70)
    print("CATEGORY NORMALIZATION SCRIPT")
    print("=" * 70)
    print("\nNormalizing injury categories to uppercase...")

    base_dir = Path(__file__).parent

    # List of data files to process
    data_files = [
        base_dir / 'damages_full.json',
        base_dir / 'damages_table_based.json',
        base_dir / 'data' / 'sample_data.json',
    ]

    total_files = 0
    total_cases_all = 0
    total_modified_all = 0

    for file_path in data_files:
        if file_path.exists():
            total_files += 1
            total, modified = normalize_json_file(file_path)
            total_cases_all += total
            total_modified_all += modified

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files processed: {total_files}")
    print(f"Total cases: {total_cases_all}")
    print(f"Cases modified: {total_modified_all}")
    print(f"Cases unchanged: {total_cases_all - total_modified_all}")
    print("\n✓ Category normalization complete!")


if __name__ == '__main__':
    main()
