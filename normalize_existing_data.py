"""
Utility to normalize judge names and other data in existing damages files.

This script:
1. Normalizes judge names (removes titles like J., J.A., etc.)
2. Ensures plaintiff/defendant names are properly separated
3. Fixes 'other_damages' type categorization

Usage:
    python normalize_existing_data.py damages_full.json -o damages_full_normalized.json
"""

import json
import re
import argparse
from typing import Dict, Any, List


def normalize_judge_name(judge_name: str) -> str:
    """
    Normalize judge names by removing titles and standardizing format.

    Args:
        judge_name: Raw judge name

    Returns:
        Normalized judge name
    """
    if not judge_name:
        return ""

    # Remove common titles and suffixes
    name = judge_name.strip()

    # Remove trailing titles (J., J.A., C.J., etc.)
    name = re.sub(r',?\s*(J\.A\.|J\.|C\.J\.|C\.J\.O\.|C\.J\.C\.)$', '', name, flags=re.IGNORECASE)

    # Remove "The Honourable", "Hon.", etc. at start
    name = re.sub(r'^(The\s+)?(Hon\.?|Honourable)\s+', '', name, flags=re.IGNORECASE)

    # Standardize spacing
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def categorize_other_damage(description: str) -> str:
    """
    Categorize 'other' damages based on description text.

    Args:
        description: Damage description

    Returns:
        Damage type category
    """
    if not description:
        return 'other'

    desc_lower = description.lower()

    if any(term in desc_lower for term in ['future income', 'future earnings', 'future loss of income']):
        return 'future_loss_of_income'
    elif any(term in desc_lower for term in ['past income', 'past earnings', 'past loss of income']):
        return 'past_loss_of_income'
    elif any(term in desc_lower for term in ['future care', 'cost of care', 'future medical']):
        return 'cost_of_future_care'
    elif any(term in desc_lower for term in ['housekeeping', 'household services']):
        return 'housekeeping_capacity'
    else:
        return 'other'


def normalize_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single case dictionary.

    Args:
        case: Case dictionary to normalize

    Returns:
        Normalized case dictionary
    """
    # Normalize judge names
    if 'extended_data' in case and case['extended_data']:
        extended = case['extended_data']

        if 'judges' in extended and extended['judges']:
            extended['judges'] = [
                normalize_judge_name(j) for j in extended['judges'] if j
            ]
            # Remove empty strings
            extended['judges'] = [j for j in extended['judges'] if j]

    # Ensure plaintiff/defendant are properly separated
    case_name = case.get('case_name', '')
    if case_name and ('v.' in case_name or ' v ' in case_name):
        parts = re.split(r'\s+v\.?\s+', case_name, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            if 'extended_data' not in case:
                case['extended_data'] = {}
            if not case['extended_data'].get('plaintiff_name'):
                case['extended_data']['plaintiff_name'] = parts[0].strip()
            if not case['extended_data'].get('defendant_name'):
                case['extended_data']['defendant_name'] = parts[1].strip()

    # Categorize other damages
    if 'extended_data' in case and case['extended_data']:
        extended = case['extended_data']
        if 'other_damages' in extended and extended['other_damages']:
            for damage in extended['other_damages']:
                if not damage.get('type') or damage['type'] == 'Other':
                    desc = damage.get('description', '')
                    damage['type'] = categorize_other_damage(desc)

    return case


def normalize_data_file(input_path: str, output_path: str) -> None:
    """
    Normalize all cases in a JSON file.

    Args:
        input_path: Input JSON file path
        output_path: Output JSON file path
    """
    print(f"Loading data from {input_path}...")
    with open(input_path, 'r') as f:
        cases = json.load(f)

    print(f"Processing {len(cases)} cases...")
    normalized_cases = []
    stats = {
        'judges_normalized': 0,
        'plaintiff_defendant_fixed': 0,
        'damages_categorized': 0
    }

    for idx, case in enumerate(cases):
        if idx % 100 == 0:
            print(f"  Processed {idx}/{len(cases)} cases...")

        # Count before
        old_judges = None
        if 'extended_data' in case and 'judges' in case.get('extended_data', {}):
            old_judges = case['extended_data']['judges'][:]

        normalized = normalize_case(case)

        # Count after
        if old_judges:
            new_judges = normalized.get('extended_data', {}).get('judges', [])
            if old_judges != new_judges:
                stats['judges_normalized'] += 1

        normalized_cases.append(normalized)

    print(f"\nWriting normalized data to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(normalized_cases, f, indent=2)

    print(f"\n✓ Normalization complete!")
    print(f"  Total cases: {len(normalized_cases)}")
    print(f"  Cases with normalized judges: {stats['judges_normalized']}")
    print(f"  Output saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize judge names and other data in damages JSON files"
    )
    parser.add_argument(
        'input_file',
        help='Input JSON file (e.g., damages_full.json)'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output JSON file (default: input_file with _normalized suffix)'
    )

    args = parser.parse_args()

    input_path = args.input_file
    output_path = args.output

    if not output_path:
        # Add _normalized before .json
        if input_path.endswith('.json'):
            output_path = input_path[:-5] + '_normalized.json'
        else:
            output_path = input_path + '_normalized.json'

    normalize_data_file(input_path, output_path)


if __name__ == '__main__':
    main()
