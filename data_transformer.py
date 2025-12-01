"""
Data transformer for Ontario Damages Compendium

Converts parsed cases to dashboard format with embeddings.
"""

import json
from typing import List, Dict, Any
from pathlib import Path


def add_embeddings_to_cases(
    input_json: str,
    output_json: str
) -> List[Dict[str, Any]]:
    """
    Transform parsed cases to dashboard format.

    Args:
        input_json: Path to raw parsed cases (from damages_parser_table.py)
        output_json: Path to save dashboard-ready cases

    Returns:
        List of dashboard-ready cases
    """
    # Load raw parsed cases
    with open(input_json, 'r', encoding='utf-8') as f:
        raw_cases = json.load(f)

    dashboard_cases = []

    for idx, case in enumerate(raw_cases):
        # Transform to dashboard format
        dashboard_case = {
            'id': f"case_{idx + 1:04d}",
            'case_name': case.get('case_name', 'Unknown'),
            'year': case.get('year'),
            'court': case.get('court'),
            'judge': case.get('judge'),
            'citation': case.get('citation'),
            'source_page': case.get('source_page'),
            'category': case.get('category', 'UNKNOWN'),
            'non_pecuniary_damages': case.get('non_pecuniary_damages'),
            'pecuniary_damages': case.get('pecuniary_damages'),
            'total_award': case.get('total_award'),
            'comments': case.get('comments'),
            'extended_data': {
                'injuries': case.get('injuries', []),
                'regions': [case.get('category', 'UNKNOWN')],  # Use category as region
                'sex': case.get('sex'),
                'age': case.get('age'),
                'other_damages': case.get('other_damages', [])
            }
        }

        # Handle multi-plaintiff cases
        if case.get('plaintiffs'):
            dashboard_case['plaintiffs'] = case['plaintiffs']

        dashboard_cases.append(dashboard_case)

    # Save dashboard cases
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(dashboard_cases, f, indent=2, ensure_ascii=False)

    print(f"✅ Transformed {len(dashboard_cases)} cases")
    print(f"   Saved to: {output_json}")

    return dashboard_cases
