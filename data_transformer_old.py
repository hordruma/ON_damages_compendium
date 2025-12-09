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


def convert_to_dashboard_format(
    ai_cases: List[Dict[str, Any]],
    model
) -> List[Dict[str, Any]]:
    """
    Convert AI-parsed format to dashboard format with embeddings.

    This function handles AI-parsed cases that have a 'plaintiffs' array,
    converting each plaintiff into a separate dashboard case with embeddings.

    Args:
        ai_cases: List of cases in AI-parsed format (with 'plaintiffs' array)
        model: SentenceTransformer model for generating embeddings

    Returns:
        List of cases in dashboard format with embeddings
    """
    dashboard_cases = []
    case_counter = 1

    for case in ai_cases:
        # Handle cases with plaintiffs array (AI-parsed format)
        plaintiffs = case.get('plaintiffs', [])

        if not plaintiffs:
            # If no plaintiffs array, treat as single case (fallback)
            plaintiffs = [case]

        for plaintiff_idx, plaintiff in enumerate(plaintiffs):
            # Extract plaintiff-specific data
            if 'plaintiff_id' in plaintiff:
                # This is a separate plaintiff object
                injuries = plaintiff.get('injuries', [])
                sex = plaintiff.get('sex')
                age = plaintiff.get('age')
                non_pecuniary = plaintiff.get('non_pecuniary_damages')
                pecuniary = plaintiff.get('pecuniary_damages')
                other_damages = plaintiff.get('other_damages', [])
                comments = plaintiff.get('comments', '')
            else:
                # Fallback: use case-level data
                injuries = case.get('injuries', [])
                sex = case.get('sex')
                age = case.get('age')
                non_pecuniary = case.get('non_pecuniary_damages')
                pecuniary = case.get('pecuniary_damages')
                other_damages = case.get('other_damages', [])
                comments = case.get('comments', '')

            # Calculate total award
            total_award = None
            if non_pecuniary is not None or pecuniary is not None:
                total_award = (non_pecuniary or 0) + (pecuniary or 0)

            # Get category/region
            category = case.get('category', 'UNKNOWN')
            if isinstance(category, list):
                category = category[0] if category else 'UNKNOWN'

            region = case.get('region', [])
            if not isinstance(region, list):
                region = [region] if region else []

            # Combine category and region for regions field
            regions = [category] if category != 'UNKNOWN' else []
            if region:
                regions.extend(region)
            if not regions:
                regions = ['UNKNOWN']

            # Get citation (join if list)
            citation = case.get('citation') or case.get('citations', [])
            if isinstance(citation, list):
                citation = '; '.join(str(c) for c in citation if c)

            # Get source page (use first if list)
            source_page = case.get('source_page')
            if source_page is None:
                source_pages = case.get('source_pages', [])
                source_page = source_pages[0] if source_pages else None

            # Get judges (join if list)
            judges = case.get('judge') or case.get('judges', [])
            if not isinstance(judges, list):
                judges = [judges] if judges else []

            # Get FLA claims from case level
            fla_claims = case.get('family_law_act_claims', [])
            if not isinstance(fla_claims, list):
                fla_claims = []

            # Get region for top-level field (first region or category)
            top_level_region = None
            if region:
                top_level_region = region[0] if isinstance(region, list) else region
            elif category != 'UNKNOWN':
                top_level_region = category

            # Create dashboard case
            dashboard_case = {
                'id': f"case_{case_counter:04d}",
                'case_name': case.get('case_name', 'Unknown'),
                'year': case.get('year'),
                'court': case.get('court'),
                'judge': judges,
                'citation': citation,
                'source_page': source_page,
                'category': category,
                'region': top_level_region,  # Add top-level region field for judge analytics
                'damages': non_pecuniary,  # Add top-level damages field for judge analytics
                'non_pecuniary_damages': non_pecuniary,
                'pecuniary_damages': pecuniary,
                'total_award': total_award,
                'comments': comments,
                'extended_data': {
                    'injuries': injuries if isinstance(injuries, list) else [],
                    'regions': regions,
                    'sex': sex,
                    'age': age,
                    'other_damages': other_damages if isinstance(other_damages, list) else [],
                    'num_plaintiffs': len(plaintiffs) if plaintiffs else 1,
                    'plaintiff_id': plaintiff.get('plaintiff_id') if 'plaintiff_id' in plaintiff else None,
                    'comments': comments,
                    'judges': judges,  # Add judges to extended_data for judge analytics
                    'family_law_act_claims': fla_claims  # Add FLA claims to extended_data
                }
            }

            # Generate summary text for embedding
            # Use category for anatomical classification (injuries + category + comments)
            summary_parts = []
            if injuries:
                summary_parts.append(f"Injuries: {', '.join(injuries)}")
            if category and category != 'UNKNOWN':
                summary_parts.append(f"Category: {category}")
            if comments:
                summary_parts.append(f"Comments: {comments}")

            summary_text = ' | '.join(summary_parts) if summary_parts else 'No summary available'
            dashboard_case['summary_text'] = summary_text

            # Generate embedding
            try:
                embedding = model.encode(summary_text, convert_to_numpy=True)
                dashboard_case['embedding'] = embedding.tolist()
            except Exception as e:
                print(f"⚠️  Warning: Could not generate embedding for case {dashboard_case['id']}: {e}")
                # Use zero vector as fallback
                dashboard_case['embedding'] = [0.0] * 384  # all-MiniLM-L6-v2 dimension

            dashboard_cases.append(dashboard_case)
            case_counter += 1

    return dashboard_cases
