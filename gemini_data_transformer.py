"""
Data transformation utilities for Gemini-parsed case data.

This module provides tools to convert Gemini-parsed case data into
formats compatible with the dashboard's search and display systems.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer


def convert_gemini_to_dashboard_format(
    gemini_cases: List[Dict[str, Any]],
    model: Optional[SentenceTransformer] = None
) -> List[Dict[str, Any]]:
    """
    Convert Gemini-parsed cases to dashboard format.

    Takes the rich Gemini format (with multiple plaintiffs, FLA claims, etc.)
    and converts it to the simpler dashboard format with embeddings.

    Args:
        gemini_cases: List of cases from Gemini parser
        model: SentenceTransformer model for generating embeddings
              (if None, embeddings are set to empty arrays)

    Returns:
        List of cases in dashboard format with embeddings

    Example:
        from sentence_transformers import SentenceTransformer
        from damages_parser_gemini import parse_compendium

        # Parse with Gemini
        gemini_cases = parse_compendium(...)

        # Convert to dashboard format
        model = SentenceTransformer('all-MiniLM-L6-v2')
        dashboard_cases = convert_gemini_to_dashboard_format(gemini_cases, model)

        # Save for dashboard
        with open('damages_with_embeddings.json', 'w') as f:
            json.dump(dashboard_cases, f)
    """
    dashboard_cases = []

    for case in gemini_cases:
        # For multi-plaintiff cases, create separate entries
        plaintiffs = case.get('plaintiffs', [])

        if not plaintiffs:
            # No plaintiff data, create single entry
            dashboard_case = _create_dashboard_case(case, None, model)
            dashboard_cases.append(dashboard_case)
        else:
            # Create one entry per plaintiff
            for plaintiff in plaintiffs:
                dashboard_case = _create_dashboard_case(case, plaintiff, model)
                dashboard_cases.append(dashboard_case)

    return dashboard_cases


def _create_dashboard_case(
    case: Dict[str, Any],
    plaintiff: Optional[Dict[str, Any]],
    model: Optional[SentenceTransformer]
) -> Dict[str, Any]:
    """
    Create a single dashboard case entry.

    Args:
        case: The Gemini case data
        plaintiff: Specific plaintiff data (or None)
        model: SentenceTransformer model

    Returns:
        Dashboard-formatted case dictionary
    """
    # Build summary text for embedding
    summary_parts = []

    # Case identification
    case_name = case.get('case_name', 'Unknown')
    year = case.get('year')
    summary_parts.append(f"{case_name} ({year})" if year else case_name)

    # Category/region
    category = case.get('category', 'UNKNOWN')
    summary_parts.append(f"Category: {category}")

    # Plaintiff details
    if plaintiff:
        plaintiff_id = plaintiff.get('plaintiff_id', 'P1')
        sex = plaintiff.get('sex', 'Unknown')
        age = plaintiff.get('age', 'Unknown')
        summary_parts.append(f"Plaintiff {plaintiff_id}: {sex}, age {age}")

        # Injuries
        injuries = plaintiff.get('injuries', [])
        if injuries:
            summary_parts.append(f"Injuries: {', '.join(injuries)}")

        # Other damages
        other_damages = plaintiff.get('other_damages', [])
        if other_damages:
            damage_types = [d.get('type', 'Other') for d in other_damages]
            summary_parts.append(f"Other damages: {', '.join(damage_types)}")

    # Court and citations
    court = case.get('court')
    if court:
        summary_parts.append(f"Court: {court}")

    citations = case.get('citations', [])
    if citations:
        summary_parts.append(f"Citations: {', '.join(citations)}")

    # Judges
    judges = case.get('judges', [])
    if judges:
        summary_parts.append(f"Judges: {', '.join(judges)}")

    # FLA claims
    fla_claims = case.get('family_law_act_claims', [])
    if fla_claims:
        fla_desc = [claim.get('description', 'FLA claim') for claim in fla_claims]
        summary_parts.append(f"Family Law Act: {', '.join(fla_desc)}")

    # Comments
    comments = case.get('comments')
    if comments:
        summary_parts.append(f"Comments: {comments}")

    summary_text = '. '.join(summary_parts)

    # Generate embedding
    embedding = []
    if model:
        try:
            embedding = model.encode(summary_text).tolist()
        except Exception as e:
            print(f"Warning: Failed to generate embedding for {case_name}: {e}")
            embedding = [0.0] * 384  # Default dimension for all-MiniLM-L6-v2

    # Extract damages amount
    damages = None
    if plaintiff:
        damages = plaintiff.get('non_pecuniary_damages')

    # Build dashboard case
    dashboard_case = {
        'region': category,  # Map category to region
        'case_name': case_name,
        'year': year,
        'court': court,
        'damages': damages,
        'summary_text': summary_text,
        'embedding': embedding,

        # Extended fields from Gemini
        'gemini_data': {
            'case_id': case.get('case_id'),
            'plaintiff_name': case.get('plaintiff_name'),
            'defendant_name': case.get('defendant_name'),
            'citations': citations,
            'judges': judges,
            'comments': comments,
            'plaintiff_id': plaintiff.get('plaintiff_id') if plaintiff else None,
            'sex': plaintiff.get('sex') if plaintiff else None,
            'age': plaintiff.get('age') if plaintiff else None,
            'is_provisional': plaintiff.get('is_provisional') if plaintiff else None,
            'injuries': plaintiff.get('injuries') if plaintiff else None,
            'other_damages': plaintiff.get('other_damages') if plaintiff else None,
            'family_law_act_claims': fla_claims,
            'num_plaintiffs': len(case.get('plaintiffs', [])),
        }
    }

    return dashboard_case


def add_embeddings_to_gemini_cases(
    gemini_json_path: str,
    output_path: str,
    model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'
) -> List[Dict[str, Any]]:
    """
    Load Gemini-parsed cases and add embeddings for dashboard use.

    This is a convenience function that:
    1. Loads Gemini JSON
    2. Converts to dashboard format
    3. Generates embeddings
    4. Saves to output file

    Args:
        gemini_json_path: Path to Gemini-parsed JSON file
        output_path: Path to save dashboard-compatible JSON
        model_name: Name of the sentence transformer model

    Returns:
        List of dashboard-formatted cases with embeddings

    Example:
        # After parsing with Gemini
        dashboard_cases = add_embeddings_to_gemini_cases(
            'damages_full.json',
            'data/damages_with_embeddings.json'
        )
    """
    print(f"Loading Gemini cases from {gemini_json_path}...")
    with open(gemini_json_path) as f:
        gemini_cases = json.load(f)

    print(f"Loaded {len(gemini_cases)} cases")

    print(f"Loading embedding model: {model_name}...")
    model = SentenceTransformer(model_name)

    print("Converting to dashboard format and generating embeddings...")
    dashboard_cases = convert_gemini_to_dashboard_format(gemini_cases, model)

    print(f"Generated {len(dashboard_cases)} dashboard cases")

    print(f"Saving to {output_path}...")
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(dashboard_cases, f, indent=2)

    print(f"✓ Done! Saved {len(dashboard_cases)} cases to {output_path}")

    return dashboard_cases


def merge_gemini_with_existing(
    gemini_json_path: str,
    existing_json_path: str,
    output_path: str,
    model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'
) -> List[Dict[str, Any]]:
    """
    Merge Gemini-parsed cases with existing dashboard data.

    Useful when you want to add new cases or replace existing ones
    with better Gemini-parsed data.

    Args:
        gemini_json_path: Path to Gemini-parsed JSON
        existing_json_path: Path to existing dashboard JSON
        output_path: Path to save merged results
        model_name: Embedding model name

    Returns:
        Merged list of cases

    Example:
        merged = merge_gemini_with_existing(
            'damages_full.json',
            'data/damages_with_embeddings.json',
            'data/damages_merged.json'
        )
    """
    # Load existing cases
    print(f"Loading existing cases from {existing_json_path}...")
    with open(existing_json_path) as f:
        existing_cases = json.load(f)
    print(f"Loaded {len(existing_cases)} existing cases")

    # Convert Gemini cases
    print(f"Loading Gemini cases from {gemini_json_path}...")
    with open(gemini_json_path) as f:
        gemini_cases = json.load(f)
    print(f"Loaded {len(gemini_cases)} Gemini cases")

    print(f"Loading embedding model: {model_name}...")
    model = SentenceTransformer(model_name)

    print("Converting Gemini cases...")
    new_cases = convert_gemini_to_dashboard_format(gemini_cases, model)
    print(f"Converted to {len(new_cases)} dashboard cases")

    # Merge: prioritize Gemini cases by case name
    case_map = {}

    # Add existing cases first
    for case in existing_cases:
        case_key = f"{case.get('case_name', 'UNKNOWN')}_{case.get('year', 0)}"
        if case_key not in case_map:
            case_map[case_key] = case

    # Add/replace with Gemini cases
    replaced = 0
    added = 0
    for case in new_cases:
        case_key = f"{case.get('case_name', 'UNKNOWN')}_{case.get('year', 0)}"
        if case_key in case_map:
            replaced += 1
        else:
            added += 1
        case_map[case_key] = case

    merged_cases = list(case_map.values())

    print(f"\nMerge results:")
    print(f"  Existing: {len(existing_cases)}")
    print(f"  New from Gemini: {len(new_cases)}")
    print(f"  Replaced: {replaced}")
    print(f"  Added: {added}")
    print(f"  Total: {len(merged_cases)}")

    # Save
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(merged_cases, f, indent=2)

    print("✓ Done!")

    return merged_cases


def extract_gemini_statistics(gemini_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract statistics from Gemini-parsed cases.

    Args:
        gemini_cases: List of Gemini-parsed cases

    Returns:
        Dictionary of statistics

    Example:
        stats = extract_gemini_statistics(cases)
        print(f"Multi-plaintiff cases: {stats['multi_plaintiff_count']}")
    """
    total_cases = len(gemini_cases)
    total_plaintiffs = sum(len(c.get('plaintiffs', [])) for c in gemini_cases)
    multi_plaintiff_cases = [c for c in gemini_cases if len(c.get('plaintiffs', [])) > 1]
    fla_cases = [c for c in gemini_cases if c.get('family_law_act_claims')]

    # Category distribution
    categories = {}
    for case in gemini_cases:
        cat = case.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1

    # Damages statistics
    all_damages = []
    for case in gemini_cases:
        for plaintiff in case.get('plaintiffs', []):
            damages = plaintiff.get('non_pecuniary_damages')
            if damages:
                all_damages.append(damages)

    stats = {
        'total_cases': total_cases,
        'total_plaintiffs': total_plaintiffs,
        'multi_plaintiff_count': len(multi_plaintiff_cases),
        'family_law_act_count': len(fla_cases),
        'categories': dict(sorted(categories.items(), key=lambda x: -x[1])[:20]),
        'damages_stats': {
            'count': len(all_damages),
            'mean': np.mean(all_damages) if all_damages else 0,
            'median': np.median(all_damages) if all_damages else 0,
            'min': min(all_damages) if all_damages else 0,
            'max': max(all_damages) if all_damages else 0,
        }
    }

    return stats


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python gemini_data_transformer.py <gemini_json> <output_json>")
        print("\nExample:")
        print("  python gemini_data_transformer.py damages_full.json data/damages_with_embeddings.json")
        sys.exit(1)

    gemini_json = sys.argv[1]
    output_json = sys.argv[2]

    add_embeddings_to_gemini_cases(gemini_json, output_json)
