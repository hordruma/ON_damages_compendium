"""
Data transformer for Ontario Damages Compendium

Converts parsed case data to dashboard format with embeddings.
Handles both the new CSV parser output and legacy AI-parsed format.
"""

import json
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict


def convert_to_dashboard_format(
    parsed_cases: List[Dict[str, Any]],
    model
) -> List[Dict[str, Any]]:
    """
    Convert parsed cases to dashboard format with embeddings.

    Handles the output from damages_parser_csv.py which already contains
    deduplicated cases with merged regions/categories.

    Args:
        parsed_cases: List of parsed case dicts (already deduplicated)
        model: SentenceTransformer model for generating embeddings

    Returns:
        List of cases in dashboard format with embeddings
    """
    dashboard_cases = []

    for case_idx, case in enumerate(parsed_cases, 1):
        # Get case identifiers
        case_name = case.get('case_name', 'Unknown')
        year = case.get('year')
        court = case.get('court')

        # Get citation (handle both string and list)
        citation = case.get('citation', '')
        if isinstance(citation, list):
            citation = '; '.join(str(c) for c in citation if c)

        # Get judges (handle both list and single value)
        judges = case.get('judge', [])
        if not isinstance(judges, list):
            judges = [judges] if judges else []

        # Get source page
        source_page = case.get('source_page')
        if isinstance(source_page, list):
            source_page = source_page[0] if source_page else None

        # Get categories and regions (may already be merged lists from dedup)
        categories = case.get('categories', [])
        if not categories:
            cat = case.get('category')
            categories = [cat] if cat else ['General']

        regions = case.get('region', [])
        if isinstance(regions, str):
            regions = [regions]
        if not regions:
            regions = categories.copy()

        primary_category = categories[0] if categories else 'General'
        primary_region = regions[0] if regions else 'General'

        # Get injuries (already extracted by parser)
        injuries = case.get('injuries', [])

        # Get demographics
        sex = case.get('sex')
        age = case.get('age')

        # Get damages — use top-level value directly (already correct from parser)
        non_pecuniary = case.get('non_pecuniary_damages') or 0
        is_provisional = case.get('is_provisional', False)

        # Handle multi-plaintiff cases
        plaintiffs = case.get('plaintiffs', [])
        if plaintiffs:
            # Multi-plaintiff: damages is already the total
            # Get sex/age from first plaintiff if not at case level
            if not sex and plaintiffs[0].get('sex'):
                sex = plaintiffs[0]['sex']
            if not age and plaintiffs[0].get('age'):
                age = plaintiffs[0]['age']
        else:
            # Single plaintiff: create a basic plaintiff record
            plaintiffs = [{
                'plaintiff_id': 'P1',
                'plaintiff_name': case.get('plaintiff_name', case_name.split(' v. ')[0] if ' v. ' in case_name else case_name),
                'non_pecuniary_damages': non_pecuniary,
                'sex': sex,
                'age': age,
            }]

        # Get other damages
        other_damages_list = case.get('other_damages', [])
        total_pecuniary = sum(d.get('amount', 0) for d in other_damages_list)

        total_award = (non_pecuniary + total_pecuniary) if (non_pecuniary or total_pecuniary) else None

        # Get FLA claims
        fla_claims = case.get('family_law_act_claims', [])

        # Get comments
        comments = case.get('comments', '')

        # Create dashboard case
        dashboard_case = {
            'id': f"case_{case_idx:04d}",
            'case_name': case_name,
            'year': year,
            'court': court,
            'judge': judges,
            'citation': citation,
            'source_page': source_page,
            'category': primary_category,
            'region': primary_region,
            'damages': non_pecuniary,
            'non_pecuniary_damages': non_pecuniary,
            'pecuniary_damages': total_pecuniary,
            'total_award': total_award,
            'comments': comments,
            'extended_data': {
                'injuries': injuries,
                'regions': regions,
                'categories': categories,
                'sex': sex,
                'age': age,
                'other_damages': other_damages_list,
                'num_plaintiffs': len(plaintiffs),
                'plaintiffs': plaintiffs,
                'comments': comments,
                'judges': judges,
                'family_law_act_claims': fla_claims,
                'is_provisional': is_provisional,
            }
        }

        # Generate summary text for embedding
        summary_parts = []
        if injuries:
            summary_parts.append(f"Injuries: {', '.join(injuries[:10])}")
        if categories and categories != ['General']:
            summary_parts.append(f"Categories: {', '.join(categories)}")
        if comments:
            summary_parts.append(f"Comments: {comments}")

        summary_text = ' | '.join(summary_parts) if summary_parts else 'No summary available'
        dashboard_case['summary_text'] = summary_text

        # Generate embedding
        try:
            embedding = model.encode(summary_text, convert_to_numpy=True)
            dashboard_case['embedding'] = embedding.tolist()
        except Exception as e:
            print(f"Warning: Could not generate embedding for case {dashboard_case['id']}: {e}")
            dashboard_case['embedding'] = [0.0] * 768

        dashboard_cases.append(dashboard_case)

    return dashboard_cases
