"""
Data transformer for Ontario Damages Compendium - FIXED VERSION

Consolidates duplicate cases and keeps plaintiffs/regions as attributes.
"""

import json
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict


def consolidate_cases(ai_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Consolidate duplicate cases that appear multiple times with different categories/regions.

    Groups by: case_name + year + court
    Merges: plaintiffs, regions, categories from all duplicates

    Args:
        ai_cases: List of potentially duplicate cases

    Returns:
        List of consolidated unique cases
    """
    # Group cases by unique identifier
    case_groups = defaultdict(list)

    for case in ai_cases:
        # Create unique key (case_name + year + court)
        key = (
            case.get('case_name', 'Unknown'),
            case.get('year'),
            case.get('court')
        )
        case_groups[key].append(case)

    consolidated = []

    for (case_name, year, court), cases in case_groups.items():
        # Use first case as base
        base_case = cases[0]

        # Collect all unique plaintiffs
        all_plaintiffs = []
        seen_plaintiff_ids = set()

        for case in cases:
            plaintiffs = case.get('plaintiffs', [])
            if not plaintiffs:
                # Single plaintiff case
                plaintiffs = [case]

            for p in plaintiffs:
                p_id = p.get('plaintiff_id') or f"P{len(all_plaintiffs)+1}"
                if p_id not in seen_plaintiff_ids:
                    seen_plaintiff_ids.add(p_id)
                    all_plaintiffs.append(p)

        # Collect all unique regions/categories
        all_regions = set()
        all_categories = set()

        for case in cases:
            cat = case.get('category')
            if cat and cat != 'UNKNOWN':
                all_categories.add(cat)

            regions = case.get('region', [])
            if isinstance(regions, list):
                all_regions.update(r for r in regions if r and r != 'UNKNOWN')
            elif regions and regions != 'UNKNOWN':
                all_regions.add(regions)

        # Collect all injuries from all plaintiffs
        all_injuries = set()
        for p in all_plaintiffs:
            injuries = p.get('injuries', [])
            if isinstance(injuries, list):
                all_injuries.update(injuries)

        # Also check case-level injuries
        for case in cases:
            injuries = case.get('injuries', [])
            if isinstance(injuries, list):
                all_injuries.update(injuries)

        # Build consolidated case
        consolidated_case = {
            'case_name': case_name,
            'year': year,
            'court': court,
            'judge': base_case.get('judge') or base_case.get('judges', []),
            'citation': base_case.get('citation') or base_case.get('citations', []),
            'source_page': base_case.get('source_page') or base_case.get('source_pages', []),
            'categories': sorted(list(all_categories)) if all_categories else ['UNKNOWN'],
            'regions': sorted(list(all_regions)) if all_regions else ['UNKNOWN'],
            'injuries': sorted(list(all_injuries)),
            'plaintiffs': all_plaintiffs,
            'family_law_act_claims': base_case.get('family_law_act_claims', []),
            'comments': base_case.get('comments', '')
        }

        consolidated.append(consolidated_case)

    return consolidated


def convert_to_dashboard_format(
    ai_cases: List[Dict[str, Any]],
    model
) -> List[Dict[str, Any]]:
    """
    Convert AI-parsed format to dashboard format with embeddings.

    FIXED: Consolidates duplicate cases and keeps plaintiffs as nested data.

    Args:
        ai_cases: List of cases in AI-parsed format
        model: SentenceTransformer model for generating embeddings

    Returns:
        List of cases in dashboard format with embeddings
    """
    # First, consolidate duplicate cases
    print("   🔄 Consolidating duplicate cases...")
    consolidated_cases = consolidate_cases(ai_cases)
    print(f"   ✓ Consolidated {len(ai_cases)} records → {len(consolidated_cases)} unique cases")

    dashboard_cases = []

    for case_idx, case in enumerate(consolidated_cases, 1):
        plaintiffs = case.get('plaintiffs', [])

        # Get citation (handle list)
        citation = case.get('citation', [])
        if isinstance(citation, list):
            citation = '; '.join(str(c) for c in citation if c)

        # Get judges (handle list)
        judges = case.get('judge', [])
        if not isinstance(judges, list):
            judges = [judges] if judges else []

        # Get source page (use first if list)
        source_page = case.get('source_page')
        if isinstance(source_page, list):
            source_page = source_page[0] if source_page else None

        # Calculate total damages across all plaintiffs
        total_non_pecuniary = 0
        total_pecuniary = 0

        for p in plaintiffs:
            total_non_pecuniary += p.get('non_pecuniary_damages') or 0
            total_pecuniary += p.get('pecuniary_damages') or 0

        total_award = total_non_pecuniary + total_pecuniary if (total_non_pecuniary or total_pecuniary) else None

        # Get primary category and region
        categories = case.get('categories', ['UNKNOWN'])
        regions = case.get('regions', ['UNKNOWN'])
        primary_category = categories[0] if categories else 'UNKNOWN'
        primary_region = regions[0] if regions else 'UNKNOWN'

        # Create dashboard case
        dashboard_case = {
            'id': f"case_{case_idx:04d}",
            'case_name': case.get('case_name', 'Unknown'),
            'year': case.get('year'),
            'court': case.get('court'),
            'judge': judges,
            'citation': citation,
            'source_page': source_page,
            'category': primary_category,  # Primary category for compatibility
            'region': primary_region,  # Primary region for compatibility
            'damages': total_non_pecuniary,  # Total damages for sorting/filtering
            'non_pecuniary_damages': total_non_pecuniary,
            'pecuniary_damages': total_pecuniary,
            'total_award': total_award,
            'comments': case.get('comments', ''),
            'extended_data': {
                'injuries': case.get('injuries', []),
                'regions': regions,  # ALL regions
                'categories': categories,  # ALL categories
                'sex': plaintiffs[0].get('sex') if plaintiffs else None,  # Primary plaintiff
                'age': plaintiffs[0].get('age') if plaintiffs else None,  # Primary plaintiff
                'other_damages': [],
                'num_plaintiffs': len(plaintiffs),
                'plaintiffs': plaintiffs,  # Keep full plaintiff data
                'comments': case.get('comments', ''),
                'judges': judges,
                'family_law_act_claims': case.get('family_law_act_claims', [])
            }
        }

        # Generate summary text for embedding
        summary_parts = []
        injuries = case.get('injuries', [])
        if injuries:
            summary_parts.append(f"Injuries: {', '.join(injuries[:10])}")  # Limit to 10 for embedding
        if categories and categories != ['UNKNOWN']:
            summary_parts.append(f"Categories: {', '.join(categories)}")
        if case.get('comments'):
            summary_parts.append(f"Comments: {case.get('comments')}")

        summary_text = ' | '.join(summary_parts) if summary_parts else 'No summary available'
        dashboard_case['summary_text'] = summary_text

        # Generate embedding
        try:
            embedding = model.encode(summary_text, convert_to_numpy=True)
            dashboard_case['embedding'] = embedding.tolist()
        except Exception as e:
            print(f"⚠️  Warning: Could not generate embedding for case {dashboard_case['id']}: {e}")
            # Use zero vector as fallback (768 dimensions for all-mpnet-base-v2)
            dashboard_case['embedding'] = [0.0] * 768

        dashboard_cases.append(dashboard_case)

    return dashboard_cases
